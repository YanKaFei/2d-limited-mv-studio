#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""slicer —— 真的把用户的音乐切成 14.5 秒的段（不是只算时间）。

三级降级（缺工具不许让流程死掉）：

  1. 源本身是 WAV           → 标准库 wave 直接切，最准
  2. ffmpeg 可用            → 任意格式 → WAV → 切
  3. afconvert 可用（macOS）→ 任意格式 → WAV → 切
  4. 都没有                 → 只产出**切分清单**（manifest），
                             并明确告诉用户在 DAW / 画布里自己切。
                             **绝不假装切成功。**

两条纪律：
  * 原始音乐永远只读，绝不修改、移动、改名、删除。
  * **不默认加淡入淡出**——这些段要首尾相接拼回去，加淡会让接缝变糊。
"""

import json
import os
import sys
import wave

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common  # noqa: E402

WAV_EXTS = (".wav", ".wave")


def available_cutter():
    """当前机器上能用到的最好的切分能力。"""
    if common.which("ffmpeg"):
        return "ffmpeg"
    if common.which("afconvert"):
        return "afconvert"
    return "wav-only"


def is_wav(path):
    return os.path.splitext(path or "")[1].lower() in WAV_EXTS


def convert_to_wav(src, dst):
    """把任意音频转成 16-bit PCM WAV。返回 (ok, tool, detail)。"""
    common.ensure_parent(dst)
    if is_wav(src):
        return True, "source-wav", "源本身是 WAV，无需转码"
    if common.which("ffmpeg"):
        rc, _out, err = common.run(
            ["ffmpeg", "-y", "-v", "error", "-i", src,
             "-acodec", "pcm_s16le", "-f", "wav", dst], timeout=900)
        if rc == 0 and os.path.isfile(dst):
            return True, "ffmpeg", "ffmpeg → pcm_s16le"
    if common.which("afconvert"):
        rc, _out, err = common.run(
            ["afconvert", "-f", "WAVE", "-d", "LEI16", src, dst], timeout=900)
        if rc == 0 and os.path.isfile(dst):
            return True, "afconvert", "afconvert → LEI16 WAVE"
        return False, "afconvert", "afconvert 失败：%s" % (err or "").strip()[:200]
    return False, "none", "既没有 ffmpeg 也没有 afconvert，无法解码非 WAV 音频"


def _wav_params(path):
    with wave.open(path, "rb") as wf:
        return {"channels": wf.getnchannels(), "width": wf.getsampwidth(),
                "rate": wf.getframerate(), "frames": wf.getnframes()}


def _slice_wav(src, segments, out_dir, prefix, log=None):
    p = _wav_params(src)
    rate = p["rate"]
    total = p["frames"]
    written = []
    with wave.open(src, "rb") as wf:
        for i, seg in enumerate(segments, 1):
            start = max(0.0, float(seg.get("start", 0.0)))
            end = float(seg.get("end", 0.0))
            i0 = max(0, min(total, int(round(start * rate))))
            i1 = max(i0, min(total, int(round(end * rate))))
            if i1 <= i0:
                if log:
                    log.warn("%s 长度为 0，已跳过（start=%.3f end=%.3f）" % (seg, start, end))
                continue
            label = seg.get("label") or ("%s%02d" % (prefix, i))
            name = "%s.wav" % label if not label.lower().endswith(".wav") else label
            dst = os.path.join(out_dir, name)
            wf.setpos(i0)
            data = wf.readframes(i1 - i0)
            common.ensure_parent(dst)
            with wave.open(dst, "wb") as out:
                out.setnchannels(p["channels"])
                out.setsampwidth(p["width"])
                out.setframerate(rate)
                out.writeframes(data)
            written.append({
                "label": os.path.splitext(name)[0],
                "path": dst,
                "start": round(i0 / float(rate), 6),
                "end": round(i1 / float(rate), 6),
                "duration": round((i1 - i0) / float(rate), 6),
            })
    return written


def slice_audio(src, segments, out_dir, prefix="C", log=None):
    """按 segments 的真实时间切音频。返回 dict（永不抛异常）。"""
    log = log or common.Log("slicer")
    src = os.path.abspath(os.path.expanduser(src or ""))
    if not src or not os.path.isfile(src):
        return {"ok": False, "error": "找不到音频文件：%s" % src, "files": []}
    if not segments:
        return {"ok": False, "error": "没有分段可切（segments 为空）", "files": []}

    common.ensure_parent(os.path.join(out_dir, "_"))
    tool = available_cutter()
    work_src = src
    convert_note = "源本身是 WAV"

    if not is_wav(src):
        if tool == "ffmpeg" or tool == "afconvert":
            work_src = os.path.join(common.path("workspace_temp"), "sliced_source.wav")
            ok, used, note = convert_to_wav(src, work_src)
            if not ok:
                return _manifest_only(src, segments, out_dir, prefix,
                                      "解码失败：%s" % note)
            tool = used
            convert_note = note
            log.step("convert", "ok", note, used)
        else:
            return _manifest_only(
                src, segments, out_dir, prefix,
                "本机既没有 ffmpeg 也没有 afconvert，无法解码非 WAV 音频")

    try:
        files = _slice_wav(work_src, segments, out_dir, prefix, log=log)
    except Exception as exc:
        return {"ok": False, "error": "%s: %s" % (type(exc).__name__, exc),
                "files": [], "tool": tool}

    manifest = {
        "source": src,
        "tool": tool,
        "convert": convert_note,
        "output_dir": out_dir,
        "fade": None,
        "note": "段与段首尾相接拼回原曲；未加淡入淡出，接缝不会变糊。",
        "segments": files,
    }
    mpath = os.path.join(out_dir, "manifest.json")
    common.write_json(mpath, manifest)
    return {"ok": True, "tool": tool, "files": files, "manifest": mpath,
            "error": None, "note": manifest["note"]}


def _manifest_only(src, segments, out_dir, prefix, why):
    """切不了也要给出能用的东西：一份精确到毫秒的切分清单。"""
    common.ensure_parent(os.path.join(out_dir, "_"))
    plan = [{
        "label": s.get("label") or ("%s%02d" % (prefix, i)),
        "start": round(float(s.get("start", 0.0)), 3),
        "end": round(float(s.get("end", 0.0)), 3),
        "length": round(float(s.get("end", 0.0)) - float(s.get("start", 0.0)), 3),
    } for i, s in enumerate(segments, 1)]
    mpath = os.path.join(out_dir, "manifest.json")
    common.write_json(mpath, {
        "source": src, "tool": "none", "audio_written": False,
        "reason": why, "segments": plan,
        "how_to_cut": ("请在 DAW / 画布里按下表的 start–end 自己切，"
                       "切好后放进 input/music_segments/ 再重跑。"),
    })
    return {"ok": False, "tool": "none", "files": [], "manifest": mpath,
            "error": why, "fallback": "只产出切分清单（manifest.json）",
            "segments_planned": plan}


def write_cut_sheet(manifest_path, out_md):
    """把 manifest 渲染成一张人读的切分操作单。"""
    data = common.read_json(manifest_path, {}) or {}
    lines = ["# 切分操作单", ""]
    lines.append("- 源文件：`%s`" % data.get("source"))
    lines.append("- 切分工具：`%s`" % data.get("tool"))
    if not data.get("audio_written", True):
        lines.append("- ⚠️ **没有生成音频段**：%s" % data.get("reason"))
        lines.append("- %s" % data.get("how_to_cut", ""))
    lines.append("")
    lines.append("| 段 | 起点 | 终点 | 时长 |")
    lines.append("|----|------|------|------|")
    for s in data.get("segments", []):
        lines.append("| %s | %.3fs | %.3fs | %.3fs |"
                     % (s.get("label"), s.get("start", 0), s.get("end", 0),
                        s.get("length", s.get("duration", 0))))
    lines.append("")
    common.write_text(out_md, "\n".join(lines) + "\n")
    return out_md


def main(argv=None):
    import argparse
    ap = argparse.ArgumentParser(description="按分段切音频")
    common.add_common_args(ap)
    ap.add_argument("--audio", required=True)
    ap.add_argument("--duration", type=float, required=True)
    ap.add_argument("--target", type=float, default=None)
    ap.add_argument("--bpm", type=float, default=None)
    ap.add_argument("--out", default=None)
    args = ap.parse_args(argv)
    common.apply_common_args(args)
    import beats  # noqa: E402
    grid = beats.beat_grid(args.bpm, args.duration) if args.bpm else None
    segs = beats.segment_14_5(args.duration, grid=grid, target=args.target)
    out = args.out or common.path("workspace_segments")
    res = slice_audio(args.audio, segs, out, prefix="C")
    if args.json:
        common.emit(res, True)
    else:
        common.echo("工具=%s 段数=%d" % (res.get("tool"), len(res.get("files") or [])))
        if not res.get("ok"):
            common.echo("未生成音频：%s" % res.get("error"))
    return 0 if res.get("ok") else 1


if __name__ == "__main__":
    sys.exit(main())
