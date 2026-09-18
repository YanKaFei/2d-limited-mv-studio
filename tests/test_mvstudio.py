#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""test_mvstudio.py —— anime-mv-studio 的行为规格测试（零第三方依赖）。

跑法：
    python3 -m unittest discover -s tests -t tests -v
"""

import io
import json
import math
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SCRIPTS = os.path.join(ROOT, "scripts")
LIB = os.path.join(SCRIPTS, "lib")
for p in (SCRIPTS, LIB, HERE):
    if p not in sys.path:
        sys.path.insert(0, p)

import fixtures  # noqa: E402

sys.path.insert(0, LIB)
import common  # noqa: E402


def _mod(name):
    return __import__(name)


# ==================================================================== 隐私
class TestNoPrivateContent(unittest.TestCase):
    """这个仓库是公开的 —— 不许把某个具体项目/人物/歌曲的痕迹带进去。

    关键词在这里**拼出来**而不是写字面量，否则守卫测试自己就成了泄漏源，
    也就不可能把 tests/ 一起纳入扫描。
    """

    FORBIDDEN = [
        "".join([u"阿", u"梓"]),
        "".join([u"小", u"跳", u"蛙"]),
        "".join([u"蛙", u"梓"]),
        "".join([u"青", u"蛙"]),
        "@" + "118" + "BPM",
        "project" + "_" + "overrides",
    ]
    SKIP_DIRS = {".git", "__pycache__", "workspace", "output", "input"}

    def _files(self):
        for root, dirs, names in os.walk(ROOT):
            dirs[:] = [d for d in dirs if d not in self.SKIP_DIRS]
            for n in names:
                if n.endswith((".pyc", ".png", ".wav", ".mp3", ".DS_Store")):
                    continue
                yield os.path.join(root, n)

    def test_no_private_terms_anywhere_in_the_package(self):
        hits = []
        for path in self._files():
            try:
                text = io.open(path, encoding="utf-8", errors="replace").read()
            except Exception:
                continue
            for term in self.FORBIDDEN:
                if term in text:
                    hits.append("%s → %s" % (os.path.relpath(path, ROOT), term))
        self.assertEqual(hits, [], u"包里有不该公开的内容：\n  " + "\n  ".join(hits))

    def test_libraries_have_no_project_bookkeeping(self):
        """动作库里不该留「这个动作属于哪个私下项目」的标记 —— 对公开用户无意义。"""
        import json as _json
        path = os.path.join(ROOT, "references", "motion-library.json")
        d = _json.load(io.open(path, encoding="utf-8"))
        bad = [m.get("id") for m in d.get("motions", []) if "project" in m]
        self.assertEqual(bad, [], u"动作库里还有项目私有标记：%s" % bad)
        for m in d.get("motions", []):
            note = m.get("note") or ""
            self.assertNotIn(u"该形象", note,
                             u"%s 的 note 还带着被抹掉的痕迹：%s" % (m.get("id"), note))

    def test_no_absolute_local_paths_outside_config(self):
        """除了 config/defaults.yaml（用户可以改的默认值），别处不写死本机路径。"""
        hits = []
        for path in self._files():
            rel = os.path.relpath(path, ROOT)
            if rel.startswith("config/") or rel.startswith("references/official/"):
                continue
            try:
                text = io.open(path, encoding="utf-8", errors="replace").read()
            except Exception:
                continue
            if ("/" + "Users" + "/") in text:
                hits.append(rel)
        self.assertEqual(hits, [], u"写死了本机绝对路径：%s" % hits)


# ==================================================================== config
class TestConfig(unittest.TestCase):
    """配置被静默截断 = 后面所有判断都建立在半份配置上。必须钉死。"""

    TOP_LEVEL = ("project", "audio", "image", "lyrics", "segment", "style",
                 "paths", "output", "external", "fallbacks")

    def test_defaults_load_every_top_level_section(self):
        cfg = common.config()
        missing = [k for k in self.TOP_LEVEL if k not in cfg]
        self.assertEqual(missing, [], u"config 被截断，丢了：%s" % missing)

    def test_output_contract_is_intact(self):
        out = common.config()["output"]
        for k in ("files", "h3_ref_sections", "brief_fields", "style_required_words",
                  "style_forbidden", "camera_official_terms", "camera_2d_allowed",
                  "drift_forbidden_in_body", "prompt_max_chars"):
            self.assertIn(k, out, u"output 段缺 %s" % k)
        self.assertEqual(len(out["camera_official_terms"]), 20)
        self.assertGreaterEqual(len(out["files"]), 6)

    def test_style_and_segment_sections_are_intact(self):
        cfg = common.config()
        self.assertGreaterEqual(len(cfg["style"]["fallback_mediums"]), 8)
        self.assertEqual(cfg["segment"]["target_seconds"], 14.5)
        self.assertEqual(cfg["segment"]["hard_max_seconds"], 15.0)
        self.assertEqual(cfg["segment"]["max_prompts"], 13)

    def test_block_sequences_are_not_coerced_to_strings(self):
        """多行 flow 序列会被解析成一个字符串 —— 这是最阴的一种坏法。"""
        cfg = common.config()
        for section, key in (("style", "fallback_mediums"),
                             ("output", "camera_official_terms"),
                             ("output", "style_required_words"),
                             ("audio", "extensions"),
                             ("image", "extensions")):
            val = cfg.get(section, {}).get(key)
            self.assertIsInstance(val, list, u"%s.%s 应该是 list" % (section, key))
            self.assertTrue(all(isinstance(v, str) for v in val))


# ==================================================================== beats
class TestBeats(unittest.TestCase):
    def test_beat_grid_geometry(self):
        beats = _mod("beats")
        g = beats.beat_grid(bpm=120.0, duration=20.0)
        self.assertAlmostEqual(g["beat_sec"], 0.5, places=6)
        self.assertAlmostEqual(g["bar_sec"], 2.0, places=6)
        self.assertEqual(g["beats_per_bar"], 4)
        self.assertEqual(len(g["beats"]), 41)
        self.assertEqual(len(g["bars"]), 11)

    def test_snap_time_to_bar(self):
        beats = _mod("beats")
        g = beats.beat_grid(bpm=120.0, duration=30.0)
        snapped = beats.snap_time(14.5, g, tolerance_beats=1.5)
        self.assertAlmostEqual(snapped["time"], 14.0, places=6)
        self.assertEqual(snapped["snapped_to"], "bar")

    def test_snap_falls_back_to_beat_then_exact(self):
        beats = _mod("beats")
        g = beats.beat_grid(bpm=120.0, duration=30.0)
        # 15.4 → 最近小节 16.0（差 1.2 拍，超 1.0 容差）→ 退到拍线 15.5
        s = beats.snap_time(15.4, g, tolerance_beats=1.0)
        self.assertEqual(s["snapped_to"], "beat")
        self.assertAlmostEqual(s["time"], 15.5, places=6)
        # 容差极小 → 不吸附
        s2 = beats.snap_time(15.4, g, tolerance_beats=0.01)
        self.assertEqual(s2["snapped_to"], "exact")
        self.assertAlmostEqual(s2["time"], 15.4, places=6)

    def test_segment_count_is_ceil_of_target(self):
        beats = _mod("beats")
        for duration, expect in ((55.745, 4), (58.0, 4), (58.1, 5), (180.0, 13), (14.0, 1)):
            segs = beats.segment_14_5(duration, grid=None, target=14.5)
            self.assertEqual(len(segs), expect,
                             "duration=%s 应有 %d 段" % (duration, expect))

    def test_segments_are_contiguous_and_bounded(self):
        beats = _mod("beats")
        segs = beats.segment_14_5(55.745, grid=None, target=14.5, hard_max=15.0)
        self.assertAlmostEqual(segs[0]["start"], 0.0, places=6)
        self.assertAlmostEqual(segs[-1]["end"], 55.745, places=6)
        for a, b in zip(segs, segs[1:]):
            self.assertAlmostEqual(a["end"], b["start"], places=6)
        for s in segs:
            self.assertLessEqual(s["length"], 15.0 + 1e-9)
            self.assertGreaterEqual(s["length"], 0.0)

    def test_segments_snap_to_bar_lines_with_real_bpm(self):
        beats = _mod("beats")
        g = beats.beat_grid(bpm=118.10, duration=55.745)
        segs = beats.segment_14_5(55.745, grid=g, target=14.5, tolerance_beats=1.5)
        self.assertEqual(len(segs), 4)
        # 118.10 BPM → 小节 2.0322s；14.5 应吸到第 7 小节 14.2254
        self.assertAlmostEqual(segs[0]["end"], 14.2254, places=3)
        self.assertEqual(segs[0]["snapped_to"], "bar")
        self.assertTrue(all(s["length"] <= 15.0 + 1e-9 for s in segs))
        # 第三刀超出小节容差，应退到拍线
        self.assertIn(segs[2]["snapped_to"], ("bar", "beat"))

    def test_snap_never_breaks_hard_max(self):
        beats = _mod("beats")
        g = beats.beat_grid(bpm=60.0, duration=40.0)  # 小节 4s，吸附跨度很大
        segs = beats.segment_14_5(40.0, grid=g, target=14.5, hard_max=15.0,
                                  tolerance_beats=1.5)
        for s in segs:
            self.assertLessEqual(s["length"], 15.0 + 1e-9,
                                 "吸附把小节撑过了 H3 上限：%s" % s)

    def test_tail_flag(self):
        beats = _mod("beats")
        segs = beats.segment_14_5(16.0, grid=None, target=14.5)
        self.assertEqual(len(segs), 2)
        self.assertFalse(segs[0]["is_tail"])
        self.assertTrue(segs[1]["is_tail"])
        self.assertAlmostEqual(segs[1]["length"], 1.5, places=6)

    def test_segment_seconds_never_exceed_h3_cap_in_config(self):
        beats = _mod("beats")
        target, cap = beats.defaults()
        self.assertLessEqual(target, cap)


# ==================================================================== H3 duration contract
class TestH3DurationContract(unittest.TestCase):
    """官方 API：duration 只接受 4–15 的**整数**。

    来源：https://platform.minimax.io/docs/guides/video-generation
          「Output duration | 4–15 seconds, integer values only」
    GitHub: https://github.com/MiniMax-AI/MiniMax-H3

    这条约束和「按 14.5 秒切分」并不冲突，但必须显式换算——
    否则用户会拿着 14.5 去填 duration，被 API 拒掉。
    """

    def test_request_seconds_is_integer_inside_official_range(self):
        b = _mod("beats")
        for audio in (14.5, 14.225, 12.245, 1.5, 6.0, 13.0, 15.0, 12.9, 8.0):
            r = b.request_seconds(audio)
            self.assertIsInstance(r, int, u"duration 必须是整数，%s 得到 %r" % (audio, r))
            self.assertGreaterEqual(r, 4)
            self.assertLessEqual(r, 15)

    def test_request_guarantees_delivery_covers_the_music(self):
        """帧网格会让 13 秒请求只吐 12.958s —— 比 13s 的音乐还短。

        所以「向上取整」不够，必须取「实出时长 ≥ 音乐长度」的最小整数。
        否则用户会**丢音乐**，而且是在剪辑台上才发现。
        """
        b = _mod("beats")
        for audio in (14.5, 14.2254, 12.245, 1.5, 6.0, 13.0, 15.0, 12.9, 8.0, 4.0, 9.9):
            r = b.request_seconds(audio)
            delivered = b.delivered_seconds(r)
            self.assertGreaterEqual(
                delivered, audio - 1e-9,
                u"请求 %ss（实出 %.4fs）装不下 %.4fs 的音乐" % (r, delivered, audio))

    def test_request_never_truncates_the_music(self):
        b = _mod("beats")
        self.assertEqual(b.request_seconds(14.5), 15)
        self.assertEqual(b.request_seconds(14.2254), 15)
        self.assertEqual(b.request_seconds(12.245), 13)
        self.assertEqual(b.request_seconds(15.0), 15)
        self.assertEqual(b.request_seconds(1.5), 4, u"不足 4 秒也要抬到官方下限")

    def test_delivered_frames_follow_official_grid(self):
        """官方实测端点：4 秒 → 107 帧，15 秒 → 362 帧（24fps），即 17k+5。"""
        b = _mod("beats")
        self.assertEqual(b.delivered_frames(4), 107)
        self.assertEqual(b.delivered_frames(15), 362)
        self.assertAlmostEqual(b.delivered_seconds(4), 4.4583, places=3)
        self.assertAlmostEqual(b.delivered_seconds(15), 15.0833, places=3)

    def test_segment_carries_the_conversion(self):
        b = _mod("beats")
        segs = b.segment_14_5(55.745, grid=b.beat_grid(bpm=118.10, duration=55.745))
        for s in segs:
            # duration 必须是「不小于音乐长度的最小合法整数」
            self.assertEqual(s["request_seconds"], b.request_seconds(s["audio_seconds"]))
            self.assertGreaterEqual(s["request_seconds"], s["audio_seconds"],
                                    u"请求时长不能短于音乐，否则会丢音乐")
            self.assertAlmostEqual(s["audio_seconds"], s["length"], places=6)
            self.assertEqual(s["usable_seconds"], s["audio_seconds"])
            self.assertGreaterEqual(s["delivered_seconds"], s["audio_seconds"])
            self.assertGreater(s["headroom_seconds"], 0,
                              u"整数向上取整后必须多出余量")
        # 音乐切在 ~14.5s 的内部段：一律请求 15s（官方上限，且留出藏缝余量）
        for s in segs[:-1]:
            self.assertEqual(s["request_seconds"], 15)
            self.assertGreater(s["audio_seconds"], 14.0)
            self.assertLessEqual(s["audio_seconds"], 15.0)

    def test_short_tail_is_flagged_as_pad_or_still(self):
        b = _mod("beats")
        segs = b.segment_14_5(16.0, grid=None)
        tail = segs[-1]
        self.assertAlmostEqual(tail["audio_seconds"], 1.5, places=6)
        self.assertEqual(tail["request_seconds"], 4)
        self.assertTrue(tail["is_tail_pad"])
        self.assertIn(tail["tail_advice"], ("pad_with_hold", "still_frame_in_edit"))

    def test_interior_segments_report_seam_overlap(self):
        b = _mod("beats")
        segs = b.segment_14_5(55.745, grid=b.beat_grid(bpm=118.10, duration=55.745))
        for s in segs[:-1]:
            self.assertGreater(s["seam_overlap_seconds"], 0.0,
                               u"内部段应留出可以藏缝的重叠量")


# ==================================================================== slicer
class TestSlicer(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="prism-slice-")
        self.wav = fixtures.write_click_track(
            os.path.join(self.tmp, "song.wav"), duration=20.0, bpm=120.0)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_cutter_chain_reports_available_tool(self):
        slicer = _mod("slicer")
        tool = slicer.available_cutter()
        self.assertIn(tool, ("ffmpeg", "afconvert", "wav-only", "none"))
        self.assertNotEqual(tool, "none")

    def test_slice_wav_by_boundaries(self):
        slicer = _mod("slicer")
        out = os.path.join(self.tmp, "seg")
        segs = [{"label": "C%d" % i, "start": a, "end": b}
                for i, (a, b) in enumerate([(0.0, 6.0), (6.0, 13.0), (13.0, 20.0)], 1)]
        res = slicer.slice_audio(self.wav, segs, out, prefix="C")
        self.assertTrue(res["ok"], res)
        self.assertEqual(len(res["files"]), 3)
        for f, expect in zip(res["files"], [6.0, 7.0, 7.0]):
            self.assertTrue(os.path.isfile(f["path"]))
            self.assertAlmostEqual(fixtures.wav_duration(f["path"]), expect, delta=0.08)

    def test_sliced_total_equals_original(self):
        slicer = _mod("slicer")
        out = os.path.join(self.tmp, "seg2")
        segs = [{"label": "C1", "start": 0.0, "end": 10.0},
                {"label": "C2", "start": 10.0, "end": 20.0}]
        res = slicer.slice_audio(self.wav, segs, out, prefix="C")
        total = sum(fixtures.wav_duration(f["path"]) for f in res["files"])
        self.assertAlmostEqual(total, 20.0, delta=0.1)

    def test_missing_source_is_reported_not_crashed(self):
        slicer = _mod("slicer")
        res = slicer.slice_audio(os.path.join(self.tmp, "nope.wav"),
                                 [{"label": "C1", "start": 0, "end": 1}],
                                 os.path.join(self.tmp, "x"))
        self.assertFalse(res["ok"])
        self.assertTrue(res.get("error"))


# ==================================================================== threeview
class TestThreeView(unittest.TestCase):
    CANON = {
        "name": "@CHARACTER",
        "hair": "black bob with blunt bangs, chin length",
        "eyes": "large round dark brown eyes",
        "face": "round youthful face, small nose",
        "costume": "pale blue sailor-collar dress with red ribbon",
        "accessories": "red neck ribbon, white knee socks",
        "silhouette": "short compact figure, clear oval head shape",
        "stable_identifiers": ["red neck ribbon", "blunt bangs"],
        "dominant_colors": ["#A8C8E8", "#D94A4A"],
    }

    def test_spec_has_four_views_and_layout(self):
        tv = _mod("threeview")
        spec = tv.build_spec(self.CANON)
        self.assertEqual(spec["views"][:4], ["front", "three-quarter", "side", "back"])
        self.assertIn("panels", spec["layout"])
        # 格数只能说一次 —— 拼出来的排版说明不能自己重复
        self.assertEqual(spec["layout"].lower().count("equal panels"), 1,
                         u"排版说明重复了格数：%s" % spec["layout"])

    def test_prompt_names_every_view_and_locks_identity(self):
        tv = _mod("threeview")
        spec = tv.build_spec(self.CANON)
        text = tv.render_prompt(spec, self.CANON, lang="en")
        for v in ("front", "side", "back"):
            self.assertIn(v, text.lower())
        self.assertIn("@CHARACTER", text)
        low = text.lower()
        self.assertIn("same character", low)
        self.assertIn("do not redesign", low)
        # 关键识别物必须写进去
        self.assertIn("red neck ribbon", text)

    def test_chinese_prompt_available(self):
        tv = _mod("threeview")
        spec = tv.build_spec(self.CANON)
        text = tv.render_prompt(spec, self.CANON, lang="zh")
        self.assertIn(u"三视图", text)
        self.assertIn(u"正面", text)
        self.assertIn(u"背面", text)

    def test_checklist_flags_missing_fields(self):
        tv = _mod("threeview")
        ok = tv.consistency_checklist(self.CANON)
        self.assertTrue(all(c["ok"] for c in ok), ok)
        broken = dict(self.CANON)
        broken["hair"] = ""
        bad = tv.consistency_checklist(broken)
        self.assertFalse(all(c["ok"] for c in bad))
        self.assertTrue(any(c["field"] == "hair" and not c["ok"] for c in bad))

    def test_negative_prompt_blocks_redesign(self):
        tv = _mod("threeview")
        spec = tv.build_spec(self.CANON)
        neg = tv.render_negative(spec)
        low = neg.lower()
        self.assertIn("different outfit", low)
        self.assertIn("multiple characters", low)


# ==================================================================== style routes
class TestStyleRoutes(unittest.TestCase):
    LYRICS = [
        {"start": 4.2, "end": 9.1, "text": u"我把影子留在水面"},
        {"start": 14.3, "end": 19.4, "text": u"夕阳把池塘染成蓝色"},
        {"start": 19.4, "end": 24.6, "text": u"它跳起舞来就像被王子附体了"},
        {"start": 45.3, "end": 50.4, "text": u"越过蓝色的夕阳"},
    ]
    ANALYSIS = {"bpm": 118.1, "duration": 55.745, "rhythmic_density": 1.3,
                "structure": {"peak_sections": [{"start": 28.4, "end": 43.7}],
                              "quiet_sections": [{"start": 0, "end": 14.2}]}}

    def test_menu_has_requested_size_and_distinct_styles(self):
        sr = _mod("styleroutes")
        routes = sr.build_routes(self.LYRICS, self.ANALYSIS, size=4, segments=4)
        self.assertEqual(len(routes), 4)
        for r in routes:
            self.assertTrue(r["id"])
            self.assertTrue(r["name"])
            self.assertTrue(r["rationale"])
            self.assertEqual(len(r["movement_per_segment"]), 4)
            distinct = set(m for m in r["movement_per_segment"] if m)
            self.assertGreaterEqual(len(distinct), 3,
                                    "路线 %s 没有穿越 ≥3 种画风：%s" % (r["id"], distinct))

    def test_no_consecutive_style_repeat(self):
        """人物要在**不同**艺术风格环境下跳舞 —— 相邻两段不该是同一个画风。"""
        sr = _mod("styleroutes")
        routes = sr.build_routes(self.LYRICS, self.ANALYSIS, size=6, segments=6)
        for r in routes:
            seq = r["movement_per_segment"]
            for a, b in zip(seq, seq[1:]):
                self.assertNotEqual(a, b,
                                    u"路线 %s 相邻两段画风重复：%s" % (r["id"], seq))

    def test_routes_work_without_artvault(self):
        sr = _mod("styleroutes")
        routes = sr.build_routes(self.LYRICS, self.ANALYSIS, size=2, segments=3,
                                 vault_available=False)
        self.assertEqual(len(routes), 2)
        for r in routes:
            self.assertTrue(r["movement_per_segment"])

    def test_pick_route_writes_assignment(self):
        sr = _mod("styleroutes")
        routes = sr.build_routes(self.LYRICS, self.ANALYSIS, size=2, segments=3)
        plan = {"segments": [{"id": 1}, {"id": 2}, {"id": 3}]}
        out = sr.apply_route(plan, routes[1])
        self.assertEqual(out["art_direction"]["route_id"], routes[1]["id"])
        self.assertEqual(len(out["art_direction"]["movement_per_segment"]), 3)
        for seg, mv in zip(out["segments"], routes[1]["movement_per_segment"]):
            self.assertEqual(seg["art_movement"], mv)

    def test_lyric_image_lookup_uses_style_map(self):
        sr = _mod("styleroutes")
        hit = sr.lookup_image(u"夕阳")
        self.assertTrue(hit, "style-map 里应能查到「夕阳」")
        self.assertIn("slug", hit[0])


# ==================================================================== h3 render
class TestH3Render(unittest.TestCase):
    def _plan(self):
        return {
            "meta": {"duration": 29.0, "segment_count": 2, "lang": "en",
                     "bpm": 120.0, "beat_sec": 0.5, "bar_sec": 2.0},
            "mv_concept": u"身体不变，世界不断更换画风",
            "character_canon": {
                "name": "@CHARACTER",
                "hair": "black bob with blunt bangs",
                "eyes": "large round dark brown eyes",
                "face": "round youthful face",
                "costume": "pale blue sailor dress with red ribbon",
                "accessories": "red neck ribbon, white knee socks",
                "silhouette": "short compact figure",
                "stable_identifiers": ["red neck ribbon", "blunt bangs"],
            },
            "assets": {
                "character_reference": {"path": "char.png",
                                        "role": "character reference",
                                        "label": "<Picture 1>"},
                "turnaround_sheet": {"path": "threeview.png",
                                     "role": "character turnaround reference",
                                     "label": "<Picture 2>"},
                "audio": {"path": "song.wav", "role": "original song reused 1:1",
                          "label": "<Audio 1>"},
            },
            "art_direction": {"primary_medium": "risograph and graphite 2D animation",
                              "movement_per_segment": ["rimpa", "shin-hanga"]},
            "segments": [
                {"id": 1, "label": "C1", "time_start": 0.0, "time_end": 14.5,
                 "bar_start": 1, "bar_end": 8, "beat_start": 0, "beat_end": 28,
                 "lyrics": [u"我把影子留在水面"],
                 "central_meaning": u"主体把自己的痕迹交给水面",
                 "character_state": u"重心下沉，持续跳，不表演情绪",
                 "primary_metaphor": u"水面复印主体",
                 "secondary_motif": u"错版水纹",
                 "environment_system": u"水面本身是叙事装置，波纹随歌词扩张",
                 "background_lyric_elements": [u"水面", u"影子", u"波纹"],
                 "choreography": "step-touch with a slow arm sweep across the body",
                 "art_movement": "rimpa",
                 "animation_medium": "animation on twos, held frame on the downbeat",
                 "style_prompt": ("2D limited animation, hand-drawn, flat composition, "
                                  "rimpa gold-leaf water pattern"),
                 "shots": [
                     {"index": 1, "start": 0.0, "end": 7.0, "beat_start": 0, "beat_end": 14,
                      "camera": "Static Shot", "camera_amplitude": "",
                      "camera_speed": "", "shot_size": "medium shot",
                      "camera_relation": "observes",
                      "action": "she plants her weight and sweeps one arm across the water",
                      "cut": "hard cut", "lyric": u"我把影子留在水面"},
                     {"index": 2, "start": 7.0, "end": 14.5, "beat_start": 14, "beat_end": 28,
                      "camera": "Push In", "camera_amplitude": "with small amplitude",
                      "camera_speed": "at slow speed", "shot_size": "close-up",
                      "camera_relation": "opposes",
                      "action": "her reflection ripples and doubles",
                      "cut": "hard cut", "lyric": u"我把影子留在水面"}],
                 "content_prompt": "0-7s ... 7-14.5s ...",
                 "overall_soundscape": "water laps against the bank.",
                 "continuity_from_previous": "opening shot",
                 "hook_to_next": "her arm stays raised"},
                {"id": 2, "label": "C2", "time_start": 14.5, "time_end": 29.0,
                 "bar_start": 8, "bar_end": 15, "beat_start": 28, "beat_end": 56,
                 "lyrics": [u"夕阳把池塘染成蓝色"],
                 "central_meaning": u"世界被重新上色，主体不变",
                 "character_state": u"动作幅度放大，重心开始移动",
                 "primary_metaphor": u"世界换色而人不变",
                 "secondary_motif": u"渐变天空分带",
                 "environment_system": u"天空被切成平涂色带，每一带对应一个重拍",
                 "background_lyric_elements": [u"夕阳", u"池塘", u"蓝色"],
                 "choreography": "hip shift into a two-step turn",
                 "art_movement": "shin-hanga",
                 "animation_medium": "stepped motion with smear frames",
                 "style_prompt": ("2D limited animation, hand-drawn, flat composition, "
                                  "shin-hanga gradation sky"),
                 "shots": [
                     {"index": 1, "start": 0.0, "end": 14.5, "beat_start": 0, "beat_end": 28,
                      "camera": "Pan Right", "camera_amplitude": "with large amplitude",
                      "camera_speed": "at slow speed", "shot_size": "wide shot",
                      "camera_relation": "reveals_behind",
                      "action": "she keeps dancing as the palette changes behind her",
                      "cut": "none", "lyric": u"夕阳把池塘染成蓝色"}],
                 "content_prompt": "0-14.5s ...",
                 "overall_soundscape": "cloth shifts and a low breeze.",
                 "continuity_from_previous": "continues the raised arm",
                 "hook_to_next": "final held cel"},
            ],
        }

    def test_ref2va_has_six_official_sections_in_order(self):
        h3 = _mod("h3render")
        text = h3.render_segment(self._plan(), self._plan()["segments"][0], route="ref")
        order = ["subject_definitions:", "summary:", "retention_analysis:",
                 "detailed_description:", "overall_soundscape:", "non_diegetic_music:"]
        pos = [text.index(k) for k in order]
        self.assertEqual(pos, sorted(pos), "Ref2VA 六段顺序不对")

    def test_ref2va_summary_task_prefix_and_labels(self):
        h3 = _mod("h3render")
        text = h3.render_segment(self._plan(), self._plan()["segments"][0], route="ref")
        self.assertIn("[reference generation + audio reuse]", text)
        self.assertIn("<Subject 1>", text)
        self.assertIn("<Picture 1>", text)
        self.assertIn("fully_preserved", text)
        self.assertIn("<Audio 1>: fully_copy", text)
        self.assertIn("non_diegetic_music: N/A", text)

    def test_ref2va_character_is_cited_not_rebuilt_as_picture(self):
        """官方规则：图只用于定义角色时，不得单独建 <Picture N> 条目。

        判据是**有没有独立条目行**（行首就是 <Picture N>），
        而不是 <Picture N> 这个字样能不能出现——它必须出现在 <Subject 1> 的定义里。
        """
        h3 = _mod("h3render")
        text = h3.render_segment(self._plan(), self._plan()["segments"][0], route="ref")
        subject_block = text.split("summary:")[0]
        self.assertIn("<Picture 1>", subject_block)
        # 三视图被引在 Subject 1 的定义里
        self.assertIn("<Picture 2>", subject_block)
        for line in subject_block.splitlines():
            self.assertFalse(line.strip().startswith("<Picture 2>"),
                             u"<Picture 2> 被建成了独立条目：%s" % line)
            self.assertFalse(line.strip().startswith("<Picture 1>"),
                             u"<Picture 1> 被建成了独立条目：%s" % line)
        # 必须有独立的 Subject 定义行
        self.assertTrue(any(l.strip().startswith("<Subject 1>")
                            for l in subject_block.splitlines()))

    def test_first_shot_has_no_timestamp_later_shots_do(self):
        h3 = _mod("h3render")
        text = h3.render_segment(self._plan(), self._plan()["segments"][0], route="ref")
        body = text.split("detailed_description:")[1].split("overall_soundscape:")[0]
        self.assertIn("[Shot 1]", body)
        self.assertNotIn("[Shot 1] At ", body)
        self.assertIn("[Shot 2] At 00:07.000", body)

    def test_i2va_first_line_is_verbatim_alignment(self):
        h3 = _mod("h3render")
        text = h3.render_segment(self._plan(), self._plan()["segments"][0], route="i2va")
        first = text.splitlines()[0]
        self.assertEqual(
            first,
            "For the target video, at 0.00 seconds into the target video, "
            "<Picture 1> (from [Shot 1]) is fully referenced.")
        self.assertEqual(text.splitlines()[1], "")
        self.assertIn("integrated_multimodal_description:", text)

    def test_t2va_starts_with_multimodal_and_has_no_picture_labels(self):
        h3 = _mod("h3render")
        text = h3.render_segment(self._plan(), self._plan()["segments"][0], route="t2va")
        self.assertTrue(text.startswith("integrated_multimodal_description:"))
        self.assertNotIn("<Picture 1>", text)

    def test_camera_terms_are_official_only(self):
        """运镜必须用官方词表，且写成自然英文动作（官方样式是带词形变化的句子）。"""
        h3 = _mod("h3render")
        text = h3.render_segment(self._plan(), self._plan()["segments"][0], route="ref")
        used = h3.camera_terms_in(text)
        self.assertIn("Static Shot", used)
        self.assertIn("Push In", used)
        # 官方样式的自然句（推镜要写成 pushes in，而不是贴标签）
        self.assertIn("The camera pushes in with small amplitude at slow speed", text)
        self.assertEqual(h3.invented_camera_in(text), [],
                         u"出现了自造/3D 运镜词")
        for invented in ("graphic push-in", "snap zoom", "dolly", "3D orbit"):
            self.assertNotIn(invented, text)

    def test_character_canon_is_restated_in_ref_blocks(self):
        h3 = _mod("h3render")
        text = h3.render_segment(self._plan(), self._plan()["segments"][0], route="ref")
        subject_block = text.split("summary:")[0]
        self.assertIn("black bob with blunt bangs", subject_block)
        self.assertIn("red neck ribbon", subject_block)
        self.assertIn("the only character", subject_block)

    def test_paste_block_has_no_markdown_and_fits_limit(self):
        h3 = _mod("h3render")
        text = h3.render_segment(self._plan(), self._plan()["segments"][0], route="ref")
        self.assertNotIn("**", text)
        self.assertLessEqual(len(text), 7000)

    def test_shot_descriptions_are_well_formed_sentences(self):
        """正文是模型要读的英文，不能是拼起来的小写碎片。"""
        h3 = _mod("h3render")
        text = h3.render_segment(self._plan(), self._plan()["segments"][0], route="ref")
        body = text.split("detailed_description:")[1].split("overall_soundscape:")[0]
        first = re.search(r"\[Shot 1\]\s+(\S)", body)
        self.assertIsNotNone(first, u"找不到 [Shot 1]")
        self.assertTrue(first.group(1).isupper(),
                        u"[Shot 1] 的内容必须以大写开头，实际是 %r" % first.group(1))
        second = re.search(r"\[Shot 2\]\s+(\S+)", body)
        self.assertTrue(second and second.group(1).startswith("At"),
                        u"[Shot 2] 必须以 'At MM:SS.mmm' 起头，实际是 %r"
                        % (second.group(1) if second else None))
        # 剧情句不能以句号开始新片段却用小写
        self.assertNotIn(". she ", body)
        self.assertNotIn(". the ", body)
        # 拼接不能产生重复标点
        self.assertNotIn("..", text, u"出现重复句号")
        self.assertNotIn(" .", text, u"出现「空格+句号」")

    def test_zh_route_preserves_original_lyrics(self):
        h3 = _mod("h3render")
        text = h3.render_segment(self._plan(), self._plan()["segments"][0],
                                 route="ref", lang="zh")
        self.assertIn(u"我把影子留在水面", text)

    def test_full_package_contains_every_segment(self):
        h3 = _mod("h3render")
        text = h3.render_package(self._plan(), route="ref")
        self.assertIn("MiniMax H3 Prompt 1", text)
        self.assertIn("MiniMax H3 Prompt 2", text)


# ==================================================================== mv 路线（用户指定结构 + 尾帧延续）
class TestMvRoute(unittest.TestCase):
    """用户指定的每条提示词结构：

        人物与参考保持一致性 / 风格提示词 / 内容提示词 /
        integrated_multimodal_description / overall_soundscape / non_diegetic_music

    并且：第一条出片后截尾帧 → 下一条在【内容提示词】里写「延续上一帧」，
    把那张图作为首帧参考放进提示词。用户已上传原曲，所以**不许**再写生成音乐的提示。
    """

    SECTIONS = [u"人物与参考保持一致性", u"风格提示词", u"内容提示词",
                "integrated_multimodal_description", "overall_soundscape",
                "non_diegetic_music"]

    def _plan(self, chained=False):
        plan = TestH3Render()._plan()
        plan["meta"]["lang"] = "zh"
        plan["meta"]["h3_route"] = "mv"
        if chained:
            plan["segments"][1]["chain"] = {
                "from_segment": "C1",
                "frame": "workspace/frames/C1_last.png",
                "label": "<Picture 3>",
                "declared": True,
                "describe": u"她右臂抬起，重心在左脚，背景是琳派水纹与注册标记",
                "continue_seconds": 1.5,
            }
            plan["segments"][1]["chain_continuity"] = u"起手直接接上一帧的抬臂与重心"
        else:
            plan["segments"][1]["chain"] = None
        return plan

    def test_sections_appear_in_required_order(self):
        h3 = _mod("h3render")
        text = h3.render_segment(self._plan(), self._plan()["segments"][0],
                                 route="mv", lang="zh")
        pos = [text.index(k) for k in self.SECTIONS]
        self.assertEqual(pos, sorted(pos), u"六段顺序不对：%s" % text[:200])
        for k in self.SECTIONS:
            self.assertIn(k, text)

    def test_no_music_generation_instruction(self):
        """用户自己传原曲 —— 提示词里不许再要求生成音乐/配乐。"""
        h3 = _mod("h3render")
        text = h3.render_segment(self._plan(), self._plan()["segments"][0],
                                 route="mv", lang="zh")
        self.assertIn("non_diegetic_music: N/A", text)
        for bad in (u"生成配乐", u"生成音乐", u"创作配乐", u"作曲", u"添加背景音乐",
                    "generate music", "compose a soundtrack", "add background music"):
            self.assertNotIn(bad, text, u"出现了生成音乐的要求：%s" % bad)

    def test_chained_segment_starts_from_previous_last_frame(self):
        h3 = _mod("h3render")
        plan = self._plan(chained=True)
        text = h3.render_segment(plan, plan["segments"][1], route="mv", lang="zh")
        # 首帧对齐指令必须是第一行（官方 I2VA 硬要求）
        self.assertTrue(text.splitlines()[0].startswith("For the target video"),
                        u"缺少首帧对齐指令：%s" % text.splitlines()[0])
        self.assertIn("<Picture 3>", text)
        self.assertIn("first_frame", text.lower().replace("first frame", "first_frame"))
        # 【内容提示词】里必须出现「延续上一帧」
        seg_block = text.split(u"内容提示词")[1].split("integrated_multimodal_description")[0]
        self.assertIn(u"延续上一帧", seg_block,
                      u"【内容提示词】里没有「延续上一帧」：%s" % seg_block[:200])
        self.assertIn(u"她右臂抬起", seg_block)

    def test_first_segment_has_no_chain_and_no_alignment_line(self):
        h3 = _mod("h3render")
        plan = self._plan()
        text = h3.render_segment(plan, plan["segments"][0], route="mv", lang="zh")
        self.assertFalse(text.splitlines()[0].startswith("For the target video"))
        self.assertNotIn(u"延续上一帧", text)
        self.assertNotIn("<Picture 3>", text)

    def test_reference_section_declares_frame_role(self):
        """那张尾帧必须**声明职责**（官方失败模式②：传了文件没写用途）。"""
        h3 = _mod("h3render")
        plan = self._plan(chained=True)
        text = h3.render_segment(plan, plan["segments"][1], route="mv", lang="zh")
        ref = text.split(u"风格提示词")[0]
        self.assertIn("<Picture 3>", ref)
        self.assertIn(u"首帧", ref)
        self.assertIn(u"人物参考", ref)
        # 文件名不能写进提示词（模型按上传顺序编号，不读路径）
        self.assertNotIn("C1_last.png", text)

    def test_mv_route_still_declares_character_consistency(self):
        h3 = _mod("h3render")
        plan = self._plan()
        text = h3.render_segment(plan, plan["segments"][0], route="mv", lang="zh")
        ref = text.split(u"风格提示词")[0]
        self.assertIn("black bob with blunt bangs", ref)
        self.assertIn("red neck ribbon", ref)
        self.assertIn(u"不得换脸", ref)

    def test_package_uses_mv_route_by_default(self):
        h3 = _mod("h3render")
        text = h3.render_package(self._plan(), route="mv", lang="zh")
        for k in self.SECTIONS:
            self.assertIn(k, text)

    def test_zh_block_formatting(self):
        """中文块里嵌英文句子时，别粘在一起、别小写开头。"""
        h3 = _mod("h3render")
        plan = TestH3Render()._plan()
        plan["meta"]["lang"] = "zh"
        text = h3.render_segment(plan, plan["segments"][0], route="mv", lang="zh")
        block = text.split(u"内容提示词")[1].split("integrated_multimodal_description")[0]
        self.assertNotIn(".[Shot", block, u"镜头标记和上一句粘在一起了")
        self.assertNotIn("。[shot", block, u"镜头标记和上一句粘在一起了")
        self.assertFalse(re.search(u"。[a-z]", block),
                         u"中文句号后面接了小写英文：%s" % block[:200])

    def test_chain_plan_links_segments_in_order(self):
        """链条：C1 无前帧；C2 接 C1；C3 接 C2 …"""
        ch = _mod("chain")
        plan = TestH3Render()._plan()
        plan = ch.build_chain(plan)
        segs = plan["segments"]
        self.assertIsNone(segs[0]["chain"])
        self.assertEqual(segs[1]["chain"]["from_segment"], "C1")
        self.assertEqual(segs[1]["chain"]["label"], "<Picture 3>")


# ==================================================================== 取帧
class TestFrames(unittest.TestCase):
    def test_extractor_chain_is_ordered(self):
        fr = _mod("frames")
        rep = fr.extractor_report()
        self.assertIn(rep["best"], ("ffmpeg", "avfoundation", "platform-export"))
        self.assertTrue(rep["platform_export_always_available"],
                        u"最后一级必须是「平台导出」——否则没有兜底")

    def test_missing_video_is_reported_not_crashed(self):
        fr = _mod("frames")
        res = fr.capture("/nope/not-a-video.mp4", "/tmp/x.png")
        self.assertFalse(res["ok"])
        self.assertTrue(res.get("error"))
        self.assertEqual(res.get("fallback"), "platform-export")

    def test_no_tool_at_all_degrades_to_platform_export(self):
        fr = _mod("frames")
        res = fr.capture(__file__, "/tmp/x.png", tool="none")
        self.assertFalse(res["ok"])
        self.assertIn("platform-export", res.get("fallback", ""))
        self.assertTrue(res.get("how"), u"要告诉用户去平台怎么导出")

    def test_avfoundation_none_actual_time_is_tolerated(self):
        """PyObjC 的 out-param 传 None 时返回 (image, None)。

        踩到过：直接拿 res[1] 去 CMTimeGetSeconds 会抛
        「depythonifying struct, got no sequence」，整个取帧就废了。
        """
        fr = _mod("frames")
        self.assertEqual(fr.resolve_actual_time((object(), None), 14.95, 15.084), 14.95)
        self.assertAlmostEqual(
            fr.resolve_actual_time((object(), 15.03), 14.95, 15.084), 15.03)
        self.assertEqual(fr.resolve_actual_time(None, 14.95, 15.084), 14.95)
        self.assertEqual(fr.resolve_actual_time((object(),), 14.95, 15.084), 14.95)

    def test_frame_output_path_convention(self):
        fr = _mod("frames")
        ch = _mod("chain")
        self.assertTrue(ch.frame_path("C1", "/tmp/f").endswith("C1_last.png"))
        self.assertTrue(ch.frame_path("C2", "/tmp/f", at="first")
                        .endswith("C2_first.png"))


# ==================================================================== 逐步骤确认
class TestConfirmations(unittest.TestCase):
    """用户要求：**每一个步骤都要让用户确认一下**。"""

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="prism-confirm-")
        self.plan = TestH3Render()._plan()
        self.plan["meta"]["lang"] = "zh"

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_ledger_records_and_reads_back(self):
        cf = _mod("confirm")
        led = cf.Ledger(self.tmp)
        self.assertFalse(led.is_confirmed("canon"))
        led.confirm("canon", note=u"人设没问题")
        self.assertTrue(led.is_confirmed("canon"))
        led2 = cf.Ledger(self.tmp)
        self.assertTrue(led2.is_confirmed("canon"), u"没有落盘")
        self.assertEqual(led2.get("canon").get("note"), u"人设没问题")

    def test_required_steps_include_every_prompt(self):
        cf = _mod("confirm")
        led = cf.Ledger(self.tmp)
        req = led.required_for_render(self.plan)
        self.assertIn("gate", req)
        self.assertIn("styles", req)
        self.assertIn("prompt-01", req)
        self.assertIn("prompt-02", req)
        self.assertEqual(len([r for r in req if r.startswith("prompt-")]), 2)

    def test_required_steps_include_chain_frames(self):
        """每一段的尾帧也要确认（用户要求逐步骤确认）。"""
        ch = _mod("chain")
        cf = _mod("confirm")
        plan = ch.build_chain(self.plan)
        led = cf.Ledger(self.tmp)
        req = led.required_for_render(plan)
        self.assertIn("chain-01", req)
        self.assertIn("chain-02", req)

    def test_pending_lists_unconfirmed_in_order(self):
        cf = _mod("confirm")
        led = cf.Ledger(self.tmp)
        led.confirm("gate")
        pend = led.pending(led.required_for_render(self.plan))
        self.assertNotIn("gate", pend)
        self.assertIn("analyze", pend)

    def test_render_blocks_until_confirmed(self):
        """未确认就渲染 = 跳过用户，必须被拦住。"""
        h3 = _mod("h3render")
        cf = _mod("confirm")
        led = cf.Ledger(self.tmp)
        missing = led.pending(led.required_for_render(self.plan))
        self.assertTrue(missing, u"应当有未确认的步骤")
        self.assertIn("prompt-01", missing)

    def test_confirm_all_batch(self):
        cf = _mod("confirm")
        led = cf.Ledger(self.tmp)
        led.confirm_all(led.required_for_render(self.plan))
        self.assertEqual(led.pending(led.required_for_render(self.plan)), [])


# ==================================================================== 平台适配
class TestPlatforms(unittest.TestCase):
    PLATFORMS = ["xiaoyunque", "minimax-design", "generic"]

    def test_known_platforms(self):
        pl = _mod("platforms")
        for p in self.PLATFORMS:
            self.assertIn(p, pl.known())

    def test_ops_sheet_names_the_platform_cut_feature(self):
        """用户说这两个平台有切割功能 —— 操作单必须点名它、并说清怎么用。"""
        pl = _mod("platforms")
        for p in ("xiaoyunque", "minimax-design"):
            md = pl.ops_sheet(p, TestH3Render()._plan())
            self.assertIn(u"切割", md, u"%s 的操作单没提切割功能" % p)
            self.assertTrue(pl.cut_feature(p), u"%s 没有声明切割功能" % p)

    def test_xiaoyunque_mentions_storyboard_and_first_last_frame(self):
        pl = _mod("platforms")
        spec = pl.get("xiaoyunque")
        blob = json.dumps(spec, ensure_ascii=False)
        self.assertIn(u"分镜", blob)
        self.assertIn(u"首尾帧", blob)

    def test_minimax_design_mentions_agent_confirm_and_edit(self):
        pl = _mod("platforms")
        spec = pl.get("minimax-design")
        blob = json.dumps(spec, ensure_ascii=False)
        self.assertIn(u"Agent", blob)
        self.assertIn(u"确认", blob)
        self.assertIn(u"剪辑", blob)

    def test_upload_table_has_one_more_row_when_chained(self):
        """续接段要多传一张尾帧 —— 操作单的表必须多一行。"""
        pl = _mod("platforms")
        ch = _mod("chain")
        plan = ch.build_chain(TestH3Render()._plan())
        md = pl.ops_sheet("xiaoyunque", plan)
        self.assertIn(u"尾帧", md)

    def test_unknown_platform_falls_back_to_generic(self):
        pl = _mod("platforms")
        self.assertEqual(pl.get("nope-not-real")["id"], "generic")


# ==================================================================== 收尾效果
class TestEndings(unittest.TestCase):
    """全片结束不一定「站定」。给用户几个收尾效果挑。"""

    def _plan(self):
        plan = TestH3Render()._plan()
        plan["meta"]["lang"] = "zh"
        plan["meta"]["h3_route"] = "mv"
        return plan

    def test_catalog_offers_at_least_six_choices(self):
        en = _mod("endings")
        ids = [e["id"] for e in en.catalog()]
        self.assertGreaterEqual(len(ids), 6, u"收尾效果给的选择太少：%s" % ids)
        self.assertEqual(len(ids), len(set(ids)), u"id 有重复")

    def test_every_ending_is_bilingual_and_directable(self):
        """每条都要中英双语，而且写的是**镜头看得见的东西**，不是情绪词。"""
        en = _mod("endings")
        for e in en.catalog():
            for k in ("id", "name_zh", "name_en", "what_zh", "what_en",
                      "prompt_zh", "prompt_en", "best_for"):
                self.assertIn(k, e, u"%s 缺字段 %s" % (e.get("id"), k))
                self.assertTrue(e[k], u"%s.%s 为空" % (e["id"], k))
            self.assertGreaterEqual(len(e["prompt_zh"]), 20,
                                    u"%s 的中文收尾描述太短" % e["id"])
            self.assertGreaterEqual(len(e["prompt_en"]), 30,
                                    u"%s 的英文收尾描述太短" % e["id"])

    def test_menu_is_ranked_by_music_ending(self):
        en = _mod("endings")
        hard = {"structure": {"ending_character": "hard stop —— 突然收住，"
                                                   "最后一段用定格抽帧 + 图形断口"}}
        soft = {"structure": {"ending_character": "fade/decay —— 收束为渐弱，"
                                                   "最后一段用 hold frame + 视觉衰减补足"}}
        m_hard = en.build_menu(hard, self._plan())
        m_soft = en.build_menu(soft, self._plan())
        self.assertNotEqual([e["id"] for e in m_hard[:3]],
                            [e["id"] for e in m_soft[:3]],
                            u"不同收束性格应该给出不同的首选")

    def test_menu_items_carry_a_reason(self):
        en = _mod("endings")
        for e in en.build_menu({}, self._plan()):
            self.assertTrue(e.get("why"), u"%s 没说为什么推荐" % e["id"])

    def test_apply_ending_writes_plan_and_is_idempotent(self):
        en = _mod("endings")
        plan = self._plan()
        e1 = en.catalog()[0]
        en.apply_ending(plan, e1["id"])
        self.assertEqual(plan["ending"]["id"], e1["id"])
        en.apply_ending(plan, e1["id"])
        self.assertEqual(plan["ending"]["id"], e1["id"])

    def test_apply_unknown_ending_raises(self):
        en = _mod("endings")
        self.assertRaises(KeyError, en.apply_ending, self._plan(), "not-a-real-ending")

    def test_last_segment_prompt_carries_the_chosen_ending(self):
        h3 = _mod("h3render")
        en = _mod("endings")
        plan = self._plan()
        pick = [e for e in en.catalog() if e["id"] == "reach_and_crack"][0]
        en.apply_ending(plan, pick["id"])
        text = h3.render_segment(plan, plan["segments"][-1], route="mv", lang="zh")
        seg_block = text.split(u"内容提示词")[1].split("integrated_multimodal_description")[0]
        self.assertIn(pick["prompt_zh"][:12], seg_block,
                      u"末段的【内容提示词】没有带上收尾效果")
        # 非末段不该出现收尾效果
        first = h3.render_segment(plan, plan["segments"][0], route="mv", lang="zh")
        self.assertNotIn(pick["prompt_zh"][:12], first)

    def test_no_ending_chosen_does_not_add_one(self):
        h3 = _mod("h3render")
        plan = self._plan()
        plan.pop("ending", None)
        text = h3.render_segment(plan, plan["segments"][-1], route="mv", lang="zh")
        self.assertNotIn(u"收尾效果", text)

    def test_ending_prompts_are_markdown_free(self):
        """收尾描述会直接进粘贴区 —— 粘贴区必须零 Markdown。"""
        en = _mod("endings")
        for e in en.catalog():
            for k in ("prompt_zh", "prompt_en"):
                self.assertNotIn("**", e[k], u"%s.%s 里有 Markdown 加粗" % (e["id"], k))

    def test_menu_md_is_bilingual(self):
        en = _mod("endings")
        md = en.render_md(en.build_menu({}, self._plan()))
        for e in en.catalog():
            self.assertIn(e["name_zh"], md)
            self.assertIn(e["name_en"], md)


# ==================================================================== 运镜/角度库
class TestCameraEnrichment(unittest.TestCase):
    """2D MV 也要有丰富的**角度**，不只是平移推拉。

    硬约束：MiniMax H3 只认它官方那 20 个运镜词，自造词不认。
    所以丰富化的方式不是编新词，而是分三层：
      shot_size（景别）· angle（角度）· camera（官方运动词）· framing（构图）
    并且**每一个电影术语都必须能映射回官方词**——否则就是在教用户写废词。
    """

    def test_angle_layer_exists_and_is_bilingual(self):
        cam = _mod("camera")
        ang = cam.angles()
        self.assertGreaterEqual(len(ang), 9, u"角度太少：%d" % len(ang))
        for a in ang:
            for k in ("id", "name_cn", "name_en", "prompt_en", "use") :
                self.assertTrue(a.get(k), u"%s 缺 %s" % (a.get("id"), k))

    def test_composition_layer_exists(self):
        cam = _mod("camera")
        comp = cam.compositions()
        self.assertGreaterEqual(len(comp), 9, u"构图项太少：%d" % len(comp))
        for c in comp:
            self.assertTrue(c.get("prompt_en"), u"%s 缺 prompt_en" % c.get("id"))

    def test_focus_layer_exists(self):
        cam = _mod("camera")
        f = cam.focus_terms()
        self.assertGreaterEqual(len(f), 4)
        ids = [x["id"] for x in f]
        self.assertIn("rack_focus", ids, u"少了「移焦」—— 换注意力最省的一招")

    def test_sixty_shot_sizes_are_replaced_by_a_grounded_set(self):
        cam = _mod("camera")
        sizes = cam.shot_sizes()
        self.assertGreaterEqual(len(sizes), 8)
        ids = [x["id"] for x in sizes]
        for need in ("extreme_close_up", "close_up", "medium_shot", "full_shot",
                     "wide_shot"):
            self.assertIn(need, ids, u"景别缺 %s" % need)

    def test_every_cinematic_term_maps_to_an_official_h3_term(self):
        """最要紧的一条不变量：丰富化不能教用户写 H3 不认的词。"""
        cam = _mod("camera")
        official = set(common.config()["output"]["camera_official_terms"])
        table = cam.cinematic_map()
        self.assertGreaterEqual(len(table), 15, u"电影术语映射表太小")
        for term, spec in table.items():
            self.assertIn(spec["official"], official,
                          u"%s 映射到了非官方词 %s" % (term, spec["official"]))
            self.assertTrue(spec.get("why"), u"%s 没写为什么这么映射" % term)
            amp = spec.get("amplitude")
            spd = spec.get("speed")
            if amp:
                self.assertIn(amp, common.config()["output"]["camera_amplitude"])
            if spd:
                self.assertIn(spd, common.config()["output"]["camera_speed"])

    def test_2d_native_moves_exist_and_stay_flat(self):
        """2D 专属的那几招：这是本技能和实拍运镜库的区别所在。"""
        cam = _mod("camera")
        moves = cam.moves_2d()
        ids = [m["id"] for m in moves]
        for need in ("rostrum", "multiplane_parallax", "cel_slide",
                     "registration_shift"):
            self.assertIn(need, ids, u"缺 2D 专属运镜 %s" % need)
        for m in moves:
            blob = json.dumps(m, ensure_ascii=False).lower()
            for bad in ("3d orbit", "drone", "fpv"):
                self.assertNotIn(bad, blob, u"%s 里混入了 3D 运镜" % m["id"])

    def test_static_lock_line_exists(self):
        """模型最容易在「固定镜头」上飘——必须有自然语言的加锁句。"""
        cam = _mod("camera")
        line = cam.static_lock_line("en")
        self.assertIn("motionless", line.lower())
        self.assertTrue(cam.static_lock_line("zh"))

    def test_relationship_verb_is_required(self):
        """相机与主体的关系不写清 → 抖动、人物像在飘。"""
        cam = _mod("camera")
        rel = cam.relations()
        self.assertGreaterEqual(len(rel), 5)
        for r in rel:
            self.assertTrue(r.get("en") and r.get("zh"))

    def test_renderer_emits_angle_and_purpose(self):
        h3 = _mod("h3render")
        plan = TestH3Render()._plan()
        plan["segments"][0]["shots"][0].update({
            "angle": "low_angle", "framing": "rule_of_thirds",
            "focus": "shallow_focus", "camera_relation": "follows",
            "purpose": "reveal the mark on her arm"})
        text = h3.render_segment(plan, plan["segments"][0], route="mv", lang="en")
        low = text.lower()
        self.assertIn("low angle", low, u"没有写角度")
        self.assertIn("rule of thirds", low, u"没有写构图")
        self.assertIn("follows", low, u"没有写相机与主体的关系")
        self.assertIn("reveal the mark", low, u"没有写这个镜头要揭示什么")

    def test_renderer_adds_static_lock_for_locked_shot(self):
        h3 = _mod("h3render")
        plan = TestH3Render()._plan()
        sh = plan["segments"][0]["shots"][0]
        sh["camera"] = "Static Shot"
        sh.pop("angle", None)
        text = h3.render_segment(plan, plan["segments"][0], route="mv", lang="en")
        self.assertIn("motionless", text.lower(),
                      u"固定镜头没有加锁句，模型会飘")

    def test_director_assigns_varied_angles_within_a_segment(self):
        d = _mod("director")
        plan = TestH3Render()._plan()
        shots = d.build_shots({"start": 0.0, "end": 30.0, "index": 1, "label": "C1"},
                              None, ["Static Shot", "Push In", "Pan Right"])
        angles = [s.get("angle") for s in shots]
        self.assertTrue(all(angles), u"有镜头没分到角度：%s" % angles)
        self.assertGreater(len(set(angles)), 1, u"同一段里角度全一样：%s" % angles)

    def test_moving_shots_are_capped_at_half(self):
        """运镜丰富 ≠ 运镜展览。每段运动镜头 ≤ 一半，其余留给 fixed。"""
        d = _mod("director")
        for end in (14.5, 20.0, 30.0, 45.0):
            shots = d.build_shots({"start": 0.0, "end": end, "index": 1, "label": "C1"},
                                  None, ["Push In", "Pan Left", "Truck Right",
                                         "Pull Out", "Zoom In", "Arc Shot"])
            moving = [x for x in shots if x.get("camera") != "Static Shot"]
            cap = -(-len(shots) // 2)          # ceil(n/2)
            self.assertLessEqual(len(moving), cap,
                                 u"%.1fs 段：%d 镜里 %d 个运动镜，超过上限 %d"
                                 % (end, len(shots), len(moving), cap))

    def test_gates_reject_too_many_moving_shots(self):
        gates = _mod("gates")
        plan = TestH3Render()._plan()
        plan["meta"]["h3_route"] = "mv"
        seg = plan["segments"][0]
        for sh in seg["shots"]:
            sh["camera"] = "Push In"          # 2/2 都是运动镜
            sh["camera_relation"] = "opposes"
        res = gates.validate(plan, "")
        self.assertFalse(res["passed"])
        self.assertTrue(any(u"运动镜头" in p for p in res["problems"]),
                        u"运动镜头超量没被拦：%s" % res["problems"])

    def test_moving_shot_without_relation_is_caught(self):
        gates = _mod("gates")
        plan = TestH3Render()._plan()
        plan["meta"]["h3_route"] = "mv"
        plan["segments"][0]["shots"][1]["camera_relation"] = ""
        res = gates.validate(plan, "")
        self.assertFalse(res["passed"])
        self.assertTrue(any(u"关系" in p for p in res["problems"]),
                        u"运动镜没写相机关系没被拦：%s" % res["problems"])

    def test_old_plan_without_new_fields_still_renders(self):
        """向后兼容：老导演稿没有 angle/framing 也要能出，不能炸。"""
        h3 = _mod("h3render")
        plan = TestH3Render()._plan()
        for seg in plan["segments"]:
            for sh in seg["shots"]:
                for k in ("angle", "framing", "focus", "camera_relation",
                          "purpose", "move_2d"):
                    sh.pop(k, None)
        text = h3.render_segment(plan, plan["segments"][0], route="mv", lang="zh")
        self.assertIn(u"内容提示词", text)
        self.assertIn("non_diegetic_music: N/A", text)

    def test_broken_library_degrades_instead_of_crashing(self):
        cam = _mod("camera")
        saved = cam._LIB_CACHE[0]
        try:
            cam._LIB_CACHE[0] = {}            # 模拟库被改坏
            self.assertEqual(cam.angles(), [])
            self.assertEqual(cam.cinematic_map(), {})
            self.assertEqual(cam.describe_shot({"angle": "low_angle"},
                                               "en")["text"], "")
            # 库坏了就不该再拿库去判 angle/framing 合不合法（那会把整片判红）
            probs = cam.validate_shot({"angle": "low_angle", "framing": "whatever"})
            self.assertEqual([x for x in probs if u"不在" in x], [],
                             u"库没加载起来时仍然在拿库判合法性：%s" % probs)
            # 不依赖库的规则照常生效
            self.assertTrue(any(u"关系" in x
                                for x in cam.validate_shot({"camera": "Push In"})))
        finally:
            cam._LIB_CACHE[0] = saved

    def test_2d_moves_land_on_locked_shots(self):
        """2D 专属招应该加在**机位不动**的镜头上：静止机位 + 画面仍在动。"""
        d = _mod("director")
        shots = d.build_shots({"start": 0.0, "end": 30.0, "index": 1, "label": "C1"},
                              None, ["Static Shot", "Push In", "Pan Right"])
        locked = [s for s in shots if s["camera"] == "Static Shot"]
        self.assertTrue(locked, u"样本里应该至少有一个固定镜头")
        self.assertTrue(any(s.get("move_2d") for s in locked),
                        u"固定镜头上没有安排任何 2D 专属运镜")

    def test_draft_markers_never_reach_a_rendered_prompt(self):
        """提示词里绝不能出现「（草稿：…）」——那是给人看的占位符。"""
        h3 = _mod("h3render")
        plan = TestH3Render()._plan()
        plan["segments"][0]["shots"][0]["action"] = u"（草稿：这一镜身体怎么动）"
        probs = h3.check_ready(plan)
        self.assertTrue(any(u"草稿" in p for p in probs),
                        u"草稿标记没被拦住：%s" % probs[:4])

    def test_draft_purpose_also_blocks_rendering(self):
        h3 = _mod("h3render")
        plan = TestH3Render()._plan()
        plan["segments"][0]["shots"][0]["purpose"] = u"（草稿：这一下要揭示什么）"
        probs = h3.check_ready(plan)
        self.assertTrue(any(u"草稿" in p for p in probs),
                        u"草稿 purpose 没被拦住：%s" % probs[:4])

    def test_2d_moves_vary_across_segments(self):
        """不同段不该老是同一招 —— 丰富度要真的落到输出上。"""
        d = _mod("director")
        firsts, allp = [], []
        for seed in range(6):
            shots = d.build_shots(
                {"start": 0.0, "end": 14.5, "index": seed + 1, "label": "C%d" % (seed + 1)},
                None, ["Static Shot", "Push In", "Pan Right"], shot_size_seed=seed)
            picked = [x.get("move_2d") for x in shots if x.get("move_2d")]
            allp += picked
            firsts.append(picked[0] if picked else None)
        self.assertGreater(len(set(allp)), 1, u"只用到一种 2D 招：%s" % allp)
        self.assertGreater(len(set(firsts)), 1,
                           u"每一段的**第一招**都是同一个，等于没有变化：%s" % firsts)

    def test_shot_size_is_not_stated_twice(self):
        h3 = _mod("h3render")
        plan = TestH3Render()._plan()
        sh = plan["segments"][0]["shots"][0]
        sh.update({"shot_size_id": "medium_shot", "angle": "low_angle",
                   "framing": "rule_of_thirds", "focus": "deep_focus",
                   "camera_relation": "observes", "purpose": "reveal the mark"})
        text = h3.render_segment(plan, plan["segments"][0], route="mv", lang="en")
        seg = text.split("content_prompt:")[1].split("integrated_multimodal_description")[0]
        self.assertEqual(seg.lower().count("medium shot"), 1,
                         u"景别写了两遍：%s" % seg[:260].replace("\n", " "))

    def test_zh_layers_use_chinese_names(self):
        h3 = _mod("h3render")
        plan = TestH3Render()._plan()
        sh = plan["segments"][0]["shots"][0]
        sh.update({"shot_size_id": "medium_shot", "angle": "low_angle",
                   "framing": "rule_of_thirds", "focus": "deep_focus",
                   "camera_relation": "observes", "purpose": u"露出身后的水面"})
        text = h3.render_segment(plan, plan["segments"][0], route="mv", lang="zh")
        seg = text.split(u"内容提示词")[1].split("integrated_multimodal_description")[0]
        self.assertIn(u"中景", seg, u"中文块里景别没用中文名")
        self.assertIn(u"仰角", seg)
        self.assertNotIn("medium shot", seg, u"中文块里混进了英文景别")

    def test_relation_and_purpose_are_separated(self):
        """关系与「要揭示什么」之间不能只隔一个空格。"""
        h3 = _mod("h3render")
        plan = TestH3Render()._plan()
        sh = plan["segments"][0]["shots"][0]
        sh.update({"angle": "low_angle", "framing": "rule_of_thirds",
                   "camera_relation": "observes", "purpose": u"露出身后的水面"})
        text = h3.render_segment(plan, plan["segments"][0], route="mv", lang="zh")
        seg = text.split(u"内容提示词")[1].split("integrated_multimodal_description")[0]
        self.assertRegex(seg, u"看着她。露出身后的水面",
                         u"关系与目的粘在一起了：%s" % seg[:260])

    def test_non_first_segment_is_not_called_the_opening(self):
        """只有真的第 1 段才叫「全片开头」。第 2 段没接上尾帧时要如实说。"""
        h3 = _mod("h3render")
        plan = TestH3Render()._plan()
        plan["meta"]["lang"] = "zh"
        plan["meta"]["h3_route"] = "mv"
        plan["segments"][1]["chain"] = None
        text = h3.render_segment(plan, plan["segments"][1], route="mv", lang="zh")
        seg = text.split(u"内容提示词")[1].split("integrated_multimodal_description")[0]
        self.assertNotIn(u"这是全片开头", seg,
                         u"第 2 段没接尾帧，却被写成「全片开头」")
        self.assertIn(u"未接上一帧", seg, u"没如实说明这一段没接上尾帧")

    def test_gates_reject_unknown_angle(self):
        gates = _mod("gates")
        plan = TestH3Render()._plan()
        plan["meta"]["h3_route"] = "mv"
        plan["segments"][0]["shots"][0]["angle"] = "impossible_angle"
        res = gates.validate(plan, "")
        self.assertFalse(res["passed"])
        self.assertTrue(any(u"角度" in p for p in res["problems"]),
                        u"野角度没被拦：%s" % res["problems"])

    def test_gates_reject_unknown_framing(self):
        gates = _mod("gates")
        plan = TestH3Render()._plan()
        plan["meta"]["h3_route"] = "mv"
        plan["segments"][0]["shots"][0]["framing"] = "made_up_composition"
        res = gates.validate(plan, "")
        self.assertFalse(res["passed"])
        self.assertTrue(any(u"构图" in p for p in res["problems"]),
                        u"野构图没被拦：%s" % res["problems"])


# ==================================================================== gates
class TestGates(unittest.TestCase):
    def _plan(self):
        base = TestH3Render()._plan()
        return base

    def test_clean_plan_passes(self):
        gates = _mod("gates")
        h3 = _mod("h3render")
        plan = self._plan()
        text = h3.render_package(plan, route="ref")
        res = gates.validate(plan, text)
        self.assertTrue(res["passed"], res["problems"])

    def test_segment_over_h3_cap_is_caught(self):
        gates = _mod("gates")
        plan = self._plan()
        plan["segments"][0]["time_end"] = 20.0
        res = gates.validate(plan, "")
        self.assertFalse(res["passed"])
        self.assertTrue(any("15" in p for p in res["problems"]))

    def test_invented_camera_word_is_caught(self):
        gates = _mod("gates")
        plan = self._plan()
        plan["segments"][0]["shots"][0]["camera"] = "graphic push-in"
        res = gates.validate(plan, "")
        self.assertFalse(res["passed"])
        self.assertTrue(any("运镜" in p or "camera" in p.lower() for p in res["problems"]))

    def test_missing_background_lyric_elements_is_caught(self):
        gates = _mod("gates")
        plan = self._plan()
        plan["segments"][0]["background_lyric_elements"] = []
        res = gates.validate(plan, "")
        self.assertFalse(res["passed"])
        self.assertTrue(any(u"背景" in p for p in res["problems"]))

    def test_broken_dance_continuity_is_caught(self):
        gates = _mod("gates")
        plan = self._plan()
        plan["segments"][0]["hook_to_next"] = ""
        res = gates.validate(plan, "")
        self.assertFalse(res["passed"])
        self.assertTrue(any(u"连" in p for p in res["problems"]))

    def test_too_few_distinct_styles_is_caught(self):
        gates = _mod("gates")
        plan = self._plan()
        for s in plan["segments"]:
            s["art_movement"] = "rimpa"
        res = gates.validate(plan, "")
        self.assertFalse(res["passed"])
        self.assertTrue(any(u"画风" in p for p in res["problems"]))

    def test_forbidden_generic_anime_word_is_caught(self):
        gates = _mod("gates")
        plan = self._plan()
        plan["segments"][0]["style_prompt"] = (
            "2D limited animation, hand-drawn, flat composition, "
            "neon city cyberpunk rooftop")
        res = gates.validate(plan, "")
        self.assertFalse(res["passed"])
        self.assertTrue(any("neon city" in p for p in res["problems"]))

    def test_missing_style_required_word_is_caught(self):
        gates = _mod("gates")
        plan = self._plan()
        plan["segments"][0]["style_prompt"] = "pretty colours"
        res = gates.validate(plan, "")
        self.assertFalse(res["passed"])
        self.assertTrue(any("limited animation" in p for p in res["problems"]))

    def test_missing_canon_is_caught(self):
        gates = _mod("gates")
        plan = self._plan()
        plan["character_canon"]["hair"] = ""
        res = gates.validate(plan, "")
        self.assertFalse(res["passed"])

    def test_lyrics_not_reflected_in_background_is_flagged(self):
        gates = _mod("gates")
        plan = self._plan()
        plan["segments"][0]["lyrics"] = [u"我把影子留在水面"]
        plan["segments"][0]["background_lyric_elements"] = [u"键盘", u"数据表"]
        plan["segments"][0]["content_prompt"] = "0-7s a girl dances in an empty room"
        res = gates.validate(plan, "")
        self.assertFalse(res["passed"])
        self.assertTrue(any(u"歌词" in p and u"背景" in p for p in res["problems"]))

    def test_cjk_sentence_in_english_body_is_flagged(self):
        """英文路线下正文必须英文（官方 O13）——夹整句中文要被提示。

        创作字段（environment_system / overall_soundscape / content_prompt …）
        会被原样写进英文正文，所以它们必须用目标语言写。
        """
        gates = _mod("gates")
        h3 = _mod("h3render")
        plan = self._plan()
        plan["meta"]["lang"] = "en"
        plan["segments"][0]["environment_system"] = u"水面本身就是叙事装置，波纹随歌词扩张"
        text = h3.render_package(plan, route="ref", lang="en")
        res = gates.validate(plan, text)
        self.assertTrue(
            any(u"英文" in w or u"中文" in w for w in res["warnings"]),
            u"英文正文里夹整句中文没有被提示：%s" % res["warnings"])

    def test_cjk_object_names_are_not_flagged(self):
        """背景实物与逐字引用的歌词按官方规则**保留原语言**，不该误报。"""
        gates = _mod("gates")
        h3 = _mod("h3render")
        plan = self._plan()
        plan["meta"]["lang"] = "en"
        text = h3.render_package(plan, route="ref", lang="en")
        res = gates.validate(plan, text)
        self.assertFalse(
            any(u"英文正文里夹" in w for w in res["warnings"]),
            u"把 2 字实物名误判成中文句子了：%s" % res["warnings"])

    def test_aggregate_coverage_stats(self):
        gates = _mod("gates")
        plan = self._plan()
        res = gates.validate(plan, "")
        self.assertIn("distinct_styles", res["stats"])
        self.assertIn("segments", res["stats"])


# ==================================================================== gates：mv 结构 / 尾帧 / 禁音乐
class TestGatesMv(unittest.TestCase):
    def _plan(self):
        plan = TestH3Render()._plan()
        plan["meta"]["lang"] = "zh"
        plan["meta"]["h3_route"] = "mv"
        _mod("endings").apply_ending(plan, "reach_and_crack")
        return plan

    def _text(self, plan, route="mv", lang="zh"):
        h3 = _mod("h3render")
        return h3.render_package(plan, route=route, lang=lang)

    def test_clean_mv_plan_passes(self):
        gates = _mod("gates")
        plan = self._plan()
        res = gates.validate(plan, self._text(plan))
        self.assertTrue(res["passed"], res["problems"])

    def test_missing_required_section_is_caught(self):
        gates = _mod("gates")
        plan = self._plan()
        text = self._text(plan)
        broken = text.replace(u"内容提示词：", u"（被我删掉了）：")
        res = gates.validate(plan, broken)
        self.assertFalse(res["passed"])
        self.assertTrue(any(u"内容提示词" in p for p in res["problems"]),
                        u"结构缺段没被抓到：%s" % res["problems"])

    def test_music_generation_phrasing_is_caught(self):
        """用户自己传原曲 —— 提示词里出现生成音乐的要求必须红。"""
        gates = _mod("gates")
        plan = self._plan()
        for seg in plan["segments"]:
            seg["overall_soundscape"] = u"生成配乐：舒缓钢琴"
        res = gates.validate(plan, self._text(plan))
        self.assertFalse(res["passed"])
        self.assertTrue(any(u"音乐" in p for p in res["problems"]),
                        u"生成音乐的措辞没被抓到：%s" % res["problems"])

    def test_chained_segment_without_continue_clause_is_caught(self):
        gates = _mod("gates")
        ch = _mod("chain")
        plan = ch.build_chain(self._plan())
        plan["segments"][1]["chain"]["declared"] = True
        plan["segments"][1]["chain"]["frame"] = __file__
        plan["segments"][1]["chain"]["describe"] = u"上一帧"
        plan["segments"][1]["chain_continuity"] = u"接上一帧的抬臂"
        text = self._text(plan)
        # 人为把「延续上一帧」删掉
        broken = text.replace(u"延续上一帧", u"另起一段")
        res = gates.validate(plan, broken)
        self.assertFalse(res["passed"])
        self.assertTrue(any(u"延续上一帧" in p for p in res["problems"]),
                        u"续接段缺「延续上一帧」没被抓到：%s" % res["problems"])

    def test_chain_declared_but_frame_missing_is_caught(self):
        gates = _mod("gates")
        plan = self._plan()
        plan["segments"][1]["chain"] = {
            "from_segment": "C1", "frame": "/nope/does-not-exist.png",
            "label": "<Picture 3>", "declared": True, "describe": u"x",
            "continue_seconds": 1.5}
        res = gates.validate(plan, self._text(plan))
        self.assertFalse(res["passed"])
        self.assertTrue(any(u"尾帧" in p for p in res["problems"]),
                        u"尾帧文件不存在没被抓到：%s" % res["problems"])

    def test_missing_ending_is_caught(self):
        """全片收尾必须由用户挑过 —— 缺了要红，不能默认成「站定」。"""
        gates = _mod("gates")
        plan = self._plan()
        plan.pop("ending", None)
        res = gates.validate(plan, self._text(plan))
        self.assertFalse(res["passed"])
        self.assertTrue(any(u"收尾" in p for p in res["problems"]),
                        u"没选收尾效果没被抓到：%s" % res["problems"])

    def test_ending_missing_from_last_block_is_caught(self):
        gates = _mod("gates")
        en = _mod("endings")
        plan = self._plan()
        text = self._text(plan)
        pick = en.get("reach_and_crack")
        broken = text.replace(pick["prompt_zh"][:12], u"（收尾被删掉了）")
        res = gates.validate(plan, broken)
        self.assertFalse(res["passed"])
        self.assertTrue(any(u"收尾" in p for p in res["problems"]),
                        u"末段缺收尾效果没被抓到：%s" % res["problems"])

    def test_chain_problems_are_folded_in(self):
        gates = _mod("gates")
        ch = _mod("chain")
        plan = ch.build_chain(self._plan())
        res = gates.validate(plan, self._text(plan))
        # 还没取帧 → 至少要有 warning，不能静默
        self.assertTrue(any(u"尾帧" in w for w in res["warnings"]),
                        u"未取尾帧没有提醒：%s" % res["warnings"])


# ==================================================================== gates on real pipeline output
class TestPipelineEndToEnd(unittest.TestCase):
    """真跑 CLI：合成素材 → all → 草稿必须拒绝渲染 → 填稿后必须绿。"""

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp(prefix="prism-e2e-")
        cls.proj = os.path.join(cls.tmp, "proj")
        for sub in ("input/music", "input/character", "input/lyrics",
                    "workspace", "output/latest", "output/archive"):
            os.makedirs(os.path.join(cls.proj, sub), exist_ok=True)
        cls.audio = fixtures.write_click_track(
            os.path.join(cls.proj, "input/music/song.wav"), duration=55.0, bpm=118.1)
        cls.image = fixtures.write_png(
            os.path.join(cls.proj, "input/character/character_ref.png"))
        fixtures.write_lyrics(os.path.join(cls.proj, "input/lyrics/song.lrc"))

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def _run(self, *args):
        cmd = [sys.executable, os.path.join(SCRIPTS, "mvstudio.py")] + list(args)
        return subprocess.run(cmd, cwd=self.proj, stdout=subprocess.PIPE,
                              stderr=subprocess.STDOUT)

    def test_01_doctor_json(self):
        r = self._run("doctor", "--json")
        self.assertEqual(r.returncode, 0, r.stdout.decode("utf-8", "replace"))
        data = json.loads(r.stdout.decode("utf-8"))
        self.assertIn("tools", data)
        self.assertIn("segment", data)

    def test_02_all_produces_segments_and_sliced_audio(self):
        r = self._run("all", "--unattended", "--audio", self.audio,
                      "--image", self.image)
        self.assertIn(r.returncode, (0, 3), r.stdout.decode("utf-8", "replace"))
        plan_path = os.path.join(self.proj, "workspace/analysis/director_plan.json")
        self.assertTrue(os.path.isfile(plan_path), r.stdout.decode("utf-8", "replace"))
        with open(plan_path, encoding="utf-8") as fh:
            plan = json.load(fh)
        expect = int(math.ceil(55.0 / 14.5))
        self.assertEqual(len(plan["segments"]), expect)
        seg_dir = os.path.join(self.proj, "workspace/segments")
        wavs = [f for f in os.listdir(seg_dir) if f.endswith(".wav")]
        self.assertEqual(len(wavs), expect)
        self.assertTrue(plan.get("_draft"), "全自动产出必须标记为草稿")

    def test_03_render_refuses_draft(self):
        r = self._run("render")
        self.assertEqual(r.returncode, 2, r.stdout.decode("utf-8", "replace"))

    def test_04_fill_draft_then_render_and_validate(self):
        plan_path = os.path.join(self.proj, "workspace/analysis/director_plan.json")
        with open(plan_path, encoding="utf-8") as fh:
            plan = json.load(fh)
        _fill_plan(plan)
        with open(plan_path, "w", encoding="utf-8") as fh:
            json.dump(plan, fh, ensure_ascii=False, indent=2)
        r = self._run("render", "--unattended")
        self.assertEqual(r.returncode, 0, r.stdout.decode("utf-8", "replace"))
        r2 = self._run("validate")
        self.assertEqual(r2.returncode, 0, r2.stdout.decode("utf-8", "replace"))

    def test_05_pack_delivery(self):
        r = self._run("pack", "--unattended")
        self.assertEqual(r.returncode, 0, r.stdout.decode("utf-8", "replace"))
        pack = os.path.join(self.proj, "output/latest/交付包")
        self.assertTrue(os.path.isdir(pack), r.stdout.decode("utf-8", "replace"))
        self.assertTrue(os.path.isfile(os.path.join(pack, "01-上传顺序与操作单.md")))

    def test_07_project_flag_before_subcommand_is_honoured(self):
        """`mvstudio.py --project X all` 与 `mvstudio.py all --project X` 必须等价。

        argparse 的子解析器默认值会**覆盖**父解析器已解析到的值，
        所以 --project 写在子命令之前会被静默丢掉——产物落到 skill 安装目录里。
        """
        other = os.path.join(self.tmp, "other_project")
        for sub in ("workspace", "output/latest", "output/archive",
                    "input/music", "input/character", "input/lyrics"):
            os.makedirs(os.path.join(other, sub), exist_ok=True)
        r = self._run("--project", other, "analyze", "--audio", self.audio)
        self.assertEqual(r.returncode, 0, r.stdout.decode("utf-8", "replace"))
        self.assertTrue(
            os.path.isfile(os.path.join(other, "workspace/analysis/music.json")),
            u"--project 放在子命令之前时没有被采纳；产物落到了别处")

    def test_08_unwritable_project_root_gives_actionable_advice(self):
        """项目根不可写时：不许抛 traceback，而且要给出**当前可写**的目录建议。

        典型场景：skill 装在只读/共享位置，或在受限沙箱里跑。
        """
        ro = os.path.join(self.tmp, "readonly-root")
        os.makedirs(ro, exist_ok=True)
        os.chmod(ro, 0o500)
        try:
            r = subprocess.run(
                [sys.executable, os.path.join(SCRIPTS, "mvstudio.py"),
                 "--project", ro, "doctor"],
                cwd=self.proj, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
            out = r.stdout.decode("utf-8", "replace")
            self.assertEqual(r.returncode, 4, out)
            self.assertNotIn("Traceback", out, u"抛了 traceback：%s" % out)
            self.assertIn("--project", out, u"没给出可操作的命令建议：%s" % out)
            # 建议必须是**当前环境里的可写位置**，不能是一个写死的 home 路径
            self.assertIn(self.proj, out,
                          u"建议的目录不是当前工作目录（写死的路径在沙箱里同样不可写）：%s"
                          % out)
        finally:
            os.chmod(ro, 0o700)

    def test_09_render_refuses_unconfirmed_steps(self):
        """每个步骤都要用户确认 —— 没确认就渲染，必须被拦住。"""
        r = self._run("render")
        self.assertEqual(r.returncode, 5, r.stdout.decode("utf-8", "replace"))
        out = r.stdout.decode("utf-8", "replace")
        self.assertIn(u"确认", out, out)
        self.assertIn("prompt-01", out, out)

    def test_10_confirm_records_and_unblocks(self):
        r = self._run("confirm", "--step", "canon", "--note", u"OK")
        self.assertEqual(r.returncode, 0, r.stdout.decode("utf-8", "replace"))
        r2 = self._run("confirm", "--status", "--json")
        self.assertEqual(r2.returncode, 0, r2.stdout.decode("utf-8", "replace"))
        data = json.loads(r2.stdout.decode("utf-8"))
        self.assertIn("canon", data["confirmed"])

    def test_11_default_route_is_mv_with_user_structure(self):
        """默认输出的每条提示词必须用用户指定的六段结构。"""
        r = self._run("render", "--unattended")
        self.assertEqual(r.returncode, 0, r.stdout.decode("utf-8", "replace"))
        with open(os.path.join(self.proj, "output/latest/minimax_h3_prompts.md"),
                  encoding="utf-8") as fh:
            text = fh.read()
        for k in (u"人物与参考保持一致性", u"风格提示词", u"内容提示词",
                  "integrated_multimodal_description", "overall_soundscape",
                  "non_diegetic_music"):
            self.assertIn(k, text, u"缺少结构段：%s" % k)
        self.assertIn("non_diegetic_music: N/A", text)

    def test_12_lastframe_extractor_is_reported(self):
        r = self._run("lastframe", "--report", "--json")
        self.assertEqual(r.returncode, 0, r.stdout.decode("utf-8", "replace"))
        data = json.loads(r.stdout.decode("utf-8"))
        self.assertIn(data["best"], ("ffmpeg", "avfoundation", "platform-export"))

    def test_13_pack_requires_render_and_validate_confirmation(self):
        """pack 比 render 多两道确认：render 与 validate 本身。

        「每一个步骤都要确认」意味着看完校验报告也要点一次头，
        而不是渲染成功就自动打包。
        """
        self._run("confirm", "--all")
        r = self._run("pack")
        self.assertEqual(r.returncode, 5, r.stdout.decode("utf-8", "replace"))
        out = r.stdout.decode("utf-8", "replace")
        self.assertIn("render", out, out)
        self.assertIn("validate", out, out)
        # 补确认后应当放行
        self._run("confirm", "--step", "render")
        self._run("confirm", "--step", "validate")
        r2 = self._run("pack")
        self.assertEqual(r2.returncode, 0, r2.stdout.decode("utf-8", "replace"))

    def test_06_over_three_minutes_is_blocked(self):
        long_wav = fixtures.write_click_track(
            os.path.join(self.tmp, "long.wav"), duration=185.0, bpm=120.0)
        r = self._run("gate", "--audio", long_wav, "--image", self.image, "--json")
        self.assertEqual(r.returncode, 3, r.stdout.decode("utf-8", "replace"))
        data = json.loads(r.stdout.decode("utf-8"))
        self.assertTrue(data["duration_gate"]["blocked"])


def _fill_plan(plan):
    """模拟导演填稿：把草稿里必须由人补的字段填满。"""
    plan["_draft"] = False
    plan["mv_concept"] = u"身体不变，世界不断更换画风"
    _mod("endings").apply_ending(plan, "reach_and_crack")
    plan["logline"] = u"一支舞穿过几种不同的艺术世界"
    plan["art_direction"] = dict(plan.get("art_direction") or {})
    plan["art_direction"].update({
        "primary_medium": "2D limited animation over risograph and graphite",
        "color_narrative": u"压抑段去饱和，主体恢复段回到角色原色",
        "why_this_medium": u"歌词讲的是被观看，印刷/错版正是被复制的视觉语言",
        "palette": ["#A8C8E8", "#D94A4A", "#1B1B1B"],
    })
    plan["visual_arc"] = [
        {"time_start": s["time_start"], "time_end": s["time_end"],
         "stage": "STAGE %d" % s["id"], "description": u"母题继续演化"}
        for s in plan["segments"]]
    plan["motif_dictionary"] = {
        "water": {"concept": "the self left behind", "visual_form": "flat ripple band",
                  "evolution": [u"水面", u"复制水纹", u"错版水纹", u"碎水纹", u"空水面"]}}
    plan["lyric_semantic_map"] = [
        {"time": s["time_start"], "lyric": (s.get("lyrics") or [u"（器乐）"])[0],
         "literal_meaning": u"字面", "emotional_meaning": u"情绪",
         "psychological_meaning": u"心理", "primary_visual_metaphor": u"主隐喻",
         "physical_object": u"实物", "character_action": u"动作",
         "transformation": u"转化"}
        for s in plan["segments"]]
    plan["character_canon"] = dict(plan.get("character_canon") or {})
    plan["character_canon"].update({
        "hair": "black bob with blunt bangs, chin length",
        "eyes": "large round dark brown eyes",
        "face": "round youthful face, small nose",
        "costume": "pale blue sailor-collar dress with a red ribbon",
        "accessories": "red neck ribbon, white knee socks",
        "silhouette": "short compact figure with a clear oval head shape",
        "stable_identifiers": ["red neck ribbon", "blunt bangs"],
    })
    plan["assets"] = {
        "character_reference": {"path": "input/character/character_ref.png",
                                "role": "character reference", "label": "<Picture 1>"},
        "turnaround_sheet": {"path": "workspace/character/threeview.png",
                             "role": "character turnaround reference",
                             "label": "<Picture 2>"},
        "audio": {"path": "input/music/song.wav",
                  "role": "original song reused 1:1", "label": "<Audio 1>"},
    }
    plan["segments"] = plan["segments"]
    for s in plan["segments"]:
        # 取**有内容的**那句歌词来推背景元素；器乐标记不能当内容
        content = [t for t in (s.get("lyrics") or []) if not _is_instrumental(t)]
        lyric_text = content[0] if content else u"（器乐）"
        s["central_meaning"] = u"这段歌词真正在讲的是主体被世界改写而自身不变"
        s["character_state"] = u"持续跳舞，重心稳定"
        s["primary_metaphor"] = u"水面复印主体"
        s["secondary_motif"] = u"错版水纹"
        bg = _bg_elements(lyric_text)
        s["background_lyric_elements"] = bg
        s["meaningful_objects"] = bg[:2]
        s["lyric_action_binding"] = [
            {"lyric": lyric_text, "action": "a slow arm sweep across the water",
             "beat": s.get("beat_start", 0)}]
        s["choreography"] = "step-touch into a slow arm sweep, weight low"
        s["environment_system"] = u"水面本身就是叙事装置，波纹随歌词扩张"
        s["art_movement"] = s.get("art_movement") or "rimpa"
        s["animation_medium"] = "animation on twos with held frames on downbeats"
        s["style_prompt"] = ("2D limited animation, hand-drawn, flat composition, "
                             "risograph misregistration, %s" % s["art_movement"])
        s["content_prompt"] = ("0-7s she dances while the background is built out of "
                               "%s; 7-14.5s the same elements reprint across the "
                               "background." % " ".join(bg))
        s["integrated_multimodal_description"] = (
            "the character reference, the original song and the printed world mutate together")
        s["overall_soundscape"] = "water laps against the bank."
        s["transition_in"] = "paper wipe"
        s["transition_out"] = "hard cut"
        s["continuity_from_previous"] = (u"承接上一段结尾抬起的右臂"
                                         if s["id"] > 1 else u"开场定调")
        s["hook_to_next"] = u"右臂继续抬起，留给下一段"
        if not s.get("shots"):
            s["shots"] = [{"index": 1, "start": 0.0,
                           "end": s["time_end"] - s["time_start"],
                           "beat_start": 0, "beat_end": 28,
                           "camera": "Static Shot", "camera_amplitude": "",
                           "camera_speed": "", "shot_size": "medium shot",
                           "action": "she keeps dancing", "cut": "hard cut",
                           "lyric": lyric_text}]
        for sh in s["shots"]:
            if not sh.get("camera"):
                sh["camera"] = "Static Shot"
            if not sh.get("camera_relation"):
                sh["camera_relation"] = (
                    _mod("camera").default_relation(sh["camera"]) or "observes")
            # 草稿里的 action 是占位符，必须换成真实编排
            sh["action"] = ("she steps through a step-touch and sweeps one arm across "
                            "the %s" % (bg[0] if bg else "frame"))
            sh["purpose"] = (u"露出她身后的%s" % (bg[0] if bg else u"平面世界")
                             if isinstance(sh.get("purpose"), str) else sh.get("purpose"))
            if not sh.get("purpose") or u"草稿" in str(sh.get("purpose")):
                sh["purpose"] = "reveal the printed world behind her"
    return plan


def _is_instrumental(text):
    t = (text or "").strip()
    if not t:
        return True
    return bool(re.match(r"^[（(\[].*[）)\]]$", t))


def _bg_elements(lyric):
    """从这句歌词里取背景元素（模拟导演真的读歌词）。"""
    if _is_instrumental(lyric):
        return [u"空水面"]        # 器乐段：用母题元素，不伪造歌词
    pool = [u"水面", u"波纹", u"影子", u"夕阳", u"池塘", u"荷叶", u"蓝色",
            u"王子", u"岸边", u"名字", u"光", u"舞", u"圈"]
    hits = [w for w in pool if w in lyric]
    if not hits:
        core = u"".join(ch for ch in lyric if u"\u4e00" <= ch <= u"\u9fff")
        hits = [core[i:i + 2] for i in range(0, min(4, len(core) - 1), 2)] or [u"图形"]
    return hits[:3]


if __name__ == "__main__":
    unittest.main(verbosity=2)
