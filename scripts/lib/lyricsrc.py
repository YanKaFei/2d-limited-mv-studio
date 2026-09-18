#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""lyricsrc —— 歌词来源发现、解析、ASR 链（规则 12-17）。

优先级（严格按序，见 SKILL.md）：
  01 音频内嵌歌词（ID3 USLT/SYLT、Vorbis LYRICS、MP4 ©lyr）
  02 同目录 .lrc
  03 同目录 .srt
  04 同目录 .vtt
  05 同目录 .txt（无时间轴，标记 timed=false）
  06 自动 ASR（whisperx → faster-whisper → whisper → mlx_whisper → whisper.cpp）

已有可靠歌词时**不重复 ASR**（规则 12）。
"""

import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import audioprobe  # noqa: E402
import common  # noqa: E402

PRIORITY = ["embedded", "lrc", "srt", "vtt", "txt", "asr"]

_LRC_TIME = re.compile(r"\[(\d{1,3}):(\d{1,2}(?:[.:]\d{1,3})?)\]")
_LRC_META = re.compile(r"^\[(ar|ti|al|by|offset|re|ve|length):(.*)\]$", re.I)
_SRT_TIME = re.compile(
    r"(\d{1,2}):(\d{2}):(\d{2})[,.](\d{1,3})\s*-->\s*(\d{1,2}):(\d{2}):(\d{2})[,.](\d{1,3})")


# ------------------------------------------------------------ 来源发现
def search_dirs(audio_path):
    """歌词可能出现的目录：音频同目录 → input/lyrics → input/ → input/music → 项目根。"""
    dirs = []
    for d in [os.path.dirname(os.path.abspath(audio_path)),
              common.path("input_lyrics"),
              os.path.dirname(common.path("input_lyrics")),
              common.path("input_music"),
              common.PROJECT_ROOT]:
        d = os.path.abspath(d)
        if os.path.isdir(d) and d not in dirs:
            dirs.append(d)
    return dirs


def find_sidecar_lyrics(audio_path):
    """按 .lrc > .srt > .vtt > .txt 优先级找同名词／任意歌词文件。"""
    stem = os.path.splitext(os.path.basename(audio_path))[0]
    dirs = search_dirs(audio_path)
    found = []
    for d in dirs:
        try:
            names = sorted(os.listdir(d))
        except OSError:
            continue
        for ext in (".lrc", ".srt", ".vtt", ".txt"):
            # 同名优先
            for name in names:
                if name.lower() == (stem + ext).lower():
                    found.append((ext, os.path.join(d, name), "same-name"))
            if found and found[-1][0] == ext and found[-1][2] == "same-name":
                break
        for ext in (".lrc", ".srt", ".vtt", ".txt"):
            for name in names:
                if name.lower().endswith(ext) and not name.startswith("."):
                    p = os.path.join(d, name)
                    if not any(p == f[1] for f in found):
                        found.append((ext, p, "dir-scan"))
    order = {".lrc": 0, ".srt": 1, ".vtt": 2, ".txt": 3}
    found.sort(key=lambda f: order[f[0]])
    if not found:
        return None
    kind = found[0][0].lstrip(".")
    return {"kind": kind, "path": found[0][1], "how": found[0][2], "candidates": found}


# ------------------------------------------------------------ 格式解析
def parse_lyrics_file(path):
    ext = os.path.splitext(path)[1].lower()
    with open(path, "r", encoding="utf-8", errors="replace") as fh:
        text = fh.read()
    if ext == ".lrc":
        return parse_lrc(text)
    if ext == ".srt":
        return parse_srt(text)
    if ext == ".vtt":
        return parse_vtt(text)
    return parse_txt(text)


def parse_lrc(text):
    lines = []
    meta = {}
    offset = 0.0
    for raw in text.splitlines():
        raw = raw.strip()
        if not raw:
            continue
        m = _LRC_META.match(raw)
        if m:
            meta[m.group(1).lower()] = m.group(2).strip()
            if m.group(1).lower() == "offset":
                try:
                    offset = float(m.group(2)) / 1000.0
                except ValueError:
                    offset = 0.0
            continue
        times = _LRC_TIME.findall(raw)
        if not times:
            continue
        lyric = _LRC_TIME.sub("", raw).strip()
        if not lyric:
            continue
        for mm, ss in times:
            start = int(mm) * 60 + float(ss.replace(":", ".")) + offset
            lines.append({"start": round(start, 2), "end": None, "text": lyric})
    lines.sort(key=lambda l: l["start"])
    for i, line in enumerate(lines):
        if i + 1 < len(lines):
            line["end"] = round(lines[i + 1]["start"], 2)
    if lines:
        last = lines[-1]
        if last["end"] is None:
            last["end"] = round(last["start"] + 4.0, 2)
    return {"source": "lrc", "timed": True, "lines": lines, "meta": meta,
            "language_hint": detect_language(" ".join(l["text"] for l in lines)),
            "confidence": "high"}


def _tc(h, m, s, ms):
    return int(h) * 3600 + int(m) * 60 + int(s) + int(ms.ljust(3, "0")) / 1000.0


def parse_srt(text):
    lines = []
    for block in re.split(r"\n\s*\n", text.replace("\r\n", "\n")):
        rows = [r.strip() for r in block.splitlines() if r.strip()]
        if not rows:
            continue
        idx = 0
        if rows[0].isdigit():
            idx = 1
        if idx >= len(rows):
            continue
        m = _SRT_TIME.search(rows[idx])
        if not m:
            continue
        start = _tc(*m.groups()[:4])
        end = _tc(*m.groups()[4:])
        body = " ".join(rows[idx + 1:]).strip()
        if body:
            lines.append({"start": round(start, 2), "end": round(end, 2), "text": body})
    lines.sort(key=lambda l: l["start"])
    return {"source": "srt", "timed": True, "lines": lines, "meta": {},
            "language_hint": detect_language(" ".join(l["text"] for l in lines)),
            "confidence": "high"}


def parse_vtt(text):
    body = re.sub(r"^WEBVTT.*?(\n\n|$)", "", text, flags=re.S)
    parsed = parse_srt(body)
    parsed["source"] = "vtt"
    return parsed


def parse_txt(text):
    lines = []
    for raw in text.splitlines():
        row = raw.strip()
        if not row or row.startswith("#"):
            continue
        # 允许 "0:12.3 歌词" 这种简单时间轴写法
        m = re.match(r"^\[?(\d{1,2}):(\d{2}(?:\.\d{1,3})?)\]?[\s\-–—]*(.+)$", row)
        if m:
            start = int(m.group(1)) * 60 + float(m.group(2))
            lines.append({"start": round(start, 2), "end": None, "text": m.group(3).strip()})
        else:
            lines.append({"start": None, "end": None, "text": row})
    timed = all(l["start"] is not None for l in lines) and bool(lines)
    if timed:
        lines.sort(key=lambda l: l["start"])
        for i, line in enumerate(lines):
            if i + 1 < len(lines):
                line["end"] = round(lines[i + 1]["start"], 2)
        if lines[-1]["end"] is None:
            lines[-1]["end"] = round(lines[-1]["start"] + 4.0, 2)
    return {"source": "txt", "timed": timed, "lines": lines, "meta": {},
            "language_hint": detect_language(" ".join(l["text"] for l in lines)),
            "confidence": "high" if timed else "timed-missing"}


_EN_STOP = set("""the you and me my to in of is it that we on for with your are be a an
do don't can't i'm love all no not so if but at from as they their them he she his her
what when where why how was were will would can could there here this these those""".split())

_ROMAJI_HINT = re.compile(
    r"\b(kono|sono|ano|boku|kimi|watashi|wa|ga|wo|ni|no|desu|masu|suru|shita|nai|da|yo|ne|"
    r"sekai|kokoro|yume|sora|machi|hitori|zutto|mou|ima|doko|nani)\b")


def detect_language(text):
    """粗粒度语言判定。绝不默认中文（规则 15）。

    拉丁字母内容还会区分「英语」与「罗马字日文」——后者按 unknown 处理，
    避免把日文歌当成英文歌去理解语义。
    """
    if not text:
        return "unknown"
    cjk = len(re.findall(r"[\u4e00-\u9fff]", text))
    kana = len(re.findall(r"[\u3040-\u30ff]", text))
    hangul = len(re.findall(r"[\uac00-\ud7af]", text))
    latin = len(re.findall(r"[A-Za-z]", text))
    if kana and kana > max(cjk, latin) * 0.15:
        return "ja"
    if hangul > max(cjk, latin) * 0.15:
        return "ko"
    if cjk >= latin:
        return "zh"
    if latin:
        tokens = re.findall(r"[A-Za-z']+", text.lower())
        if not tokens:
            return "en"
        hits = sum(1 for t in tokens if t in _EN_STOP)
        if hits:
            return "en"          # 有功能词 = 英语，优先判定
        romaji = set(m.group(0) for m in _ROMAJI_HINT.finditer(text.lower()))
        vowel_end = sum(1 for t in tokens if t and t[-1] in "aeiou")
        if len(romaji) >= 2 or (len(romaji) >= 1 and vowel_end / float(len(tokens)) > 0.6):
            return "romaji/unknown"
        if vowel_end / float(len(tokens)) > 0.75:
            return "romaji/unknown"
        return "en"
    return "unknown"


# ------------------------------------------------------------------ ASR
ASR_CHAIN = [
    ("whisperx", ["whisperx"], True),
    ("faster-whisper", ["faster_whisper"], True),
    ("mlx-whisper", ["mlx_whisper"], True),
    ("openai-whisper", ["whisper"], True),
]


def asr_available():
    """返回可用 ASR 后端列表 [(name, how)]，how 为 'python' 或 'cli'。"""
    out = []
    for name, mods, _ in ASR_CHAIN:
        for mod in mods:
            if common.have_python_module(mod):
                out.append((name, "python:%s" % mod))
                break
    for cli, name in [("whisper", "openai-whisper-cli"), ("whisperx", "whisperx-cli"),
                      ("mlx_whisper", "mlx-whisper-cli"), ("whisper-cli", "whisper.cpp"),
                      ("main", "whisper.cpp")]:
        p = common.which(cli)
        if p and not any(o[0] == name for o in out):
            out.append((name, "cli:%s" % p))
    return out


def separate_vocals(src, out_dir, log=None):
    """可选：Demucs 分离人声（规则 14）。不可用则返回 None，绝不阻断。"""
    demucs = None
    if common.have_python_module("demucs"):
        demucs = [sys.executable, "-m", "demucs"]
    elif common.which("demucs"):
        demucs = ["demucs"]
    if not demucs:
        if log:
            log.fallback("Demucs 人声分离", "直接对整体混音做 ASR",
                         "识别率可能下降，但不阻断流程")
        return None
    rc, out, err = common.run(demucs + ["--two-stems", "vocals", "-o", out_dir, src], timeout=3600)
    if rc != 0:
        if log:
            log.warn("Demucs 运行失败（%s），改为直接 ASR" % (err or out)[:200])
        return None
    base = os.path.splitext(os.path.basename(src))[0]
    cand = os.path.join(out_dir, "htdemucs", base, "vocals.wav")
    if not os.path.isfile(cand):
        for root, _dirs, files in os.walk(out_dir):
            for f in files:
                if f == "vocals.wav":
                    cand = os.path.join(root, f)
                    break
    return cand if os.path.isfile(cand) else None


def run_asr(audio_path, model="small", language=None, log=None, timeout=3600):
    """按链降级执行 ASR。返回 (result_dict, backend) 或 (None, None)。"""
    backends = asr_available()
    if not backends:
        return None, None
    for name, how in backends:
        try:
            if how.startswith("python:"):
                res = _asr_python(name, how.split(":", 1)[1], audio_path, model, language, timeout)
            else:
                res = _asr_cli(name, how.split(":", 1)[1], audio_path, model, language, timeout)
        except Exception as exc:
            if log:
                log.warn("ASR 后端 %s 失败: %s" % (name, exc))
            continue
        if res and res.get("lines"):
            res["source"] = "asr"
            res["backend"] = name
            res["language_hint"] = res.get("language_hint") or detect_language(
                " ".join(l["text"] for l in res["lines"]))
            return res, name
    return None, None


def _asr_python(name, mod, audio, model, language, timeout):
    if name == "whisperx":
        import whisperx  # noqa
        audio_data = whisperx.load_audio(audio)
        asr_model = whisperx.load_model(model, device="cpu", compute_type="int8")
        result = asr_model.transcribe(audio_data, language=language)
        try:
            align_model, meta = whisperx.load_align_model(language_code=result.get("language", "en"),
                                                          device="cpu")
            result = whisperx.align(result["segments"], align_model, meta, audio_data, "cpu")
        except Exception:
            pass
        lines = []
        for seg in result.get("segments", []):
            entry = {"start": round(float(seg["start"]), 2), "end": round(float(seg["end"]), 2),
                     "text": (seg.get("text") or "").strip()}
            if seg.get("words"):
                entry["words"] = [{"start": round(float(w.get("start", 0)), 2),
                                   "end": round(float(w.get("end", 0)), 2),
                                   "text": w.get("word", "")} for w in seg["words"] if w.get("start") is not None]
            lines.append(entry)
        return {"lines": lines, "raw": {"language": result.get("language")},
                "language_hint": result.get("language"), "confidence": "medium"}
    if name == "faster-whisper":
        from faster_whisper import WhisperModel
        m = WhisperModel(model, device="cpu", compute_type="int8")
        segments, info = m.transcribe(audio, language=language, word_timestamps=True)
        lines = []
        for seg in segments:
            lines.append({"start": round(seg.start, 2), "end": round(seg.end, 2),
                          "text": (seg.text or "").strip()})
        return {"lines": lines, "raw": {"language": info.language},
                "language_hint": info.language,
                "confidence": round(float(getattr(info, "language_probability", 0.9)), 3)}
    if name == "mlx-whisper":
        import mlx_whisper  # noqa
        res = mlx_whisper.transcribe(audio, path_or_hf_repo="mlx-community/whisper-%s-mlx" % model)
        lines = [{"start": round(s["start"], 2), "end": round(s["end"], 2),
                  "text": (s.get("text") or "").strip()} for s in res.get("segments", [])]
        return {"lines": lines, "raw": {"language": res.get("language")},
                "language_hint": res.get("language"), "confidence": "medium"}
    if name == "openai-whisper":
        import whisper  # noqa
        m = whisper.load_model(model)
        res = m.transcribe(audio, language=language)
        lines = [{"start": round(s["start"], 2), "end": round(s["end"], 2),
                  "text": (s.get("text") or "").strip()} for s in res.get("segments", [])]
        return {"lines": lines, "raw": {"language": res.get("language")},
                "language_hint": res.get("language"), "confidence": "medium"}
    return None


def _asr_cli(name, exe, audio, model, language, timeout):
    if name == "whisper.cpp":
        args = [exe, "-m", os.environ.get("WHISPER_CPP_MODEL", "models/ggml-base.bin"),
                "-f", audio, "-oj"]
        rc, out, err = common.run(args, timeout=timeout)
        if rc != 0:
            return None
        import json
        lines = []
        for seg in json.loads(out).get("transcription", []):
            lines.append({"start": round(seg["timestamps"]["from"] / 1000.0, 2)
                          if isinstance(seg.get("timestamps"), dict) else 0,
                          "text": seg.get("text", "").strip()})
        return {"lines": lines, "confidence": "low"}
    args = [exe, audio, "--model", model, "--output_format", "json", "--output_dir",
            common.path("workspace_temp")]
    if language:
        args += ["--language", language]
    rc, out, err = common.run(args, timeout=timeout)
    if rc != 0:
        return None
    import glob
    import json
    stem = os.path.splitext(os.path.basename(audio))[0]
    cand = os.path.join(common.path("workspace_temp"), stem + ".json")
    if not os.path.isfile(cand):
        hits = glob.glob(os.path.join(common.path("workspace_temp"), "*.json"))
        cand = hits[0] if hits else None
    if not cand:
        return None
    data = common.read_json(cand, {})
    lines = [{"start": round(s["start"], 2), "end": round(s["end"], 2),
              "text": (s.get("text") or "").strip()} for s in data.get("segments", [])]
    return {"lines": lines, "language_hint": data.get("language"), "confidence": "medium"}


# ---------------------------------------------------------------- 工具
def to_lrc(lines, with_end=True):
    out = []
    for line in lines:
        start = line.get("start")
        if start is None:
            continue
        mm = int(start // 60)
        ss = start - mm * 60
        out.append("[%02d:%05.2f]%s" % (mm, ss, line.get("text", "")))
    return "\n".join(out) + "\n"


def spread_untimed(lines, start, end):
    """无时间轴歌词的**兜底**均分（必须被显式标记 estimated）。"""
    if not lines:
        return []
    span = max(0.1, end - start)
    step = span / float(len(lines))
    out = []
    for i, line in enumerate(lines):
        s = start + i * step
        out.append({"start": round(s, 2), "end": round(s + step, 2),
                    "text": line.get("text", ""), "estimated": True})
    return out
