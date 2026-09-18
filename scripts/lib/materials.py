#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""materials —— 材料闸门、环境体检、输入发现。

这是**第 0 步**：用户说「帮我做条 MV」时，第一件事不是开工，而是回答
「缺什么、会卡住哪一步」。缺必需材料就停下来要材料，不要硬产出一份不能用的东西。

两条硬闸门：
  * 时长 > 180s  → **失败**并说明，要求用户先切歌。**绝不自动截断用户的音乐。**
  * 缺音乐 / 缺人物图 → 停下来说清楚，不要猜。
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common  # noqa: E402
import audioprobe  # noqa: E402
import imgprobe  # noqa: E402


# ------------------------------------------------------------------ 发现输入
def _scan(dirs, exts, include_root=True):
    out = []
    seen = set()
    keys = list(dirs) + (["__input_root__"] if include_root else [])
    for key in keys:
        if key == "__input_root__":
            base = common.path("input_music")
            d = os.path.dirname(os.path.abspath(base))
        else:
            d = common.path(key)
        if not os.path.isdir(d):
            continue
        for name in sorted(os.listdir(d)):
            if name.startswith(".") or name.startswith("_"):
                continue
            p = os.path.join(d, name)
            if not os.path.isfile(p):
                continue
            if os.path.splitext(name)[1].lower() not in exts:
                continue
            if p in seen:
                continue
            seen.add(p)
            out.append({"path": p, "name": name, "mtime": os.path.getmtime(p),
                        "bytes": os.path.getsize(p)})
    return out


def discover(audio=None, image=None, lyrics=None):
    """找出本次要用的「一首歌 + 一张人物图（+ 可选歌词）」。永不抛异常。"""
    cfg = common.config()
    audio_ext = [e.lower() for e in cfg["audio"]["extensions"]]
    image_ext = [e.lower() for e in cfg["image"]["extensions"]]
    hints = [h.lower() for h in cfg["image"].get("character_hints", [])]

    res = {"audio": None, "image": None, "lyrics": None,
           "candidates": {"audio": [], "image": []}, "blockers": [], "notes": []}

    # 音频
    if audio:
        p = common.abspath(audio)
        if os.path.isfile(p):
            res["audio"] = {"path": p, "source": "explicit"}
        else:
            res["blockers"].append(u"命令行指定的音频不存在：%s" % audio)
    else:
        cands = _scan(["input_music"], audio_ext)
        cands.sort(key=lambda c: -c["mtime"])
        res["candidates"]["audio"] = [c["path"] for c in cands]
        if cands:
            res["audio"] = {"path": cands[0]["path"], "source": "input/music（最近修改）"}
        else:
            res["blockers"].append(u"没有音频：把音乐放进 input/music/ "
                                   u"（支持 %s）" % " ".join(audio_ext))

    # 人物图
    if image:
        p = common.abspath(image)
        if os.path.isfile(p):
            res["image"] = {"path": p, "source": "explicit"}
        else:
            res["blockers"].append(u"命令行指定的图片不存在：%s" % image)
    else:
        cands = _scan(["input_character"], image_ext)
        named = [c for c in cands
                 if any(h in c["name"].lower() for h in hints)]
        pool = named or cands
        # 三视图单独识别：它是附加参考，不当主参考图
        turned = [c for c in pool
                  if any(k in c["name"].lower()
                         for k in ("threeview", "turnaround", "三视图", "setting"))]
        main = [c for c in pool if c not in turned] or pool
        main.sort(key=lambda c: -c["mtime"])
        res["candidates"]["image"] = [c["path"] for c in cands]
        if main:
            res["image"] = {"path": main[0]["path"],
                            "source": "文件名命中" if named else "input/character（最近修改）"}
        else:
            res["blockers"].append(u"没有人物参考图：把图放进 input/character/ "
                                   u"（支持 %s）" % " ".join(image_ext))
        if turned:
            turned.sort(key=lambda c: -c["mtime"])
            res["turnaround"] = {"path": turned[0]["path"], "source": "已识别的三视图"}

    # 歌词
    try:
        import lyricsrc  # noqa: E402
        if lyrics:
            p = common.abspath(lyrics)
            res["lyrics"] = {"path": p} if os.path.isfile(p) else None
            if not res["lyrics"]:
                res["blockers"].append(u"命令行指定的歌词文件不存在：%s" % lyrics)
        elif res["audio"]:
            side = lyricsrc.find_sidecar_lyrics(res["audio"]["path"])
            if side:
                # find_sidecar_lyrics 返回 dict（含 kind/path/how）
                res["lyrics"] = {"path": side.get("path") if isinstance(side, dict) else side,
                                 "kind": side.get("kind") if isinstance(side, dict) else None,
                                 "source": "同目录 sidecar"}
        if not res["lyrics"]:
            lyr_dir = common.path("input_lyrics")
            if os.path.isdir(lyr_dir):
                for name in sorted(os.listdir(lyr_dir)):
                    if name.startswith("."):
                        continue
                    if os.path.splitext(name)[1].lower() in (".lrc", ".srt", ".vtt", ".txt"):
                        res["lyrics"] = {"path": os.path.join(lyr_dir, name),
                                         "source": "input/lyrics"}
                        break
    except Exception as exc:
        res["notes"].append(u"歌词发现失败：%s" % exc)

    if not res["lyrics"]:
        res["notes"].append(
            u"没有歌词时间轴。这不是阻断项，但会降级：画面与歌词的呼应只能按"
            u"能量曲线指派。**不要用 ASR 自动转写当定稿**——实测把「王子」转成过"
            u"「滑走」。把人工核对过的 .lrc/.srt/.vtt/.txt 放进 input/lyrics/ 即可。")
    return res


# ------------------------------------------------------------------ 时长闸门
def duration_gate(audio_path):
    """真的去读音频时长，然后判定。**禁止根据文件名猜。**"""
    cfg = common.config()
    max_sec = float(cfg["audio"]["max_duration_sec"])
    min_sec = float(cfg["audio"].get("min_duration_sec", 0) or 0)
    if not audio_path or not os.path.isfile(audio_path):
        return {"ok": False, "readable": False, "blocked": True,
                "message": u"读不到音频文件：%s" % audio_path}
    info = audioprobe.probe(audio_path)
    dur = info.get("duration")
    gate = {
        "path": audio_path,
        "readable": dur is not None,
        "duration": dur,
        "max_duration_sec": max_sec,
        "min_duration_sec": min_sec,
        "blocked": False,
        "probe_source": info.get("probe_source"),
        "format": info.get("format"),
        "sample_rate": info.get("sample_rate"),
        "channels": info.get("channels"),
        "message": "",
    }
    if dur is None:
        gate["blocked"] = True
        gate["message"] = (u"无法解析该音频的时长（%s）。请换一个文件，或安装 ffmpeg 后重试。"
                           % (info.get("error") or "未知原因"))
        return gate
    if dur > max_sec:
        gate["blocked"] = True
        gate["message"] = (
            u"**失败**：本技能默认支持不超过 3 分钟（180 秒）的歌曲，"
            u"该歌曲长度为 %s（%.2f 秒）。\n"
            u"请先把音乐切到 3 分钟以内（建议切在**小节线**上），再重新提交。\n"
            u"**我没有自动截断你的音乐**——截断会毁掉你的编曲结构。"
            % (common.mmss(dur), dur))
        gate["suggestion"] = {
            "target_seconds": 180,
            "how": u"用 Audacity / Logic 在两处之间切；"
                   u"或者把整首歌拆成两首后分别做两条 MV",
        }
        return gate
    if dur < min_sec:
        gate["blocked"] = True
        gate["message"] = u"音频只有 %.2f 秒，短于下限 %.0f 秒，不足以生成 MV。" % (dur, min_sec)
        return gate
    import beats  # noqa: E402
    target, _cap = beats.defaults()
    n = beats.segments_for_duration(dur, target)
    gate["message"] = (u"通过：%.2f 秒 ≤ 180 秒。按 %.1f 秒切分为 %d 段"
                       u"（每段提交给 MiniMax H3 的 duration 见分段表）。"
                       % (dur, target, n))
    gate["segments"] = n
    return gate


# ------------------------------------------------------------------ 环境体检
def doctor():
    cfg = common.config()
    target, cap = (cfg["segment"].get("target_seconds"),
                   cfg["segment"].get("hard_max_seconds"))
    tools = {}
    for t in ("ffmpeg", "ffprobe", "afinfo", "afconvert"):
        tools[t] = common.which(t) or None
    modules = {}
    for m in ("numpy", "librosa", "soundfile", "scipy", "PIL"):
        modules[m] = common.have_python_module(m)
    cutter = None
    try:
        import slicer  # noqa: E402
        cutter = slicer.available_cutter()
    except Exception:
        pass
    vault = None
    try:
        import artbridge  # noqa: E402
        vault = {"available": artbridge.available(), "repo": artbridge.repo_dir()}
    except Exception as exc:
        vault = {"available": False, "error": str(exc)}

    warnings = []
    if not tools["ffmpeg"] and not tools["afconvert"]:
        warnings.append(u"既没有 ffmpeg 也没有 afconvert：非 WAV 音频无法被自动切分，"
                        u"只能产出切分清单让你自己在 DAW 里切。")
    if not modules["numpy"]:
        warnings.append(u"没有 numpy/librosa：音乐分析走标准库路线"
                        u"（BPM 为自相关估计，可能差一个倍频，建议用耳朵复核）。")
    if not vault.get("available"):
        warnings.append(u"art-aesthetic-vault 不可用：画风降级到内置媒介池，"
                        u"流派术语不如库中精确。")

    # 配置完整性：被静默截断的配置比缺配置更危险
    missing_sections = [k for k in ("project", "audio", "image", "lyrics", "segment",
                                    "style", "paths", "output", "external", "fallbacks")
                        if k not in cfg]
    if missing_sections:
        warnings.append(u"config/defaults.yaml 被截断，丢了：%s" % missing_sections)

    return {
        "python": sys.version.split()[0],
        "python_ok": sys.version_info >= (3, 7),
        "tools": tools,
        "modules": modules,
        "audio_cutter": cutter,
        "artvault": vault,
        "config": {"sections": sorted(cfg.keys()), "missing": missing_sections},
        "segment": {
            "target_seconds": target,
            "hard_max_seconds": cap,
            "max_prompts": cfg["segment"].get("max_prompts"),
            "h3_duration_rule": "MiniMax H3 duration 只接受 4–15 的整数；"
                                "14.5s 的音乐一律请求 15s",
        },
        "warnings": warnings,
        "ready": bool(tools["afinfo"] or tools["ffprobe"] or tools["afconvert"]),
    }


def can_auto_slice(audio_path):
    """能不能自动切这段音频。"""
    try:
        import slicer  # noqa: E402
        if slicer.is_wav(audio_path):
            return True, "wav"
        tool = slicer.available_cutter()
        return tool in ("ffmpeg", "afconvert"), tool
    except Exception:
        return False, "unknown"


def main(argv=None):
    import argparse
    ap = argparse.ArgumentParser(description="材料闸门 / 环境体检")
    common.add_common_args(ap)
    ap.add_argument("--audio")
    ap.add_argument("--image")
    ap.add_argument("--lyrics")
    ap.add_argument("--doctor", action="store_true")
    args = ap.parse_args(argv)
    common.apply_common_args(args)
    if args.doctor:
        d = doctor()
        if args.json:
            common.emit(d, True)
        else:
            common.echo(u"Python %s" % d["python"])
            for k, v in d["tools"].items():
                common.echo(u"  %-10s %s" % (k, v or u"缺失"))
            common.echo(u"  切分能力   %s" % d["audio_cutter"])
            common.echo(u"  风格库     %s" % (u"可用" if d["artvault"].get("available")
                                              else u"不可用（降级）"))
            for w in d["warnings"]:
                common.echo(u"  ⚠️ %s" % w)
        return 0
    found = discover(args.audio, args.image, args.lyrics)
    if found.get("audio"):
        found["duration_gate"] = duration_gate(found["audio"]["path"])
    else:
        found["duration_gate"] = {"blocked": True, "readable": False,
                                  "message": u"没有音频，无法判定时长"}
    code = 0
    if found["blockers"] or found["duration_gate"].get("blocked"):
        code = 3
    if args.json:
        common.emit(found, True)
    else:
        common.echo(u"音频：%s" % (found["audio"] or {}).get("path", u"（缺）"))
        common.echo(u"人物图：%s" % (found["image"] or {}).get("path", u"（缺）"))
        common.echo(u"歌词：%s" % (found["lyrics"] or {}).get("path", u"（缺，降级）"))
        common.echo("")
        common.echo(found["duration_gate"].get("message", ""))
        for b in found["blockers"]:
            common.echo(u"  ✖ %s" % b)
        for n in found["notes"]:
            common.echo(u"  · %s" % n)
    return code


if __name__ == "__main__":
    sys.exit(main())
