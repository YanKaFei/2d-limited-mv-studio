#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""mvstudio.py —— 2d-limited-mv-studio 统一入口。

  doctor      环境体检（工具 / 模块 / 风格库 / 配置完整性）
  gate        第 0 步：材料闸门 + 时长闸门（>180s 直接失败）
  analyze     音乐实测（BPM / 拍网格 / 起音密度 / 段落能量）
  lyrics      歌词时间轴（内嵌 → lrc/srt/vtt/txt → ASR 草稿）
  canon       人物 Canon 骨架 + 工作副本（语义字段由 Agent 看图填）
  threeview   三视图规格与提示词
  styles      画风融合路线菜单（给用户挑）｜ --pick <id> 应用
  segments    14.5 秒切分 + 真的切音频 + 草稿导演稿 + 工作表
  render      渲染 MiniMax H3 原生提示词（草稿会被拒绝）
  validate    交付校验（未通过不许说 DONE）
  pack        打「上传交付包」，任何画布都能跑
  all         一次跑完所有**确定性**步骤（创意仍必须由导演填）
"""

import argparse
import os
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "lib"))

import common  # noqa: E402
import audioprobe  # noqa: E402
import beats as beats_mod  # noqa: E402
import camera as camera_mod  # noqa: E402
import canon as canon_mod  # noqa: E402
import chain as chain_mod  # noqa: E402
import confirm as confirm_mod  # noqa: E402
import director as director_mod  # noqa: E402
import endings as endings_mod  # noqa: E402
import frames as frames_mod  # noqa: E402
import gates as gates_mod  # noqa: E402
import h3render  # noqa: E402
import materials as materials_mod  # noqa: E402
import pack as pack_mod  # noqa: E402
import platforms as platforms_mod  # noqa: E402
import slicer as slicer_mod  # noqa: E402
import styleroutes as styles_mod  # noqa: E402
import threeview as threeview_mod  # noqa: E402


# ------------------------------------------------------------------ 工具
def _archive_latest():
    latest = common.path("output_latest")
    if not os.path.isdir(latest):
        return None
    entries = [f for f in os.listdir(latest) if not f.startswith(".")]
    if not entries or all(f == "README.txt" for f in entries):
        return None
    dest = os.path.join(common.path("output_archive"), common.stamp())
    os.makedirs(dest, exist_ok=True)
    for name in entries:
        src = os.path.join(latest, name)
        dst = os.path.join(dest, name)
        if os.path.isdir(src):
            shutil.copytree(src, dst, dirs_exist_ok=True)
            shutil.rmtree(src)
        else:
            shutil.move(src, dst)
    return dest


def _load_analysis():
    return common.read_json(os.path.join(common.path("workspace_analysis"),
                                         "music.json"), {}) or {}


def _load_lyrics():
    return common.read_json(os.path.join(common.path("workspace_lyrics"),
                                         "lyrics_timeline.json"), {}) or {}


def _load_plan():
    return common.read_json(os.path.join(common.path("workspace_analysis"),
                                         "director_plan.json"), {}) or {}


def _save_plan(plan):
    p = os.path.join(common.path("workspace_analysis"), "director_plan.json")
    common.write_json(p, plan)
    return p


# ------------------------------------------------------------------ 各步
def step_doctor(args):
    res = materials_mod.doctor()
    if args.json:
        common.emit(res, True)
    else:
        common.echo(u"2d-limited-mv-studio 环境体检")
        common.echo(u"  Python      %s" % res["python"])
        for k, v in res["tools"].items():
            common.echo(u"  %-11s %s" % (k, v or u"缺失"))
        common.echo(u"  切分能力    %s" % res["audio_cutter"])
        common.echo(u"  风格库      %s" % (u"可用" if res["artvault"].get("available")
                                          else u"不可用（降级到内置媒介池）"))
        seg = res["segment"]
        common.echo(u"  生成单元    %.1fs（H3 上限 %ss）｜ 最多 %s 条"
                    % (seg["target_seconds"], seg["hard_max_seconds"],
                       seg["max_prompts"]))
        common.echo(u"  %s" % seg["h3_duration_rule"])
        if res["warnings"]:
            common.echo("")
            for w in res["warnings"]:
                common.echo(u"  ⚠️ %s" % w)
        else:
            common.echo(u"\n  ✅ 全绿")
    return 0


def step_gate(args):
    found = materials_mod.discover(args.audio, args.image, args.lyrics)
    if found.get("audio"):
        found["duration_gate"] = materials_mod.duration_gate(found["audio"]["path"])
    else:
        found["duration_gate"] = {"blocked": True, "readable": False,
                                  "message": u"没有音频，无法判定时长"}
    code = 3 if (found["blockers"] or found["duration_gate"].get("blocked")) else 0
    if args.json:
        common.emit(found, True)
    else:
        common.echo(u"【材料闸门】")
        common.echo(u"  音频    %s" % (found.get("audio") or {}).get("path", u"（缺）"))
        common.echo(u"  人物图  %s" % (found.get("image") or {}).get("path", u"（缺）"))
        common.echo(u"  三视图  %s" % (found.get("turnaround") or {}).get("path", u"（无）"))
        common.echo(u"  歌词    %s" % (found.get("lyrics") or {}).get("path", u"（缺，降级）"))
        common.echo("")
        common.echo(u"【时长闸门】")
        common.echo(u"  %s" % found["duration_gate"].get("message", ""))
        if found["blockers"]:
            common.echo("")
            for b in found["blockers"]:
                common.echo(u"  ✖ %s" % b)
        if found["notes"]:
            common.echo("")
            for n in found["notes"]:
                common.echo(u"  · %s" % n)
    return code


def step_analyze(args):
    import music as music_mod  # noqa: E402
    found = materials_mod.discover(args.audio, args.image, args.lyrics)
    if not found.get("audio"):
        common.echo(u"没有音频：把音乐放进 input/music/")
        return 3
    path = found["audio"]["path"]
    gate = materials_mod.duration_gate(path)
    if gate.get("blocked"):
        common.echo(gate.get("message"))
        return 3
    analysis = music_mod.analyze(path)
    analysis["path"] = path
    common.write_json(os.path.join(common.path("workspace_analysis"), "music.json"),
                      analysis)
    common.write_text(os.path.join(common.path("output_latest"), "music_analysis.md"),
                      music_mod.render_md(analysis))
    if args.json:
        common.emit({"analysis_path": os.path.join(common.path("workspace_analysis"),
                                                   "music.json"),
                     "bpm": analysis.get("bpm"),
                     "duration": analysis.get("duration"),
                     "engine": analysis.get("engine"),
                     "degraded": analysis.get("degraded")}, True)
    else:
        common.echo(u"音乐实测：引擎=%s 时长=%.2fs BPM=%s 起音密度=%s"
                    % (analysis.get("engine"), analysis.get("duration") or 0,
                       analysis.get("bpm") or u"未测出",
                       analysis.get("rhythmic_density")))
        st = analysis.get("structure") or {}
        for sec in st.get("sections") or []:
            common.echo(u"  %-8s %7.2f–%7.2f  %s"
                        % (sec.get("label"), sec.get("start"), sec.get("end"),
                           sec.get("energy")))
    return 0


def step_lyrics(args):
    import lyricsrc  # noqa: E402
    found = materials_mod.discover(args.audio, args.image, args.lyrics)
    audio = (found.get("audio") or {}).get("path")
    src = found.get("lyrics") or {}
    path = src.get("path") if isinstance(src, dict) else src
    duration = None
    if audio:
        duration = audioprobe.probe(audio).get("duration")

    out = {"mode": "none", "lines": [], "source": None, "language": None,
           "estimated": False, "needs_manual_lyrics": False, "warnings": []}

    if path and os.path.isfile(path):
        parsed = lyricsrc.parse_lyrics_file(path) or {}
        lines = parsed.get("lines") or []
        out.update({"mode": "lyrics", "lines": lines, "source": path,
                    "language": parsed.get("language_hint"),
                    "timed": parsed.get("timed"),
                    "confidence": parsed.get("confidence")})
        if not parsed.get("timed"):
            # 无时间轴：允许均分兜底，但必须标 estimated
            if duration:
                out["lines"] = lyricsrc.spread_untimed(lines, 0.0, duration)
                out["estimated"] = True
                out["warnings"].append(
                    u"这份歌词**没有时间轴**，已按整曲时长均分兜底（estimated）。"
                    u"精度低于 LRC/ASR，建议补一份 .lrc。")
            else:
                out["needs_manual_lyrics"] = True
                out["warnings"].append(u"歌词没有时间轴，也读不到音频时长，无法对齐。")
    elif lyricsrc.asr_available() and audio:
        res, backend = lyricsrc.run_asr(audio, model=getattr(args, "asr_model", "small"))
        lines = (res or {}).get("lines") or []
        if lines:
            for l in lines:
                if "[ASR" not in (l.get("text") or ""):
                    l["text"] = (l.get("text") or "") + "  [ASR uncertain]"
            out.update({"mode": "lyrics", "lines": lines, "source": "asr:%s" % backend,
                        "needs_manual_lyrics": True, "estimated": True})
            out["warnings"].append(
                u"⚠️ 歌词来自 ASR **草稿**，必须人工核对后使用——"
                u"实测把「王子」转成过「滑走」。定稿请把 .lrc/.srt/.vtt/.txt "
                u"放进 input/lyrics/ 后重跑。")

    if not out["lines"]:
        out["mode"] = "instrumental"
        out["needs_manual_lyrics"] = True
        out["warnings"].append(
            u"拿不到可靠歌词 → 切换 **Music-Semantic Mode**："
            u"用节奏、音色、能量、和声情绪与结构变化设计视觉，而不是放弃。")

    common.write_json(os.path.join(common.path("workspace_lyrics"),
                                   "lyrics_timeline.json"), out)
    common.write_text(os.path.join(common.path("output_latest"), "lyrics_timeline.md"),
                      _lyrics_md(out))
    if getattr(args, "json", False):
        common.emit(out, True)
    else:
        common.echo(u"歌词：模式=%s 来源=%s 行数=%d%s"
                    % (out["mode"], out["source"], len(out["lines"]),
                       u"（时间轴为估算）" if out.get("estimated") else u""))
        for w in out["warnings"]:
            common.echo(u"  ⚠️ %s" % w)
    return 0


def _lyrics_md(out):
    lines = [u"# 歌词时间轴", ""]
    lines.append(u"- 模式：%s" % out.get("mode"))
    lines.append(u"- 来源：%s" % out.get("source"))
    lines.append(u"- 语言：%s" % out.get("language"))
    if out.get("needs_manual_lyrics"):
        lines.append(u"- ⚠️ **需要人工核对**")
    lines.append("")
    for w in out.get("warnings") or []:
        lines.append(u"> %s" % w)
        lines.append("")
    lines.append(u"| 起点 | 终点 | 歌词 |")
    lines.append(u"|------|------|------|")
    for l in out.get("lines") or []:
        lines.append(u"| %.2f | %.2f | %s |"
                     % (l.get("start") or 0, l.get("end") or 0, l.get("text") or ""))
    lines.append("")
    return "\n".join(lines) + "\n"


def step_canon(args):
    found = materials_mod.discover(args.audio, args.image, args.lyrics)
    img = (found.get("image") or {}).get("path") or args.image
    if not img or not os.path.isfile(img):
        common.echo(u"没有人物参考图：把图放进 input/character/")
        return 3
    turn = (found.get("turnaround") or {}).get("path")
    res = canon_mod.run(img, turn, args.name)
    out = os.path.join(common.path("workspace_character"), "character_canon.json")
    common.write_json(out, res["canon"])
    checklist = threeview_mod.consistency_checklist(res["canon"])
    common.write_text(os.path.join(common.path("output_latest"), "character_canon.md"),
                      canon_mod.render_md(res["canon"], res["measure"], checklist))
    # 三视图同步出
    spec = threeview_mod.build_spec(res["canon"])
    common.write_text(os.path.join(common.path("output_latest"), "threeview.md"),
                      threeview_mod.render_md(spec, res["canon"], None, checklist))
    common.write_json(os.path.join(common.path("workspace_character"),
                                   "threeview_spec.json"),
                      {"spec": spec,
                       "prompt_en": threeview_mod.render_prompt(spec, res["canon"], "en"),
                       "prompt_zh": threeview_mod.render_prompt(spec, res["canon"], "zh"),
                       "negative": threeview_mod.render_negative(spec),
                       "checklist": checklist})
    if args.json:
        common.emit({"canon_path": out, "work_copy": (res["measure"] or {}).get("work_copy"),
                     "missing": canon_mod.missing_fields(res["canon"]),
                     "turnaround": turn}, True)
    else:
        common.echo(u"Canon 骨架 → %s" % out)
        wc = (res["measure"] or {}).get("work_copy")
        if wc:
            common.echo(u"工作副本 → %s" % wc)
            common.echo(u"👉 现在【用视觉能力看这张图】，填满 "
                        u"hair/eyes/face/costume/accessories/silhouette 与 "
                        u"stable_identifiers。")
        common.echo(u"还需填：%s" % u"、".join(canon_mod.missing_fields(res["canon"])))
        common.echo(u"三视图规格与提示词 → output/latest/threeview.md")
    return 0


def step_threeview(args):
    path = os.path.join(common.path("workspace_character"), "character_canon.json")
    canon = common.read_json(path, {}) or {}
    if not canon:
        common.echo(u"还没有 Canon：先跑 scripts/mvstudio.py canon")
        return 3
    spec = threeview_mod.build_spec(canon)
    checklist = threeview_mod.consistency_checklist(canon)
    md = threeview_mod.render_md(spec, canon, None, checklist)
    common.write_text(os.path.join(common.path("output_latest"), "threeview.md"), md)
    if args.json:
        common.emit({"spec": spec,
                     "prompt_en": threeview_mod.render_prompt(spec, canon, "en"),
                     "prompt_zh": threeview_mod.render_prompt(spec, canon, "zh"),
                     "negative": threeview_mod.render_negative(spec),
                     "checklist": checklist,
                     "unusable_fields": threeview_mod.unusable_fields(canon)}, True)
    else:
        common.echo(md)
    return 0


def step_styles(args):
    argv = []
    if args.size:
        argv += ["--size", str(args.size)]
    if getattr(args, "segments", None):
        argv += ["--segments", str(args.segments)]
    if getattr(args, "pick", None):
        argv += ["--pick", args.pick]
    if getattr(args, "plan", None):
        argv += ["--plan", args.plan]
    if getattr(args, "json", False):
        argv.append("--json")
    return styles_mod.main(argv) or 0


def step_segments(args):
    found = materials_mod.discover(args.audio, args.image, args.lyrics)
    audio = (found.get("audio") or {}).get("path")
    if not audio:
        common.echo(u"没有音频：把音乐放进 input/music/")
        return 3
    gate = materials_mod.duration_gate(audio)
    if gate.get("blocked"):
        common.echo(gate.get("message"))
        return 3
    duration = gate["duration"]
    analysis = _load_analysis()
    if not analysis:
        import music as music_mod  # noqa: E402
        analysis = music_mod.analyze(audio)
        common.write_json(os.path.join(common.path("workspace_analysis"), "music.json"),
                          analysis)
    grid = None
    if analysis.get("bpm"):
        grid = beats_mod.beat_grid(analysis["bpm"], duration,
                                   phase=float(analysis.get("phase") or 0.0))
    target, _cap = beats_mod.defaults()
    segs = beats_mod.segment_14_5(duration, grid=grid, target=target,
                                  tolerance_beats=float(common.config()["segment"]
                                                        .get("snap_tolerance_beats", 1.5)))
    # 真的切音频
    seg_dir = common.path("workspace_segments")
    slice_res = slicer_mod.slice_audio(audio, segs, seg_dir, prefix="C")
    common.write_text(os.path.join(common.path("workspace_analysis"), "cut_sheet.md"),
                      "".join([u"# 切分表\n\n", beats_mod.describe(segs, grid), u"\n"]))
    if slice_res.get("manifest"):
        slicer_mod.write_cut_sheet(slice_res["manifest"],
                                   os.path.join(common.path("output_latest"),
                                                "cut_sheet.md"))

    # 歌词
    lyr = _load_lyrics()
    if not lyr:
        step_lyrics(argparse.Namespace(**vars(args)))
        lyr = _load_lyrics()
    lyric_lines = lyr.get("lines") or []

    # Canon
    canon = common.read_json(os.path.join(common.path("workspace_character"),
                                          "character_canon.json"), {}) or {}
    if not canon:
        canon = canon_mod.skeleton()

    # 画风路线
    plan_path = os.path.join(common.path("workspace_analysis"), "director_plan.json")
    old = common.read_json(plan_path, {}) or {}
    picked = args.route_id or (old.get("art_direction") or {}).get("route_id")
    routes = styles_mod.build_routes(lyric_lines, analysis,
                                     size=int(common.config()["style"]
                                              .get("route_menu_size", 4)),
                                     segments=len(segs))
    chosen = None
    if picked:
        for r in routes:
            if r["id"] == picked:
                chosen = r
                break
    if chosen is None:
        chosen = routes[0]
    if chosen and not old.get("art_direction", {}).get("route_id"):
        common.echo(u"未选画风路线 → 先用第 1 条（%s）。"
                    u"**请让用户在下面 4 条里挑一条**，然后跑 "
                    u"`mvstudio.py styles --pick <id>` 再重跑本步。" % chosen["name"])

    plan = director_mod.build_draft(
        duration, analysis, lyric_lines, canon, segs, routes,
        image=found.get("image"), turnaround=found.get("turnaround"),
        audio={"path": audio},
        meta_extra={"audio_cutter": slice_res.get("tool"),
                    "audio_sliced": bool(slice_res.get("ok"))})
    styles_mod.apply_route(plan, chosen)
    # 保留用户已经填过的创意字段（幂等，可反复跑）
    if old and old.get("segments") and not args.reset:
        plan = _merge_filled(plan, old)
    _save_plan(plan)
    common.write_text(os.path.join(common.path("workspace_analysis"),
                                   "director_worksheet.md"),
                      director_mod.render_worksheet(plan))
    common.write_text(os.path.join(common.path("output_latest"), "style_routes.md"),
                      styles_mod.render_md(routes, chosen["id"] if chosen else None))
    common.write_text(os.path.join(common.path("output_latest"), "storyboard.md"),
                      h3render.render_storyboard(plan))

    if args.json:
        common.emit({"segments": len(segs), "slice_ok": slice_res.get("ok"),
                     "slice_tool": slice_res.get("tool"),
                     "plan": plan_path, "audio_dir": seg_dir,
                     "style_route": chosen["id"] if chosen else None,
                     "must_fill": director_mod.fill_check(plan)}, True)
    else:
        common.echo(u"切分：%d 段（目标 %.1fs）" % (len(segs), target))
        for s in segs:
            common.echo(u"  %s  %7.3f–%7.3f  音乐 %.3fs → H3 duration %ss"
                        u"（实出 %.3fs）吸附=%s"
                        % (s["label"], s["start"], s["end"], s["audio_seconds"],
                           s["request_seconds"], s["delivered_seconds"],
                           s["snapped_to"]))
        if slice_res.get("ok"):
            common.echo(u"音频已切 → %s（工具 %s，未加淡入淡出）"
                        % (seg_dir, slice_res.get("tool")))
        else:
            common.echo(u"⚠️ 音频未切：%s" % slice_res.get("error"))
            common.echo(u"   已产出切分清单，请自行按表切。")
        common.echo(u"画风路线：%s → %s" % (chosen["name"],
                                          " → ".join(chosen["movement_per_segment"])))
        common.echo(u"草稿导演稿 → %s" % plan_path)
        common.echo(u"导演工作表 → workspace/analysis/director_worksheet.md")
        miss = director_mod.fill_check(plan)
        common.echo(u"还需人填 %d 项（前 8 项：%s）"
                    % (len(miss), u"、".join(miss[:8])))
    return 0


def _merge_filled(new_plan, old):
    """重复运行时保留人已经填好的创意字段（草稿标记除外）。"""
    old_segs = {s.get("id"): s for s in (old.get("segments") or [])}
    for key in ("mv_concept", "logline", "visual_arc", "motif_dictionary",
                "lyric_semantic_map", "quality_gates"):
        if old.get(key):
            new_plan[key] = old[key]
    for seg in new_plan.get("segments") or []:
        prev = old_segs.get(seg.get("id"))
        if not prev:
            continue
        for k, v in prev.items():
            if k in ("id", "label", "time_start", "time_end", "art_movement",
                     "shots", "lyrics", "lyric_lines"):
                continue
            if isinstance(v, str) and director_mod.DRAFT_MARK in v:
                continue
            if v in (None, "", [], {}):
                continue
            seg[k] = v
        # 镜头动作：只保留人改过的
        if prev.get("shots") and len(prev["shots"]) == len(seg.get("shots") or []):
            for a, b in zip(prev["shots"], seg["shots"]):
                if director_mod.DRAFT_MARK not in str(a.get("action") or ""):
                    b["action"] = a["action"]
                if a.get("lyric"):
                    b["lyric"] = a["lyric"]
                for k in ("shot_size", "camera_target"):
                    if a.get(k):
                        b[k] = a[k]
    if not old.get("art_direction", {}).get("route_id"):
        pass
    return new_plan


def _confirmation_gate(plan, args, for_pack=False):
    """用户要求：每一个步骤都要让用户确认一下。未确认就拦住。"""
    if getattr(args, "unattended", False):
        return None
    led = confirm_mod.Ledger(common.PROJECT_ROOT)
    pending = (led.pending_for_pack(plan) if for_pack
               else led.pending_for_render(plan))
    if not pending:
        return None
    common.echo(u"⚠️ 有 %d 个步骤还没让用户确认 —— 按约定不能继续：" % len(pending))
    for st in pending[:14]:
        title, what = confirm_mod.label_for(st)
        common.echo(u"  ⬜ %s（%s）：%s" % (st, title, what))
    if len(pending) > 14:
        common.echo(u"  … 还有 %d 个" % (len(pending) - 14))
    common.echo(u"")
    common.echo(u"  逐个确认：python3 scripts/mvstudio.py confirm --step <步骤>")
    common.echo(u"  一次确认：python3 scripts/mvstudio.py confirm --all")
    common.echo(u"  查看台账：python3 scripts/mvstudio.py confirm --status")
    common.echo(u"  （确实无人值守时加 --unattended 跳过）")
    return 5


def step_lastframe(args):
    """取某段视频的尾帧，挂到下一段的首帧上。"""
    if getattr(args, "report", False):
        rep = frames_mod.extractor_report()
        if args.json:
            common.emit(rep, True)
        else:
            common.echo(u"最好用的取帧工具：%s" % rep["best"])
            common.echo(u"  ffmpeg       %s" % (u"有" if rep["ffmpeg"] else u"没有"))
            common.echo(u"  AVFoundation %s" % (u"有" if rep["avfoundation"] else u"没有"))
            common.echo(u"  平台导出      总是可用（小云雀 / MiniMax Design 时间轴）")
        return 0

    if getattr(args, "scan", None):
        found = []
        for name in sorted(os.listdir(args.scan)):
            if not name.lower().endswith((".mp4", ".mov", ".m4v", ".webm")):
                continue
            label = os.path.splitext(name)[0].upper()
            res = frames_mod.capture_for_segment(os.path.join(args.scan, name),
                                                 label, at=args.at)
            found.append({"video": name, "label": label, "ok": res.get("ok"),
                          "path": res.get("path"), "error": res.get("error")})
        if args.json:
            common.emit({"scan": args.scan, "results": found}, True)
        else:
            for f in found:
                common.echo(u"  %s %s → %s" % (u"✓" if f["ok"] else u"✗",
                                               f["video"], f.get("path") or f.get("error")))
        return 0 if any(f["ok"] for f in found) else 1

    if not args.video:
        common.echo(u"要么给 --video，要么给 --scan <目录>")
        return 2
    seg = args.segment or "frame"
    res = frames_mod.capture_for_segment(args.video, seg, at=args.at)
    if res.get("ok") and args.segment:
        plan = _load_plan()
        if plan.get("segments"):
            ch = chain_mod.attach_frame(
                plan, args.segment, res["path"],
                describe=args.describe, declared=True)
            if ch:
                _save_plan(plan)
                nxt = {"C1": "C2", "C2": "C3", "C3": "C4"}.get(args.segment, u"下一段")
                common.echo(u"已把 %s 的尾帧挂到 %s 的首帧上（%s）"
                            % (args.segment, nxt, ch.get("label")))
    if args.json:
        common.emit(res, True)
    else:
        if res.get("ok"):
            common.echo(u"✓ %s帧 → %s（%s×%s，工具 %s，位于 %.3fs）"
                        % (u"尾" if args.at == "last" else u"首", res["path"],
                           res.get("width"), res.get("height"), res.get("tool"),
                           res.get("at_seconds") or 0))
            if not res.get("exact", True):
                common.echo(u"  ⚠️ 没取到严格意义的最后一帧，请人工核一眼")
            try:
                idx = int("".join(ch for ch in (args.segment or "") if ch.isdigit()))
            except ValueError:
                idx = 0
            common.echo(u"  然后让用户确认这一段的输出与尾帧："
                        u"python3 scripts/mvstudio.py confirm --step chain-%02d" % idx)
        else:
            common.echo(u"✗ %s" % res.get("error"))
            if res.get("how"):
                common.echo(res["how"])
    return 0 if res.get("ok") else 1


def step_chain(args):
    return chain_mod.main(_passthrough(args, ["--plan", "--md"]) +
                          (["--off"] if getattr(args, "off", False) else [])) or 0


def step_confirm(args):
    argv = _passthrough(args, ["--step", "--note", "--revoke", "--plan"])
    if getattr(args, "all_steps", False):
        argv.append("--all")
    if getattr(args, "status", False):
        argv.append("--status")
    return confirm_mod.main(argv) or 0


def step_camera(args):
    argv = _passthrough(args, ["--map"])
    return camera_mod.main(argv) or 0


def step_endings(args):
    argv = _passthrough(args, ["--pick", "--plan"])
    if getattr(args, "list_only", False):
        argv.append("--list")
    return endings_mod.main(argv) or 0


def step_platform(args):
    return platforms_mod.main(_passthrough(args, ["--platform"])) or 0


def _passthrough(args, keys):
    """把 argparse 命名空间里指定的键还原成命令行参数。"""
    argv = []
    for k in keys:
        v = getattr(args, k.replace("--", "").replace("-", "_"), None)
        if v in (None, False, ""):
            continue
        if v is True:
            argv.append(k)
        else:
            argv += [k, str(v)]
    if getattr(args, "json", False):
        argv.append("--json")
    if getattr(args, "project", None):
        argv += ["--project", args.project]
    return argv


def step_render(args):
    plan = _load_plan()
    if not plan:
        common.echo(u"没有导演稿：先跑 scripts/mvstudio.py segments")
        return 3
    # 顺序很重要：稿子还没填完时，「先填稿」比「先确认」更根本
    problems = h3render.check_ready(plan)
    if problems:
        common.echo(u"拒绝渲染（缺 %d 项）：" % len(problems))
        for p in problems[:30]:
            common.echo(u"  - %s" % p)
        if len(problems) > 30:
            common.echo(u"  … 还有 %d 项" % (len(problems) - 30))
        return 2
    gate = _confirmation_gate(plan, args)
    if gate is not None:
        return gate
    plan.setdefault("meta", {})["lang"] = args.lang
    plan["meta"]["h3_route"] = args.route
    _save_plan(plan)
    text = h3render.render_package(plan, route=args.route, lang=args.lang)
    out = os.path.join(common.path("output_latest"), "minimax_h3_prompts.md")
    common.write_text(out, text)
    common.write_text(os.path.join(common.path("output_latest"), "storyboard.md"),
                      h3render.render_storyboard(plan))
    if args.json:
        common.emit({"prompts": out, "segments": len(plan.get("segments") or []),
                     "chars": len(text), "route": args.route, "lang": args.lang}, True)
    else:
        common.echo(u"已渲染 %d 条 → %s（%s 路线 / %s，共 %d 字符）"
                    % (len(plan.get("segments") or []), out, args.route, args.lang,
                       len(text)))
    return 0


def step_validate(args):
    plan = _load_plan()
    prompts_path = os.path.join(common.path("output_latest"), "minimax_h3_prompts.md")
    text = common.read_text(prompts_path) if os.path.isfile(prompts_path) else ""
    res = gates_mod.validate(plan, text)
    common.write_text(os.path.join(common.path("output_latest"), "validation.md"),
                      gates_mod.render_md(res))
    if args.json:
        common.emit(res, True)
    else:
        common.echo(gates_mod.render_md(res))
    return 0 if res["passed"] else 1


def step_pack(args):
    plan = _load_plan()
    if not plan:
        common.echo(u"没有导演稿：先跑 scripts/mvstudio.py segments")
        return 3
    gate = _confirmation_gate(plan, args, for_pack=True)
    if gate is not None:
        return gate
    prompts_path = os.path.join(common.path("output_latest"), "minimax_h3_prompts.md")
    text = common.read_text(prompts_path) if os.path.isfile(prompts_path) else ""
    res = pack_mod.pack(plan, route=args.route, lang=args.lang,
                        platform=getattr(args, "platform", None) or
                        platforms_mod.default_platform(),
                        prompts_text=text)
    if args.json:
        common.emit(res, True)
    else:
        common.echo(u"交付包 → %s" % res["dir"])
        for f in res["files"]:
            common.echo(u"  %s" % f)
        common.echo(u"  音频段 %d 个 ｜ 提示词 %d 条"
                    % (len(res["segments"]), res["prompts"]))
    return 0


def step_all(args):
    """一次跑完所有**确定性**步骤。创意仍然必须由导演填。"""
    if not args.no_archive:
        dest = _archive_latest()
        if dest:
            common.echo(u"上一轮结果已归档 → %s" % dest)
    found = materials_mod.discover(args.audio, args.image, args.lyrics)
    if not found.get("audio"):
        common.echo(u"✖ 没有音频：把音乐放进 input/music/")
        return 3
    gate = materials_mod.duration_gate(found["audio"]["path"])
    common.echo(u"【时长闸门】%s" % gate.get("message"))
    if gate.get("blocked"):
        return 3
    if not found.get("image"):
        common.echo(u"✖ 没有人物参考图：把图放进 input/character/")
        return 3

    common.echo("")
    common.echo(u"① 音乐实测")
    rc = step_analyze(argparse.Namespace(**vars(args)))
    if rc:
        return rc
    common.echo(u"② 歌词时间轴")
    step_lyrics(argparse.Namespace(**vars(args)))
    common.echo(u"③ 人物 Canon 骨架 + 三视图规格")
    rc = step_canon(argparse.Namespace(**vars(args)))
    if rc:
        return rc
    common.echo(u"④ 14.5 秒切分 + 切音频 + 草稿导演稿")
    rc = step_segments(argparse.Namespace(**vars(args)))
    if rc:
        return rc

    # 尾帧续接链
    if not getattr(args, "no_chain", False):
        plan = _load_plan()
        if plan.get("segments"):
            chain_mod.build_chain(plan)
            _save_plan(plan)
            common.write_text(os.path.join(common.path("output_latest"), "chain.md"),
                              chain_mod.render_md(plan))
            common.echo("")
            common.echo(u"⑤ 尾帧续接链（上一段尾帧 → 下一段首帧）")
            for seg in plan["segments"]:
                ch = seg.get("chain")
                if ch:
                    common.echo(u"  %s 接 %s 的尾帧：%s"
                                % (seg.get("label"), ch["from_segment"],
                                   os.path.basename(ch.get("frame") or "")))

    common.echo("")
    common.echo(u"══ 确定性步骤完成。接下来是**创作**，机器不能替你做 ══")
    common.echo(u"  1. 用视觉能力看 workspace/character/canon_reference.*，填 "
                u"workspace/character/character_canon.json")
    common.echo(u"  2. 按 output/latest/threeview.md 出三视图，存进 "
                u"input/character/threeview.png")
    common.echo(u"  3. **让用户在 output/latest/style_routes.md 的 4 条路线里挑一条**，"
                u"然后跑 `python3 scripts/mvstudio.py styles --pick <id>`")
    common.echo(u"  4. 填 workspace/analysis/director_plan.json"
                u"（工作表：workspace/analysis/director_worksheet.md）")
    common.echo(u"  5. python3 scripts/mvstudio.py render && python3 scripts/mvstudio.py validate")
    common.echo(u"  6. python3 scripts/mvstudio.py pack")
    common.echo("")
    common.echo(u"══ 每一个步骤都要让用户确认一次 ══")
    plan = _load_plan()
    led = confirm_mod.Ledger(common.PROJECT_ROOT)
    pending = led.pending_for_render(plan)
    for st in pending:
        title, what = confirm_mod.label_for(st)
        common.echo(u"  ⬜ %-10s %s —— %s" % (st, title, what))
    if pending:
        common.echo(u"")
        common.echo(u"  确认：python3 scripts/mvstudio.py confirm --step <步骤>"
                    u"　或　--all 一次确认全部")
        common.echo(u"  未确认时 render / pack 会拒绝继续（除非 --unattended）")
    return 0


# ------------------------------------------------------------------ CLI
ROUTES = ["mv", "ref", "i2va", "t2va"]


def build_parser():
    ap = argparse.ArgumentParser(
        prog="mvstudio.py",
        description=u"2d-limited-mv-studio · 多风格融合舞蹈影像导演（MiniMax H3）")
    common.add_common_args(ap)
    sub = ap.add_subparsers(dest="cmd")

    def add(name, fn, help_text):
        p = sub.add_parser(name, help=help_text)
        common.add_common_args(p)
        p.add_argument("--audio")
        p.add_argument("--image")
        p.add_argument("--lyrics")
        p.set_defaults(func=fn)
        return p

    for name, fn, h in (
            ("doctor", step_doctor, u"环境体检"),
            ("gate", step_gate, u"材料闸门 + 时长闸门"),
            ("analyze", step_analyze, u"音乐实测"),
            ("lyrics", step_lyrics, u"歌词时间轴"),
            ("canon", step_canon, u"人物 Canon 骨架"),
            ("threeview", step_threeview, u"三视图规格与提示词"),
            ("segments", step_segments, u"14.5 秒切分 + 切音频"),
            ("all", step_all, u"跑完所有确定性步骤"),
    ):
        p = add(name, fn, h)
        if name == "lyrics":
            p.add_argument("--asr-model", default="small")
        if name == "canon":
            p.add_argument("--name", default="@character")
        if name == "segments":
            p.add_argument("--route-id", default=None)
            p.add_argument("--reset", action="store_true")
        if name == "all":
            p.add_argument("--no-archive", action="store_true")
            p.add_argument("--route-id", default=None)
            p.add_argument("--reset", action="store_true")
            p.add_argument("--asr-model", default="small")
            p.add_argument("--name", default="@character")
            p.add_argument("--platform", choices=platforms_mod.known(), default=None)
            p.add_argument("--unattended", action="store_true")
            p.add_argument("--no-chain", action="store_true",
                           help=u"不做尾帧续接")

    p = sub.add_parser("styles", help=u"画风融合路线菜单")
    common.add_common_args(p)
    p.add_argument("--size", type=int, default=None)
    p.add_argument("--segments", type=int, default=None)
    p.add_argument("--pick", default=None)
    p.add_argument("--plan", default=None)
    p.add_argument("--md", action="store_true")
    p.set_defaults(func=step_styles)

    for name, fn, h in (("validate", step_validate, u"交付校验"),
                        ("pack", step_pack, u"打上传交付包")):
        p = sub.add_parser(name, help=h)
        common.add_common_args(p)
        p.add_argument("--plan", default=None)
        p.add_argument("--route", choices=ROUTES, default="mv")
        p.add_argument("--lang", choices=["en", "zh"], default="zh")
        p.add_argument("--out", default=None)
        p.add_argument("--platform", choices=platforms_mod.known(), default=None,
                       help=u"小云雀 / MiniMax Design / 通用")
        p.add_argument("--unattended", action="store_true",
                       help=u"跳过逐步骤确认（明确表示已全部确认）")
        p.set_defaults(func=fn)

    p = sub.add_parser("render", help=u"渲染 MiniMax H3 原生提示词")
    common.add_common_args(p)
    p.add_argument("--plan", default=None)
    p.add_argument("--route", choices=ROUTES, default="mv")
    p.add_argument("--lang", choices=["en", "zh"], default="zh")
    p.add_argument("--check", action="store_true")
    p.add_argument("--unattended", action="store_true")
    p.set_defaults(func=step_render)

    p = sub.add_parser("lastframe", help=u"取视频尾帧（下一段的首帧）")
    common.add_common_args(p)
    p.add_argument("--video", default=None)
    p.add_argument("--scan", default=None, help=u"扫一个目录里所有视频")
    p.add_argument("--segment", default=None, help=u"段名，如 C1")
    p.add_argument("--at", choices=["last", "first"], default="last")
    p.add_argument("--describe", default=None, help=u"这一帧里看到了什么")
    p.add_argument("--report", action="store_true", help=u"只看有哪些取帧工具")
    p.set_defaults(func=step_lastframe)

    p = sub.add_parser("chain", help=u"构建/查看尾帧续接链")
    common.add_common_args(p)
    p.add_argument("--plan", default=None)
    p.add_argument("--md", action="store_true")
    p.add_argument("--off", action="store_true", help=u"关闭尾帧续接")
    p.set_defaults(func=step_chain)

    p = sub.add_parser("confirm", help=u"逐步骤确认台账")
    common.add_common_args(p)
    p.add_argument("--step", default=None)
    p.add_argument("--note", default=None)
    p.add_argument("--all", dest="all_steps", action="store_true")
    p.add_argument("--status", action="store_true")
    p.add_argument("--revoke", default=None)
    p.add_argument("--plan", default=None)
    p.set_defaults(func=step_confirm)

    p = sub.add_parser("camera", help=u"运镜分层库（景别/角度/构图/焦/2D 招）")
    common.add_common_args(p)
    p.add_argument("--map", default=None, help=u"查一个实拍术语的官方映射")
    p.set_defaults(func=step_camera)

    p = sub.add_parser("endings", help=u"收尾效果菜单（不一定要站定）")
    common.add_common_args(p)
    p.add_argument("--pick", default=None)
    p.add_argument("--list", dest="list_only", action="store_true")
    p.add_argument("--plan", default=None)
    p.set_defaults(func=step_endings)

    p = sub.add_parser("platform", help=u"平台适配信息（切割功能 / 首尾帧）")
    common.add_common_args(p)
    p.add_argument("--platform", choices=platforms_mod.known(), default=None)
    p.set_defaults(func=step_platform)
    return ap


def _prescan_common(argv):
    """在子解析器**覆盖之前**先抓到 --project / --json。

    argparse 的子解析器默认值会盖掉父解析器已经解析到的值，所以
    `mvstudio.py --project X all` 里的 --project 会被静默丢掉，
    产物落到 skill 安装目录里。这里先扫一遍原始 argv 兜住。
    """
    argv = list(sys.argv[1:] if argv is None else argv)
    pre = argparse.ArgumentParser(add_help=False)
    pre.add_argument("--project", default=None)
    pre.add_argument("--json", action="store_true", default=False)
    known, _rest = pre.parse_known_args(argv)
    return known


def _autodetect_project(args, prescanned=None):
    """在项目目录里直接跑 `python3 <skill>/scripts/mvstudio.py all` 时用当前目录。

    判据是存在 input/ workspace/ output/ config/ 之一——不看的话，用户在
    自己项目里跑，产物会全部落到 skill 安装目录里。
    """
    if prescanned is not None and prescanned.project:
        args.project = prescanned.project
    elif not getattr(args, "project", None):
        cwd = os.path.abspath(os.getcwd())
        if cwd != os.path.abspath(common.INSTALL_ROOT):
            for marker in ("input", "workspace", "output", "config"):
                if os.path.isdir(os.path.join(cwd, marker)):
                    args.project = cwd
                    break
    if prescanned is not None and prescanned.json:
        args.json = True
    return args


def main(argv=None):
    ap = build_parser()
    pre = _prescan_common(argv)
    args = ap.parse_args(argv)
    if not getattr(args, "cmd", None):
        ap.print_help()
        return 0
    _autodetect_project(args, pre)
    try:
        common.apply_common_args(args)
    except (PermissionError, OSError) as exc:
        common.echo(u"无法在项目目录里建运行时目录：%s" % exc)
        common.echo(u"项目根：%s" % common.PROJECT_ROOT)
        # 建议一个**当前环境里确实可写**的目录，不要写死 home 路径
        # （在受限沙箱里 home 同样不可写，那样的建议等于没建议）
        cwd = os.path.abspath(os.getcwd())
        suggestion = None
        if os.access(cwd, os.W_OK):
            suggestion = os.path.join(cwd, "mv-run")
        else:
            for cand in (os.path.expanduser("~"), "/tmp"):
                if os.path.isdir(cand) and os.access(cand, os.W_OK):
                    suggestion = os.path.join(cand, "mv-run")
                    break
        common.echo(u"换一个**当前可写**的目录再跑：")
        if suggestion:
            common.echo(u'  python3 "%s" --project "%s" all'
                        % (os.path.join(HERE, "mvstudio.py"), suggestion))
        else:
            common.echo(u'  python3 "%s" --project <可写目录> all'
                        % os.path.join(HERE, "mvstudio.py"))
        common.echo(u"（--project 放在子命令前后都一样；该目录下会自动建 "
                    u"input/ workspace/ output/）")
        return 4
    try:
        return args.func(args) or 0
    except KeyboardInterrupt:
        common.echo(u"已中断")
        return 130
    except Exception as exc:
        common.echo(u"失败：%s: %s" % (type(exc).__name__, exc))
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
