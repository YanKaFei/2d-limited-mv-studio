#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""analyze_music.py —— 音乐结构实测（规则 19-21）。

**音乐分析不是装饰。** 这里产出的数字必须真的影响：动作大小、剪辑速度、
背景密度、抽帧程度、hold frame、图形速度、色彩密度、转场、高潮、收束。

四级降级：
  T1 librosa        —— BPM/拍网格/onset/频谱质心
  T2 numpy          —— RMS包络 + onset + FFT 频谱质心
  T3 纯标准库        —— wave + audioop（RMS/过零率/onset/自相关测速）
  T4 无法解码        —— 只给时长与结构提示，明确标记 degraded

解码：ffmpeg → afconvert（macOS 自带）→ 源为 WAV 直接用。
"""

import argparse
import math
import os
import sys
import wave

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "lib"))
import audioprobe  # noqa: E402
import common  # noqa: E402

HOP_SEC = 0.02


# ------------------------------------------------------------------ 工具
def _pct(values, p):
    if not values:
        return 0.0
    s = sorted(values)
    k = (len(s) - 1) * p
    f = int(math.floor(k))
    c = min(f + 1, len(s) - 1)
    return s[f] + (s[c] - s[f]) * (k - f)


def _mean(values):
    return sum(values) / float(len(values)) if values else 0.0


def _smooth(values, win):
    if win <= 1:
        return list(values)
    out = []
    for i in range(len(values)):
        lo = max(0, i - win // 2)
        hi = min(len(values), i + win // 2 + 1)
        out.append(_mean(values[lo:hi]))
    return out


def _merge_sections(levels, hop, total, labels=("quiet", "low", "mid", "peak")):
    sections = []
    cur = None
    for i, lv in enumerate(levels):
        name = labels[lv]
        if cur and cur["label"] == name:
            cur["end"] = round((i + 1) * hop, 2)
        else:
            if cur:
                sections.append(cur)
            cur = {"start": round(i * hop, 2), "end": round((i + 1) * hop, 2), "label": name}
    if cur:
        sections.append(cur)
    for sec in sections:
        sec["end"] = min(sec["end"], round(total, 2))
        sec["duration"] = round(sec["end"] - sec["start"], 2)
    # 合并极短段落
    merged = []
    for sec in sections:
        if merged and sec["duration"] < hop * 3:
            merged[-1]["end"] = sec["end"]
            merged[-1]["duration"] = round(merged[-1]["end"] - merged[-1]["start"], 2)
        else:
            merged.append(sec)
    return [s for s in merged if s["duration"] >= hop * 2]


def _structure(rms, hop, total):
    """把 RMS 包络变成 quiet/build/peak/breakdown + 收束性格。"""
    if not rms:
        return {}
    smooth = _smooth(rms, int(round(0.5 / hop)) or 1)
    hi = _pct(smooth, 0.95) or (max(smooth) or 1e-6)
    levels = []
    for v in smooth:
        r = v / hi
        levels.append(0 if r < 0.18 else (1 if r < 0.42 else (2 if r < 0.72 else 3)))
    sections = _merge_sections(levels, hop, total)

    peaks = [s for s in sections if s["label"] == "peak"]
    quiet = [s for s in sections if s["label"] == "quiet"]
    builds = []
    for a, b in zip(sections, sections[1:]):
        if labels_rank(b["label"]) - labels_rank(a["label"]) >= 2 and b["duration"] >= 0.6:
            builds.append({"start": a["end"], "end": b["end"],
                           "describe": "%s→%s 的能量攀升" % (a["label"], b["label"])})
    breakdowns = []
    for a, b in zip(sections, sections[1:]):
        if labels_rank(a["label"]) - labels_rank(b["label"]) >= 2 and a["duration"] >= 1.0:
            breakdowns.append({"start": a["start"], "end": a["end"],
                               "describe": "%s→%s 的落差（间奏/断点）" % (a["label"], b["label"])})

    tail_len = min(4.0, total * 0.15)
    tail = [v for i, v in enumerate(smooth) if i * hop > total - tail_len]
    body = _mean(smooth) or 1e-6
    tail_mean = _mean(tail)
    last = smooth[-1] if smooth else 0.0
    if tail_mean < body * 0.35:
        ending = "fade/decay —— 收束为渐弱，最后一段用 hold frame + 视觉衰减补足"
    elif last < tail_mean * 0.4:
        ending = "hard stop —— 突然收住，最后一段用定格抽帧 + 图形断口"
    else:
        ending = "sustained —— 保持在能量上结束，最后一段延续动作到结束帧"

    return {
        "sections": sections,
        "quiet_sections": [[s["start"], s["end"]] for s in quiet],
        "peak_sections": [[s["start"], s["end"]] for s in peaks],
        "build_sections": builds,
        "breakdowns": breakdowns,
        "ending_character": ending,
        "energy_percentiles": {
            "p10": round(_pct(smooth, 0.1), 4),
            "p50": round(_pct(smooth, 0.5), 4),
            "p90": round(_pct(smooth, 0.9), 4),
            "max": round(max(smooth), 4),
        },
    }


def labels_rank(label):
    return {"quiet": 0, "low": 1, "mid": 2, "peak": 3}.get(label, 1)


def _onset_envelope(rms, hop, use_log=True):
    env = []
    for i in range(len(rms)):
        prev = rms[i - 1] if i else rms[0]
        if use_log:
            a = math.log(rms[i] + 1e-6)
            b = math.log(prev + 1e-6)
        else:
            a, b = rms[i], prev
        env.append(max(0.0, a - b))
    return env


def _tempo_from_onset(env, hop):
    if len(env) < 8:
        return None, [], None
    mean = _mean(env)
    centered = [v - mean for v in env]
    lo_lag = max(1, int(round(0.30 / hop)))
    hi_lag = min(len(centered) - 1, int(round(1.20 / hop)))
    if hi_lag <= lo_lag:
        return None, [], None
    best, best_lag = -1e18, lo_lag
    for lag in range(lo_lag, hi_lag + 1):
        acc = 0.0
        for i in range(lag, len(centered)):
            acc += centered[i] * centered[i - lag]
        acc /= float(len(centered) - lag)
        # 偏好 70–170 BPM 的常用区间，抑制倍频
        bpm = 60.0 / (lag * hop)
        if 70 <= bpm <= 170:
            acc *= 1.15
        if acc > best:
            best, best_lag = acc, lag
    period = best_lag * hop
    bpm_raw = 60.0 / period if period else None
    # 倍频校正：自相关常在半速上取到更强的峰（58 其实是 116 的一半）。
    # 折叠到 [70,170) 常用区间，同时保留原始值供人工复核。
    bpm = bpm_raw
    if bpm_raw:
        folded = bpm_raw
        while folded < 70:
            folded *= 2.0
        while folded >= 175:
            folded /= 2.0
        if 70 <= folded < 175:
            bpm = folded
    if bpm and period:
        period = 60.0 / bpm
        best_lag = max(1, int(round(period / hop)))
    # 相位：让网格尽量落在 onset 峰上
    best_phase, best_score = 0.0, -1
    for step in range(best_lag):
        score = sum(centered[i] for i in range(step, len(centered), best_lag))
        if score > best_score:
            best_score, best_phase = score, step * hop
    beats, t = [], best_phase
    while t <= len(env) * hop:
        beats.append(round(t, 3))
        t += period
    return (round(bpm, 1) if bpm else None), beats, (round(bpm_raw, 1) if bpm_raw else None)


def _onsets(env, hop, total):
    if not env:
        return [], 0.0
    thresh = max(_pct(env, 0.85), _mean(env) * 1.6)
    onsets = []
    min_gap = 0.12
    for i in range(1, len(env) - 1):
        if env[i] >= thresh and env[i] >= env[i - 1] and env[i] > env[i + 1]:
            t = i * hop
            if not onsets or t - onsets[-1] >= min_gap:
                onsets.append(round(t, 3))
    density = len(onsets) / total if total else 0.0
    return onsets, round(density, 3)


def _downsample(values, hop, target_hop=0.1):
    step = max(1, int(round(target_hop / hop)))
    out = []
    for i in range(0, len(values), step):
        chunk = values[i:i + step]
        out.append(round(_mean(chunk), 5))
    return out


# ------------------------------------------------------------------ 引擎
def analyze_librosa(path):
    import librosa  # noqa
    y, sr = librosa.load(path, sr=22050, mono=True)
    tempo, beats = librosa.beat.beat_track(y=y, sr=sr, units="time")
    onset_env = librosa.onset.onset_strength(y=y, sr=sr, hop_length=512)
    rms = librosa.feature.rms(y=y, hop_length=512)[0]
    cent = librosa.feature.spectral_centroid(y=y, sr=sr, hop_length=512)[0]
    hop = 512 / float(sr)
    total = len(y) / float(sr)
    rms_list = [float(v) for v in rms]
    env_list = [float(v) / (max(onset_env) or 1.0) for v in onset_env]
    onsets, density = _onsets(_onset_envelope(rms_list, hop), hop, total)
    struct = _structure(rms_list, hop, total)
    return {
        "engine": "librosa",
        "degraded": False,
        "duration": round(total, 2),
        "bpm": round(float(tempo), 1) if tempo else None,
        "beat_positions": [round(float(b), 3) for b in beats],
        "beat_count": len(beats),
        "onset_times": onsets,
        "rhythmic_density": density,
        "rms_energy": {"hop_sec": 0.1, "values": _downsample(rms_list, hop)},
        "onset_strength": {"hop_sec": 0.1, "values": _downsample(env_list, hop)},
        "spectral_centroid": {"hop_sec": 0.1, "values": _downsample([float(v) for v in cent], hop)},
        "brightness_source": "librosa spectral_centroid",
        "structure": struct,
    }


def analyze_numpy(path, rate=22050):
    import numpy as np  # noqa
    with wave.open(path, "rb") as wf:
        sr = wf.getframerate()
        ch = wf.getnchannels()
        width = wf.getsampwidth()
        raw = wf.readframes(wf.getnframes())
    data = np.frombuffer(raw, dtype={1: np.int8, 2: np.int16, 4: np.int32}[width]).astype(np.float32)
    if ch > 1:
        data = data.reshape(-1, ch).mean(axis=1)
    data /= float(2 ** (8 * width - 1))
    hop = max(1, int(round(HOP_SEC * sr)))
    frames = max(1, len(data) // hop)
    rms, cent = [], []
    win = np.hanning(1024)
    for i in range(frames):
        seg = data[i * hop:(i + 1) * hop]
        rms.append(float(np.sqrt(np.mean(seg ** 2))))
        if len(seg) >= 1024:
            spec = np.abs(np.fft.rfft(seg[:1024] * win))
            freqs = np.fft.rfftfreq(1024, 1.0 / sr)
            total = spec.sum() or 1e-9
            cent.append(float((spec * freqs).sum() / total))
    total_sec = len(data) / float(sr)
    env = _onset_envelope(rms, HOP_SEC)
    bpm, beats, bpm_raw = _tempo_from_onset(env, HOP_SEC)
    onsets, density = _onsets(env, HOP_SEC, total_sec)
    return {
        "engine": "numpy",
        "degraded": False,
        "duration": round(total_sec, 2),
        "bpm": bpm, "bpm_raw": bpm_raw, "beat_positions": beats, "beat_count": len(beats),
        "bpm_note": ("BPM 为自相关估计，可能存在倍频误差；bpm_raw 是未折叠的原始值。" if bpm_raw else None),
        "onset_times": onsets, "rhythmic_density": density,
        "rms_energy": {"hop_sec": 0.1, "values": _downsample(rms, HOP_SEC)},
        "onset_strength": {"hop_sec": 0.1, "values": _downsample(env, HOP_SEC)},
        "spectral_centroid": {"hop_sec": 0.1, "values": _downsample(cent, HOP_SEC)} if cent else None,
        "brightness_source": "numpy FFT spectral_centroid" if cent else None,
        "structure": _structure(rms, HOP_SEC, total_sec),
    }


def analyze_stdlib(path):
    """wave + audioop：零第三方依赖的 RMS / 过零率 / onset / 自相关测速。"""
    try:
        import audioop
    except ImportError:  # Python 3.13+
        audioop = None
    with wave.open(path, "rb") as wf:
        sr = wf.getframerate()
        ch = wf.getnchannels()
        width = wf.getsampwidth()
        nframes = wf.getnframes()
        hop = max(1, int(round(HOP_SEC * sr)))
        rms, zcr = [], []
        while True:
            frames = wf.readframes(hop)
            if not frames:
                break
            if audioop:
                rms.append(audioop.rms(frames, width) / float(2 ** (8 * width - 1)))
                samples = len(frames) // (width * ch)
                crossings = audioop.cross(frames, width)
                zcr.append(crossings / float(samples or 1))
            else:
                rms.append(_manual_rms(frames, width))
                zcr.append(_manual_zcr(frames, width))
    total_sec = nframes / float(sr) if sr else 0.0
    env = _onset_envelope(rms, HOP_SEC)
    bpm, beats, bpm_raw = _tempo_from_onset(env, HOP_SEC)
    onsets, density = _onsets(env, HOP_SEC, total_sec)
    return {
        "engine": "stdlib(audioop)" if audioop else "stdlib(pure)",
        "degraded": False,
        "duration": round(total_sec, 2),
        "sample_rate": sr, "channels": ch,
        "bpm": bpm, "bpm_raw": bpm_raw, "beat_positions": beats, "beat_count": len(beats),
        "bpm_note": ("BPM 为自相关估计，可能存在倍频误差；bpm_raw 是未折叠的原始值。" if bpm_raw else None),
        "onset_times": onsets, "rhythmic_density": density,
        "rms_energy": {"hop_sec": 0.1, "values": _downsample(rms, HOP_SEC)},
        "onset_strength": {"hop_sec": 0.1, "values": _downsample(env, HOP_SEC)},
        "zero_crossing_rate": {"hop_sec": 0.1, "values": _downsample(zcr, HOP_SEC)},
        "brightness_source": "zero_crossing_rate（过零率，音色亮度代理）",
        "spectral_centroid": None,
        "structure": _structure(rms, HOP_SEC, total_sec),
    }


def _manual_rms(frames, width):
    import struct
    fmt = {1: "b", 2: "h", 4: "i"}[width]
    n = len(frames) // width
    vals = struct.unpack("<%d%s" % (n, fmt), frames[:n * width])
    peak = float(2 ** (8 * width - 1))
    return math.sqrt(sum(v * v for v in vals) / float(n)) / peak if n else 0.0


def _manual_zcr(frames, width):
    import struct
    fmt = {1: "b", 2: "h", 4: "i"}[width]
    n = len(frames) // width
    vals = struct.unpack("<%d%s" % (n, fmt), frames[:n * width])
    if n < 2:
        return 0.0
    cross = sum(1 for i in range(1, n) if (vals[i - 1] < 0) != (vals[i] < 0))
    return cross / float(n)


def analyze(audio_path, log=None):
    cfg = common.config()
    log = log or common.Log("analyze_music")
    probe = audioprobe.probe(audio_path, log=log)
    duration = probe.get("duration")
    decoded = os.path.join(common.path("workspace_audio"), "analysis_mono_22050.wav")
    ok, tool, detail = audioprobe.decode_to_wav(audio_path, decoded)
    fallbacks = []
    if not ok:
        log.warn("无法解码音频（%s），音乐分析降级为时长+结构提示" % detail)
        fallbacks.append({"wanted": "音频解码(ffmpeg/afconvert)",
                          "used": "仅时长与容器信息", "impact": "节奏/能量分析不可用"})
        return {
            "engine": "none", "degraded": True,
            "duration": duration, "bpm": None, "beat_positions": [], "beat_count": 0,
            "onset_times": [], "rhythmic_density": None,
            "rms_energy": None, "onset_strength": None, "spectral_centroid": None,
            "structure": {"sections": [], "quiet_sections": [], "peak_sections": [],
                          "build_sections": [], "breakdowns": [],
                          "ending_character": "未知（无法解码）"},
            "probe": probe, "fallbacks": fallbacks,
            "note": "无法解码音频：请安装 ffmpeg（brew install ffmpeg）后重跑以获得节奏/能量实测。",
        }
    if tool != "ffmpeg":
        fallbacks.append({"wanted": "ffmpeg 解码", "used": tool, "impact": "无（Mac 自带工具，精度足够）"})
    log.step("decode", "ok", "解码为单声道 22050Hz（%s）" % tool)

    result = None
    if common.have_python_module("librosa"):
        try:
            result = analyze_librosa(decoded)
        except Exception as exc:
            log.warn("librosa 分析失败（%s），降级" % exc)
    if result is None and common.have_python_module("numpy"):
        try:
            result = analyze_numpy(decoded)
        except Exception as exc:
            log.warn("numpy 分析失败（%s），降级" % exc)
    if result is None:
        result = analyze_stdlib(decoded)
        fallbacks.append({"wanted": "librosa/numpy",
                          "used": "标准库 wave+audioop",
                          "impact": "无频谱质心（用音色亮度代理），BPM 为自相关估计"})
    result["decode_tool"] = tool
    result["probe"] = probe
    result["fallbacks"] = fallbacks
    result["degraded"] = False

    # 用真实时长校正（容器时长更可信）
    if duration and abs((result.get("duration") or 0) - duration) > 0.5:
        result["duration"] = round(duration, 2)
    log.step("analyze", "ok", "引擎=%s BPM=%s 段落=%d"
             % (result["engine"], result.get("bpm"), len(result["structure"].get("sections", []))),
             result["engine"])
    log.save()
    return result


def guidance(analysis):
    """把分析翻译成**会影响画面**的导演参数（规则 21）。"""
    bpm = analysis.get("bpm")
    density = analysis.get("rhythmic_density") or 0
    struct = analysis.get("structure") or {}
    out = {
        "bpm": bpm,
        "cut_speed": ("每拍一切（快剪）" if bpm and bpm >= 120 else
                      "两拍一切" if bpm and bpm >= 90 else "四拍/一小节一切（慢剪）"),
        "animation_timing": ("animation on twos + 重拍 hold" if density < 1.2 else
                             "animation on twos + 连续抽帧" if density < 2.5 else
                             "animation on ones 局部 + 密集抽帧"),
        "motion_scale": ("小幅度 isolation 为主" if (analysis.get("structure", {})
                                                    .get("energy_percentiles", {}).get("p90", 0) or 0) < 0.3
                         else "中等幅度全身动作"),
        "density_rule": "背景图形密度随 RMS 包络上升，峰值段允许满构图，quiet 段留白",
        "transition_rule": "在 breakdown/build 边界做转场，不在句子中间硬切",
        "ending_rule": struct.get("ending_character"),
    }
    peaks = struct.get("peak_sections") or []
    quiets = struct.get("quiet_sections") or []
    out["peak_windows"] = peaks
    out["quiet_windows"] = quiets
    return out


def render_md(a):
    st = a.get("structure") or {}
    lines = ["# 音乐分析（实测）", ""]
    lines.append("- 分析引擎：`%s`%s" % (a.get("engine"), "（已降级）" if a.get("degraded") else ""))
    lines.append("- 解码工具：`%s`" % a.get("decode_tool", "-"))
    lines.append("- 时长：%s" % common.mmss(a.get("duration")))
    lines.append("- BPM（估计）：%s" % (a.get("bpm") or "未测出"))
    lines.append("- 拍数：%s　起音密度：%s 次/秒" % (a.get("beat_count"), a.get("rhythmic_density")))
    p = st.get("energy_percentiles") or {}
    if p:
        lines.append("- 能量分位：p10=%s p50=%s p90=%s max=%s"
                     % (p.get("p10"), p.get("p50"), p.get("p90"), p.get("max")))
    lines.append("- 收束性格：%s" % st.get("ending_character", "-"))
    lines.append("")
    if st.get("sections"):
        lines.append("## 结构段落")
        lines.append("")
        lines.append("| 段 | 时间 | 能量 |")
        lines.append("|----|------|------|")
        for s in st["sections"]:
            lines.append("| %s | %s–%s | %s |" % (s["label"], common.fmt_clock(s["start"]),
                                                  common.fmt_clock(s["end"]), s["label"]))
        lines.append("")
    if st.get("peak_sections"):
        lines.append("**高潮段**：%s" % "，".join("%s–%s" % (common.fmt_clock(x[0]), common.fmt_clock(x[1]))
                                                for x in st["peak_sections"]))
    if st.get("quiet_sections"):
        lines.append("**低谷段**：%s" % "，".join("%s–%s" % (common.fmt_clock(x[0]), common.fmt_clock(x[1]))
                                                for x in st["quiet_sections"]))
    if st.get("build_sections"):
        lines.append("**攀升段**：%s" % "，".join("%s–%s" % (common.fmt_clock(x["start"]),
                                                          common.fmt_clock(x["end"]))
                                                for x in st["build_sections"]))
    if st.get("breakdowns"):
        lines.append("**断点/落差**：%s" % "，".join("%s–%s" % (common.fmt_clock(x["start"]),
                                                            common.fmt_clock(x["end"]))
                                                  for x in st["breakdowns"]))
    lines.append("")
    g = guidance(a)
    lines.append("## 这些数字如何影响画面（规则 21）")
    lines.append("")
    lines.append("- 剪辑速度：%s" % g["cut_speed"])
    lines.append("- 动画节律：%s" % g["animation_timing"])
    lines.append("- 动作幅度：%s" % g["motion_scale"])
    lines.append("- 背景密度：%s" % g["density_rule"])
    lines.append("- 转场：%s" % g["transition_rule"])
    lines.append("- 收束：%s" % g["ending_rule"])
    lines.append("")
    if a.get("fallbacks"):
        lines.append("## 降级记录")
        lines.append("")
        for f in a["fallbacks"]:
            lines.append("- %s 不可用 → %s（影响：%s）" % (f["wanted"], f["used"], f["impact"]))
    return "\n".join(lines) + "\n"


def main(argv=None):
    ap = argparse.ArgumentParser(description="音乐结构实测（BPM/能量/段落）")
    common.add_common_args(ap)
    ap.add_argument("--audio", help="显式指定音频")
    args = ap.parse_args(argv)
    common.apply_common_args(args)

    audio = args.audio
    if not audio:
        import discover_inputs
        probe = common.read_json(os.path.join(common.path("workspace_analysis"), "audio_probe.json"))
        audio = (probe or {}).get("workspace_copy") or (probe or {}).get("source_path")
        if not audio or not os.path.isfile(audio):
            audio = discover_inputs.discover()["audio"]["path"]
    if not audio or not os.path.isfile(audio):
        msg = "没有找到音频，无法分析音乐。"
        if args.json:
            common.emit({"engine": "none", "degraded": True, "error": msg}, True)
        else:
            common.echo(msg)
        return 2

    analysis = analyze(audio)
    common.write_json(os.path.join(common.path("workspace_analysis"), "music_analysis.json"), analysis)
    common.write_text(os.path.join(common.path("output_latest"), "music_analysis.md"), render_md(analysis))
    if args.json:
        common.emit(analysis, True)
    else:
        common.echo(render_md(analysis))
    return 0


if __name__ == "__main__":
    sys.exit(main())
