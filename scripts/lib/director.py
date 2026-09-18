#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""director —— 把实测结果拼成**草稿导演稿**，并把「必须由人补的三处」标出来。

立场（直接继承两份母技能踩出来的结论）：
  **机器负责机械的部分，人负责审美的部分。**
  自动指派一定会有不对的地方——风格和歌词的对应是审美判断，不是可计算结论。
  所以草稿会带上 `_draft: true`，渲染器见到它就拒绝输出，直到人把该填的填了。

必须由人补的三处（草稿里用「（草稿：…）」标出来）：
  1. 每一镜的 `action`   —— 把动作库候选变成「这一镜身体具体怎么动」是编排，不是检索
  2. 每段的语义          —— central_meaning / 母题 / 环境系统，是理解，不是统计
  3. 背景里的歌词元素    —— 用户的硬要求，必须能从这句歌词推出来
"""

import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common  # noqa: E402
import beats as beats_mod  # noqa: E402
try:
    import camera as camera_mod
except Exception:  # pragma: no cover
    camera_mod = None
try:
    import motion as motion_mod
except Exception:  # pragma: no cover
    motion_mod = None

# 景别优先从 camera-library 的 shot_sizes 取（10 个有出处的景别）；
# 库不可用时退回这一份等价的英文写法。
SHOT_SIZES = ["medium shot", "close-up", "wide shot", "medium close-up",
              "full shot", "extreme close-up"]


def _shot_size_id(i):
    """按轮换挑景别 id（单人 MV 可用集合）。"""
    if camera_mod is None:
        return None
    ids = [s["id"] for s in camera_mod.shot_sizes(solo_only=True)]
    if not ids:
        return None
    # 人物动作的主场占多数：中景系优先
    rotation = [x for x in ("medium_shot", "medium_long_shot", "close_up",
                            "full_shot", "medium_close_up", "wide_shot",
                            "extreme_close_up", "insert_shot",
                            "extreme_wide_shot") if x in ids] or ids
    return rotation[i % len(rotation)]


def _enforce_camera_cap(shots):
    """运镜丰富 ≠ 运镜展览：运动镜头 ≤ ceil(n/2)，其余压回固定镜头。

    这是用户定的红线，也是保住 limited animation 手感的关键。
    """
    n = len(shots)
    if n == 0:
        return shots
    cap = -(-n // 2)
    moving = [i for i, s in enumerate(shots) if s.get("camera") != "Static Shot"]
    if len(moving) <= cap:
        return shots
    # 从后往前压回，保留开头的运动镜头（开场那一下最有效）
    for i in reversed(moving[cap:]):
        s = shots[i]
        s["camera"] = "Static Shot"
        s["camera_amplitude"] = ""
        s["camera_speed"] = ""
        if camera_mod is not None:
            s["camera_relation"] = camera_mod.default_relation("Static Shot")
    return shots

# 允许的 2D 运镜（官方词表里挑出来不会破坏平面感的）
DEFAULT_CAMERAS = ["Static Shot", "Push In", "Pan Right", "Pull Out", "Pan Left",
                   "Truck Left", "Zoom In", "Pedestal Up", "Truck Right", "Tilt Down"]

CREATIVE_FIELDS = [
    "central_meaning", "character_state", "primary_metaphor", "secondary_motif",
    "background_lyric_elements", "meaningful_objects", "choreography",
    "environment_system", "art_movement", "animation_medium", "style_prompt",
    "content_prompt", "integrated_multimodal_description", "overall_soundscape",
    "transition_in", "transition_out", "continuity_from_previous", "hook_to_next",
]

DRAFT_MARK = u"（草稿："


def _draft(text):
    return DRAFT_MARK + text + u"）"


def animation_medium_for(analysis, seg_energy=None):
    """起音密度决定抽帧程度 —— 这是「音乐分析必须真的影响画面」的一条。"""
    density = (analysis or {}).get("rhythmic_density") or 0
    if density < 1.2:
        return ("animation on twos with a held frame on every downbeat; "
                "sparse keys, no smoothing")
    if density < 2.5:
        return ("animation on twos with stepped accents on the backbeat and "
                "occasional smear frames")
    return ("animation on ones for accents and on twos elsewhere, with dense "
            "smear frames and replacement animation")


def energy_for(analysis, start, end):
    """这一段落在 quiet / mid / peak 的哪一档。"""
    st = (analysis or {}).get("structure") or {}
    for key, label in (("peak_sections", "peak"), ("build_sections", "build"),
                       ("breakdowns", "breakdown"), ("quiet_sections", "quiet")):
        for sec in st.get(key) or []:
            try:
                if float(sec.get("start", 0)) <= (start + end) / 2.0 <= float(sec.get("end", 0)):
                    return label
            except Exception:
                continue
    return "mid"


def beat_range(start, end, grid):
    """段的起止落在第几拍。**按时间求最近拍**，不要求边界正好在整拍上。

    原来用 beats._index_of 做精确相等匹配，段边界只要差一点点就返回 None，
    于是整段被判为「没有可靠拍网格」——降级路径被触发的频率远超预期。
    """
    if not grid:
        return None
    b0 = beats_mod.beat_at(grid, float(start))
    b1 = beats_mod.beat_at(grid, float(end))
    if b0 is None or b1 is None:
        return None
    return (b0, b1)


def build_shots(seg, grid, cameras, shot_size_seed=0, min_shots=2, max_shots=4):
    """把一段音乐窗切成 2–4 个镜头，切点落在小节线上（退而求其次落拍线）。"""
    start, end = seg["start"], seg["end"]
    total = end - start
    if total <= 0:
        return []
    n = max(min_shots, min(max_shots, int(round(total / 4.5)) or min_shots))
    cuts = []
    for k in range(1, n):
        ideal = start + total * k / float(n)
        cand = None
        if grid:
            snap = beats_mod.snap_time(ideal, grid, tolerance_beats=2.0)
            if snap["snapped_to"] in ("bar", "beat") and start < snap["time"] < end:
                cand = snap["time"]
        cuts.append(cand if cand is not None else round(ideal, 6))
    bounds = [start] + cuts + [end]
    shots = []
    prev_cam = None
    for i in range(len(bounds) - 1):
        s0, s1 = bounds[i], bounds[i + 1]
        cam = None
        for j in range(len(cameras)):
            c = cameras[(shot_size_seed + i * 3 + j) % len(cameras)]
            if c != prev_cam:
                cam = c
                break
        cam = cam or cameras[0]
        prev_cam = cam
        amp = "" if cam == "Static Shot" else (
            "with large amplitude" if (i % 2 == 1) else "with small amplitude")
        speed = "" if cam == "Static Shot" else (
            "at fast speed" if (i % 2 == 1) else "at slow speed")
        size_id = _shot_size_id(shot_size_seed + i)
        size_en = SHOT_SIZES[(shot_size_seed + i) % len(SHOT_SIZES)]
        energy = seg.get("energy")
        shot = {
            "index": i + 1,
            "start": round(s0 - start, 6),
            "end": round(s1 - start, 6),
            "absolute_start": round(s0, 6),
            "absolute_end": round(s1, 6),
            "beat_start": beats_mod.beat_at(grid, s0) if grid else None,
            "beat_end": beats_mod.beat_at(grid, s1) if grid else None,
            "camera": cam,
            "camera_amplitude": amp,
            "camera_speed": speed,
            "camera_target": "",
            "shot_size": size_en,
            "action": _draft(u"这一镜身体具体怎么动（必须绑定本段歌词，"
                             u"并把重拍落在动作的 accent 上）"),
            "cut": "hard cut" if i < len(bounds) - 2 else "none",
            "lyric": "",
        }
        if camera_mod is not None:
            shot["shot_size_id"] = size_id
            shot["angle"] = camera_mod.pick_angle(i, energy=energy)
            shot["framing"] = camera_mod.pick_composition(i)
            shot["focus"] = camera_mod.pick_focus(size_id, energy=energy)
            shot["camera_relation"] = camera_mod.default_relation(cam)
            shot["purpose"] = _draft(u"这一下要揭示什么（答不出就删掉这个切）")
            shot["move_2d"] = None
        shots.append(shot)

    if camera_mod is not None:
        shots = _enforce_camera_cap(shots)
        # 2D 专属招加在**机位不动**的镜头上：机位锁死，画面仍在动 ——
        # 这正是 limited animation 的手感来源，而且完全不破坏平面感。
        flat_ids = [m["id"] for m in camera_mod.moves_2d()
                    if m["id"] not in ("paper_wipe", "split_screen")]
        # 用段号做偏移：否则每一段的「第一招」都是同一个，等于没有变化
        k = shot_size_seed
        for sh in shots:
            if sh.get("camera") == "Static Shot" and flat_ids:
                sh["move_2d"] = flat_ids[k % len(flat_ids)]
                k += 1
    return shots


def _lyrics_in_window(lyric_lines, start, end):
    inside, carry = [], []
    for ln in lyric_lines or []:
        try:
            ls, le = float(ln.get("start") or 0), float(ln.get("end") or ls)
        except Exception:
            continue
        if ls < end and le > start:
            inside.append(ln)
            if ls < start - 1e-6 or le > end + 1e-6:
                carry.append(ln)
    return inside, carry


def build_draft(duration, analysis, lyric_lines, canon, segs, styles,
                meta_extra=None, image=None, turnaround=None, audio=None):
    """产出草稿导演稿。`_draft` 为 True 时渲染器会拒绝输出。"""
    lyric_lines = lyric_lines or []
    grid = None
    bpm = (analysis or {}).get("bpm")
    if bpm:
        grid = beats_mod.beat_grid(bpm, duration,
                                   phase=float((analysis or {}).get("phase") or 0.0))
    routes = styles or []
    route = routes[0] if routes else {"id": "none", "name": u"（未选路线）",
                                      "movement_per_segment": [], "medium": "", "pool": []}
    per = list(route.get("movement_per_segment") or [])
    pool = list(route.get("pool") or ["rimpa"])
    while len(per) < len(segs):
        per.append(pool[len(per) % len(pool)])

    out_segments = []
    for i, s in enumerate(segs):
        inside, carry = _lyrics_in_window(lyric_lines, s["start"], s["end"])
        texts = [ln.get("text") for ln in inside if ln.get("text")]
        durs = s.get("delivered_seconds") or s["length"]
        seg = {
            "id": s["index"],
            "label": s["label"],
            "time_start": s["start"],
            "time_end": s["end"],
            "audio_seconds": s.get("audio_seconds", s["length"]),
            "request_seconds": s.get("request_seconds"),
            "delivered_seconds": s.get("delivered_seconds"),
            "headroom_seconds": s.get("headroom_seconds"),
            "seam_overlap_seconds": s.get("seam_overlap_seconds"),
            "prompt_seconds": max(durs, s["length"]),
            "is_tail": s.get("is_tail", False),
            "is_tail_pad": bool(s.get("is_tail") and s.get("is_tail_pad")),
            "tail_advice": s.get("tail_advice"),
            "snapped_to": s.get("snapped_to"),
            "offset_beats": s.get("offset_beats"),
            "bar_start": (s.get("bar_index") or 0) + 1 if s.get("bar_index") is not None else None,
            "bar_end": None,
            "beat_start": s.get("beat_index"),
            "beat_end": None,
            "lyrics": texts,
            "lyric_lines": inside,
            "lyric_carry_over": bool(carry),
            "energy": energy_for(analysis, s["start"], s["end"]),
            "motion": None,          # 由 motion.build_all 填：魔性度 + 循环表
            "art_movement": per[i] if i < len(per) else pool[i % len(pool)],
            "animation_medium": animation_medium_for(analysis),
            "central_meaning": "",
            "character_state": "",
            "primary_metaphor": "",
            "secondary_motif": "",
            "background_lyric_elements": [],
            "meaningful_objects": [],
            "lyric_action_binding": [],
            "choreography": _draft(u"这一段的舞蹈：动作与歌词、与重拍的关系"),
            "environment_system": "",
            "style_prompt": "",
            "content_prompt": "",
            "integrated_multimodal_description": "",
            "overall_soundscape": _draft(u"环境音 + 身体动作音（不要描述配乐）"),
            "camera": "",
            "transition_in": "",
            "transition_out": "",
            "continuity_from_previous": _draft(u"承接上一段结尾的哪一个动作元素")
            if i > 0 else u"开场：建立人物与世界的第一次关系",
            # 尾帧续接：chain 由 chain.build_chain 填；这里只放必须由人写的部分
            "chain": None,
            "chain_continuity": (_draft(u"起手怎么接上一帧的姿势（不要换姿势，只做同族连续动作）")
                                 if i > 0 else u""),
            "hook_to_next": _draft(u"给下一段留的动作接口"),
            "shots": build_shots(s, grid, DEFAULT_CAMERAS, shot_size_seed=i),
        }
        # 拍号：按时间求最近拍（原来用精确索引匹配，边界一差就变 None）
        _br = beat_range(s["start"], s["end"], grid)
        if _br:
            seg["beat_start"], seg["beat_end"] = _br
        # 小节编号
        if s.get("bar_index") is not None:
            nxt = None
            for j in range(i + 1, len(segs)):
                if segs[j].get("bar_index") is not None:
                    nxt = segs[j]["bar_index"] + 1
                    break
            seg["bar_end"] = nxt
        if not _br:
            nxt_beat = None
            for j in range(i + 1, len(segs)):
                if segs[j].get("beat_index") is not None:
                    nxt_beat = segs[j]["beat_index"]
                    break
            seg["beat_end"] = nxt_beat
        # 每镜挂上它覆盖到的歌词
        for sh in seg["shots"]:
            for ln in inside:
                try:
                    ls = float(ln.get("start") or 0) - s["start"]
                except Exception:
                    continue
                if ls < (sh["end"] or 0) or sh["index"] == 1:
                    sh["lyric"] = ln.get("text") or ""
                    break
        out_segments.append(seg)

    meta = {
        "duration": round(float(duration), 4),
        "segment_target_seconds": beats_mod.defaults()[0],
        "segment_count": len(out_segments),
        "bpm": bpm,
        "bpm_raw": (analysis or {}).get("bpm_raw"),
        "beat_sec": round(60.0 / bpm, 6) if bpm else None,
        "bar_sec": round(60.0 / bpm * 4, 6) if bpm else None,
        "rhythmic_density": (analysis or {}).get("rhythmic_density"),
        "analysis_engine": (analysis or {}).get("engine"),
        "lyric_mode": "lyrics" if any(s.get("lyrics") for s in out_segments)
                      else "instrumental",
        "h3_route": "ref",
        "lang": "en",
        "style_route": route.get("id"),
        "audio_cutter_ok": True,
    }
    meta.update(meta_extra or {})

    plan = {
        "_draft": True,
        "_draft_note": (u"草稿：必须由导演（Agent）填写/改写标着「（草稿：…）」的字段，"
                        u"并补全 mv_concept / lyric_semantic_map / motif_dictionary / "
                        u"visual_arc / 每段的语义字段与背景歌词元素，"
                        u"然后才能渲染。"),
        "_must_fill": CREATIVE_FIELDS,
        "meta": meta,
        "mv_concept": "",
        "logline": "",
        "ending": None,          # 由 endings.apply_ending 填；全片最后一下
        "motion_design": {"hook_id": None},   # 由 motion.apply_hook 填；全片唯一 hook
        "visual_arc": [],
        "motif_dictionary": {},
        "lyric_semantic_map": [],
        "art_direction": {
            "route_id": route.get("id"),
            "route_name": route.get("name"),
            "movements": sorted(set(per[:len(out_segments)])),
            "movement_per_segment": per[:len(out_segments)],
            "primary_medium": route.get("medium"),
            "palette": route.get("palette"),
            "why_this_medium": route.get("why"),
            "style_negative": route.get("negative"),
        },
        "character_canon": canon or {},
        "assets": {
            "character_reference": {"path": (image or {}).get("path") if isinstance(image, dict) else image,
                                    "role": "character reference",
                                    "label": "<Picture 1>"},
            "turnaround_sheet": {"path": (turnaround or {}).get("path") if isinstance(turnaround, dict) else turnaround,
                                 "role": "character turnaround reference",
                                 "label": "<Picture 2>"},
            "audio": {"path": (audio or {}).get("path") if isinstance(audio, dict) else audio,
                      "role": "original song reused 1:1", "label": "<Audio 1>"},
        },
        "segments": out_segments,
        "quality_gates": {},
    }
    # 魔性动作：逐段推魔性度 + 循环表（hook 由用户挑，见 mvstudio.py motion）
    if motion_mod is not None:
        try:
            motion_mod.build_all(plan, analysis)
        except Exception:
            pass
    return plan


def render_worksheet(plan):
    """人读的导演工作表：逐段列出该填什么，不替你写。"""
    segs = plan.get("segments") or []
    meta = plan.get("meta") or {}
    lines = [u"# 导演工作表（要你填的就是这些）", ""]
    lines.append(u"> 机器已经做完的：音乐实测、拍网格、14.5 秒切分、画风指派、"
                 u"运镜词表校验、时间换算。")
    lines.append(u"> **剩下的是理解与编排，机器做不了。**")
    lines.append("")
    lines.append(u"## 全局")
    lines.append("")
    lines.append(u"| 项 | 值 |")
    lines.append(u"|----|----|")
    lines.append(u"| 时长 | %.3f s |" % (meta.get("duration") or 0))
    lines.append(u"| BPM | %s |" % (meta.get("bpm") or u"未测出"))
    lines.append(u"| 拍 / 小节 | %.4f s / %.4f s |"
                 % (meta.get("beat_sec") or 0, meta.get("bar_sec") or 0))
    lines.append(u"| 段数 | %s（%.1f 秒 × %s）|"
                 % (meta.get("segment_count"), meta.get("segment_target_seconds"),
                    meta.get("segment_count")))
    lines.append(u"| 歌词模式 | %s |" % meta.get("lyric_mode"))
    lines.append(u"| 画风路线 | %s |" % meta.get("style_route"))
    lines.append("")
    lines.append(u"- [ ] `mv_concept`：一句话核心概念（**这条决定全片**）")
    lines.append(u"- [ ] `visual_arc`：视觉发展弧线，**必须由歌词推出**，不许套模板")
    lines.append(u"- [ ] `motif_dictionary`：母题 + 它的**演化链**"
                 u"（例：镜框 → 复制镜框 → 错版镜框 → 碎裂框架 → 空框）")
    lines.append(u"- [ ] `lyric_semantic_map`：逐句理解"
                 u"（字面／情感／心理／主隐喻／实物／动作／转化）")
    lines.append(u"- [ ] `art_direction.why_this_medium`："
                 u"回答「这个媒介为什么属于这首歌」")
    lines.append("")
    lines.append(u"## 逐段")
    lines.append("")
    lines.append(u"| 段 | 时间 | H3 duration | 歌词 | 画风 | 能量 |")
    lines.append(u"|----|------|-------------|------|------|------|")
    for s in segs:
        lines.append(u"| %s | %.3f–%.3f | %ss（音乐 %.3fs）| %s | `%s` | %s |"
                     % (s.get("label"), s.get("time_start"), s.get("time_end"),
                        s.get("request_seconds"), s.get("audio_seconds"),
                        u" ／ ".join(s.get("lyrics") or []) or u"〔器乐〕",
                        s.get("art_movement"), s.get("energy")))
    lines.append("")
    for s in segs:
        lines.append(u"### %s　%.3f–%.3f s" % (s.get("label"), s.get("time_start"),
                                               s.get("time_end")))
        lines.append("")
        if s.get("lyric_carry_over"):
            lines.append(u"> ⚠️ 这一段的歌词**跨了边界**：相邻两段必须表达同一意象，"
                         u"不许因为 14.5 秒到了就换场景。")
            lines.append("")
        for f in ("central_meaning", "character_state", "primary_metaphor",
                  "secondary_motif", "environment_system", "choreography"):
            lines.append(u"- [ ] `%s`：%s" % (f, s.get(f) or u"**待填**"))
        lines.append(u"- [ ] `background_lyric_elements`："
                     u"把这段歌词里的**实物**放进背景里（用户硬要求）")
        _m = s.get("motion") or {}
        if _m:
            lines.append(u"- [ ] `motion`（魔性动作）：档 **%s**、动作单元 %s 拍、"
                         u"重复 %s 次、变异点 %s、hook `%s`"
                         u"　__想让这一段更魔性就调高 `viral_level`（0–3）__"
                         % (_m.get("viral_name_cn") or u"—", _m.get("unit_beats"),
                            _m.get("repeats"),
                            _m.get("mutation_at") or u"—",
                            _m.get("hook_id") or u"（还没挑）"))
        lines.append(u"- [ ] `style_prompt`：必须含 "
                     u"2D / limited animation / hand-drawn / flat composition")
        lines.append(u"- [ ] `content_prompt`：按歌词自然分段写（0–Xs / Xs–Ys …）")
        lines.append(u"- [ ] `overall_soundscape`：只写环境音与身体动作音，"
                     u"**不要描述配乐**")
        lines.append(u"- [ ] `hook_to_next` / `continuity_from_previous`："
                     u"整条要连成**一支持续的舞**")
        lines.append("")
        lines.append(u"| 镜 | 本地时间 | 拍 | 景别 | 角度 | 构图 | 焦 | "
                     u"2D 招 | 运镜（官方词） | 速度 | 关系 | 切 |")
        lines.append(u"|----|---------|----|------|------|------|----|"
                     u"-------|---------------|------|------|-----|")
        for sh in s.get("shots") or []:
            lines.append(u"| %d | %.3f–%.3f | %s→%s | %s | %s | %s | %s | %s | `%s` | %s | %s | %s |"
                         % (sh.get("index"), sh.get("start"), sh.get("end"),
                            sh.get("beat_start"), sh.get("beat_end"),
                            sh.get("shot_size_id") or sh.get("shot_size"),
                            sh.get("angle") or u"—", sh.get("framing") or u"—",
                            sh.get("focus") or u"—", sh.get("move_2d") or u"—",
                            sh.get("camera"),
                            sh.get("camera_speed") or u"—",
                            sh.get("camera_relation") or u"—", sh.get("cut")))
        lines.append("")
        lines.append(u"> 运镜按**六层**来：景别 / 角度 / 构图 / 焦 / 2D 招 / 官方运动词 + 关系。"
                     u"完整词表见 `references/camera-vocabulary.md`，"
                     u"或用 `python3 scripts/mvstudio.py camera --md` 打印。")
        lines.append("")
        lines.append(u"**这一镜身体具体怎么动**（逐镜填 `action`）：")
        lines.append("")
        for sh in s.get("shots") or []:
            lines.append(u"- [ ] 镜头 %d（%s / %s → %s）：%s"
                         % (sh.get("index"), sh.get("angle") or u"—",
                            sh.get("camera"), sh.get("end"),
                            sh.get("action") or u"**待填**"))
            lines.append(u"      - [ ] 这一下**要揭示什么**（`purpose`）：%s"
                         % (sh.get("purpose") or u"**待填**"))
        lines.append("")
    return "\n".join(lines) + "\n"


def fill_check(plan):
    """草稿还缺哪些必须由人补的东西。"""
    miss = []
    segs = plan.get("segments") or []
    if not str(plan.get("mv_concept") or "").strip():
        miss.append("mv_concept")
    if not (plan.get("visual_arc") or []):
        miss.append("visual_arc")
    if not (plan.get("motif_dictionary") or {}):
        miss.append("motif_dictionary")
    if not (plan.get("lyric_semantic_map") or []):
        miss.append("lyric_semantic_map")
    for s in segs:
        for f in CREATIVE_FIELDS:
            v = s.get(f)
            if v is None or (isinstance(v, str) and not v.strip()) or v == []:
                miss.append("%s.%s" % (s.get("label"), f))
        for sh in s.get("shots") or []:
            if DRAFT_MARK in str(sh.get("action") or ""):
                miss.append("%s.shot%d.action" % (s.get("label"), sh.get("index")))
        for f in ("continuity_from_previous", "hook_to_next"):
            if DRAFT_MARK in str(s.get(f) or ""):
                miss.append("%s.%s" % (s.get("label"), f))
    return miss
