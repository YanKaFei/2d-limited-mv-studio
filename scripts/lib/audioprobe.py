#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""audioprobe —— 音频探测与内嵌歌词提取。

三级降级（规则 10 / 12 / 94）：
  1) ffprobe            —— 有就用，最准
  2) macOS afinfo       —— Mac 自带，覆盖 mp3/m4a/wav/aac/flac
  3) 纯 Python 解析器    —— 零依赖兜底：MP3 帧头 / WAV / FLAC STREAMINFO /
                           MP4 moov / Ogg 页尾 granule

内嵌歌词（优先级 01）：
  * ID3v2 的 USLT（无时间轴）与 SYLT（带时间轴）
  * FLAC/OGG 的 Vorbis Comment: LYRICS / UNSYNCHRONISED LYRICS
  * MP4 的 ©lyr

解码（给音乐分析用）：
  ffmpeg → afconvert（macOS 自带）→ 源本身是 WAV 则直接用

绝不修改用户原始文件；所有派生文件写到调用方指定的 workspace 路径。
"""

import os
import re
import struct
import sys
import wave

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common  # noqa: E402

# ---------------------------------------------------------------- MP3 表
_MP3_BITRATES = {
    ("1", 3): [0, 32, 40, 48, 56, 64, 80, 96, 112, 128, 160, 192, 224, 256, 320],
    ("1", 2): [0, 32, 48, 56, 64, 80, 96, 112, 128, 160, 192, 224, 256, 320, 384],
    ("1", 1): [0, 32, 64, 96, 128, 160, 192, 224, 256, 288, 320, 352, 384, 416, 448],
    ("2", 1): [0, 32, 48, 56, 64, 80, 96, 112, 128, 144, 160, 176, 192, 224, 256],
    ("2", 2): [0, 8, 16, 24, 32, 40, 48, 56, 64, 80, 96, 112, 128, 144, 160],
    ("2", 3): [0, 8, 16, 24, 32, 40, 48, 56, 64, 80, 96, 112, 128, 144, 160],
}
_MP3_RATES = {"1": [44100, 48000, 32000], "2": [22050, 24000, 16000], "2.5": [11025, 12000, 8000]}
_MP3_SPF = {("1", 1): 384, ("1", 2): 1152, ("1", 3): 1152,
            ("2", 1): 384, ("2", 2): 1152, ("2", 3): 576, ("2.5", 3): 576}


def _empty(error=None):
    return {"format": None, "codec": None, "duration": None, "sample_rate": None,
            "channels": None, "bitrate": None, "probe_source": None, "error": error}


# ------------------------------------------------------------------ 对外
def probe(path, log=None):
    """返回音频基础信息。永远返回 dict，不抛异常。"""
    path = os.path.abspath(path)
    if not os.path.isfile(path):
        return _empty("文件不存在: %s" % path)

    info = _probe_ffprobe(path)
    if info:
        info["probe_source"] = "ffprobe"
        info["error"] = None
        return info
    if log:
        log.fallback("ffprobe", "afinfo / 纯 Python 解析", "时长精度略降，不影响分段")

    info = _probe_afinfo(path)
    if info:
        info["probe_source"] = "afinfo"
        info["error"] = None
        return info

    info = _probe_pure(path)
    if info and info.get("duration"):
        info["probe_source"] = "pure-python"
        info["error"] = None
        return info

    out = info or _empty()
    if not out.get("error"):
        out["error"] = "无法解析该音频（ffprobe/afinfo/纯 Python 均失败）"
    out["probe_source"] = "none"
    return out


def _probe_ffprobe(path):
    if not common.which("ffprobe"):
        return None
    rc, out, err = common.run([
        "ffprobe", "-v", "error", "-print_format", "json",
        "-show_format", "-show_streams", path], timeout=60)
    if rc != 0 or not out.strip():
        return None
    try:
        import json
        data = json.loads(out)
    except Exception:
        return None
    stream = None
    for s in data.get("streams", []):
        if s.get("codec_type") == "audio":
            stream = s
            break
    if stream is None:
        return None
    fmt = data.get("format", {})
    dur = fmt.get("duration") or stream.get("duration")
    return {
        "format": (fmt.get("format_name") or "").split(",")[0] or None,
        "codec": stream.get("codec_name"),
        "duration": float(dur) if dur else None,
        "sample_rate": int(stream["sample_rate"]) if stream.get("sample_rate") else None,
        "channels": stream.get("channels"),
        "bitrate": int(fmt["bit_rate"]) if fmt.get("bit_rate") else None,
    }


def _probe_afinfo(path):
    if not common.which("afinfo"):
        return None
    rc, out, err = common.run(["afinfo", path], timeout=60)
    text = (out or "") + (err or "")
    if rc != 0 or "Data format" not in text:
        return None
    dur = None
    m = re.search(r"estimated duration:\s*([0-9.]+)\s*sec", text)
    if m:
        dur = float(m.group(1))
    rate = channels = None
    m = re.search(r"Data format:\s*(\d+)\s*ch,\s*(\d+)\s*Hz,\s*([.\w/]+)", text)
    codec = None
    if m:
        channels = int(m.group(1))
        rate = int(m.group(2))
        codec = m.group(3).lstrip(".")
    bitrate = None
    m = re.search(r"bit rate:\s*(\d+)\s*bits per second", text)
    if m:
        bitrate = int(m.group(1))
    m = re.search(r"File type ID:\s*(\S+)", text)
    fmt = m.group(1) if m else None
    return {"format": fmt, "codec": codec, "duration": dur, "sample_rate": rate,
            "channels": channels, "bitrate": bitrate}


def _probe_pure(path):
    ext = os.path.splitext(path)[1].lower()
    head = common.read_bytes(path, 16)
    try:
        if head[:4] == b"RIFF" and head[8:12] == b"WAVE" or ext == ".wav":
            return parse_wav(path)
        if head[:4] == b"fLaC":
            return parse_flac(path)
        if head[:4] == b"OggS":
            return parse_ogg(path)
        if head[4:8] == b"ftyp":
            return parse_mp4(path)
        if head[:3] == b"ID3" or (len(head) > 1 and head[0] == 0xFF and (head[1] & 0xE0) == 0xE0):
            return parse_mp3(path)
    except Exception as exc:
        return _empty("%s: %s" % (type(exc).__name__, exc))
    return _empty("无法识别的容器格式: %s" % (ext or "?"))


# ------------------------------------------------------------- 纯 Python
def _id3v2_size(head10):
    size = 0
    for b in head10[6:10]:
        size = (size << 7) | (b & 0x7F)
    return size + 10


def parse_mp3(path):
    """零依赖 MP3 帧解析。返回 duration/sample_rate/channels/bitrate。"""
    data = common.read_bytes(path)
    offset = 0
    tags = {}
    if data[:3] == b"ID3":
        offset = _id3v2_size(data[:10])
        tags = _parse_id3v2(data[:offset])
    end = len(data)
    if data[end - 128:end - 125] == b"TAG":
        end -= 128

    frames = 0
    samples = 0
    bitrates = []
    rate = channels = spf = None
    xing_frames = None
    pos = offset
    limit = min(end, offset + 400000)
    first = True
    while pos + 4 <= end:
        b0, b1, b2, b3 = data[pos], data[pos + 1], data[pos + 2], data[pos + 3]
        if b0 != 0xFF or (b1 & 0xE0) != 0xE0:
            pos += 1
            if frames and pos > limit:
                break
            continue
        version_bits = (b1 >> 3) & 0x3
        layer_bits = (b1 >> 1) & 0x3
        if version_bits == 1 or layer_bits == 0:
            pos += 1
            continue
        ver = {0: "2.5", 2: "2", 3: "1"}[version_bits]
        layer = {1: 3, 2: 2, 3: 1}[layer_bits]
        br_index = (b2 >> 4) & 0xF
        sr_index = (b2 >> 2) & 0x3
        padding = (b2 >> 1) & 0x1
        if br_index in (0, 15) or sr_index == 3:
            pos += 1
            continue
        key = (ver if ver in ("1", "2") else "2", layer)
        table = _MP3_BITRATES.get(key)
        if not table:
            pos += 1
            continue
        bitrate = table[br_index] * 1000
        sample_rate = _MP3_RATES[ver][sr_index]
        spf = _MP3_SPF.get((ver if ver in ("1", "2") else "2", layer),
                           _MP3_SPF.get(("2", layer), 1152))
        if layer == 1:
            frame_len = int((12 * bitrate / sample_rate + padding) * 4)
        elif ver == "1":
            frame_len = int(144 * bitrate / sample_rate + padding)
        else:
            frame_len = int(72 * bitrate / sample_rate + padding)
        if frame_len <= 4:
            pos += 1
            continue
        if rate is None:
            rate = sample_rate
            mode = (b3 >> 6) & 0x3
            channels = 1 if mode == 3 else 2
        if first:
            first = False
            side = 17 if channels == 1 else 32
            if ver != "1":
                side = 9 if channels == 1 else 17
            xoff = pos + 4 + side
            marker = data[xoff:xoff + 4]
            if marker in (b"Xing", b"Info"):
                flags = struct.unpack(">I", data[xoff + 4:xoff + 8])[0]
                if flags & 0x1:
                    xing_frames = struct.unpack(">I", data[xoff + 8:xoff + 12])[0]
        frames += 1
        bitrates.append(bitrate)
        samples += spf
        pos += frame_len
        if frames > 400000:
            break

    if frames == 0:
        return _empty("MP3 帧解析失败")
    if xing_frames:
        samples = xing_frames * spf
        frames = xing_frames
    duration = samples / float(rate) if rate else None
    avg_bitrate = sum(bitrates) // len(bitrates) if bitrates else None
    uniq = set(bitrates)
    return {
        "format": "mp3", "codec": "mp3", "duration": duration, "sample_rate": rate,
        "channels": channels, "bitrate": avg_bitrate, "frames": frames,
        "vbr": len(uniq) > 1,
        "bitrate_min": min(uniq) if uniq else None,
        "bitrate_max": max(uniq) if uniq else None,
    }


def parse_wav(path):
    with wave.open(path, "rb") as wf:
        rate = wf.getframerate()
        frames = wf.getnframes()
        channels = wf.getnchannels()
        width = wf.getsampwidth()
        duration = frames / float(rate) if rate else None
    return {"format": "wav", "codec": "pcm_s%dle" % (width * 8), "duration": duration,
            "sample_rate": rate, "channels": channels,
            "bitrate": int(rate * channels * width * 8) if rate else None}


def parse_flac(path):
    data = common.read_bytes(path)
    pos = 4
    info = {"format": "flac", "codec": "flac", "duration": None, "sample_rate": None,
            "channels": None, "bitrate": None}
    while pos + 4 <= len(data):
        block = data[pos]
        last = block >> 7
        btype = block & 0x7F
        length = int.from_bytes(data[pos + 1:pos + 4], "big")
        body = data[pos + 4:pos + 4 + length]
        if btype == 0 and len(body) >= 34:
            bits = int.from_bytes(body[10:18], "big")
            rate = (bits >> 44) & 0xFFFFF
            channels = ((bits >> 41) & 0x7) + 1
            total = bits & 0xFFFFFFFFF
            info["sample_rate"] = rate
            info["channels"] = channels
            if rate:
                info["duration"] = total / float(rate)
                info["bitrate"] = int(os.path.getsize(path) * 8 / info["duration"]) if info["duration"] else None
            info["total_samples"] = total
        pos += 4 + length
        if last:
            break
    return info


def parse_ogg(path):
    size = os.path.getsize(path)
    with open(path, "rb") as fh:
        head = fh.read(65536)
        tail_start = max(0, size - 65536)
        fh.seek(tail_start)
        tail = fh.read()
    rate, channels, codec = None, None, "vorbis"
    if head[28:35] == b"\x01vorbis":
        channels = head[39]
        rate = struct.unpack("<I", head[40:44])[0]
    elif head[28:36] == b"OpusHead":
        codec = "opus"
        channels = head[37]
        rate = 48000
    idx = tail.rfind(b"OggS")
    granule = None
    if idx >= 0 and len(tail) >= idx + 14:
        granule = struct.unpack("<q", tail[idx + 6:idx + 14])[0]
    duration = granule / float(rate) if (granule is not None and rate) else None
    return {"format": "ogg", "codec": codec, "duration": duration, "sample_rate": rate,
            "channels": channels, "bitrate": int(size * 8 / duration) if duration else None}


def _mp4_boxes(data, start=0, end=None, depth=0, max_depth=6):
    """极简 ISO-BMFF 遍历，yield (path, type, payload_offset, payload_size)。"""
    if end is None:
        end = len(data)
    pos = start
    while pos + 8 <= end:
        size = struct.unpack(">I", data[pos:pos + 4])[0]
        btype = data[pos + 4:pos + 8]
        header = 8
        if size == 1:
            if pos + 16 > end:
                break
            size = struct.unpack(">Q", data[pos + 8:pos + 16])[0]
            header = 16
        elif size == 0:
            size = end - pos
        if size < header or pos + size > end:
            break
        yield btype, pos + header, size - header
        pos += size


def _mp4_find(data, path, start=0, end=None, depth=0):
    """按路径查找 box，返回 (payload_offset, payload_size) 或 None。"""
    if end is None:
        end = len(data)
    if not path:
        return None
    target = path[0]
    for btype, off, size in _mp4_boxes(data, start, end):
        if btype == target:
            if len(path) == 1:
                return (off, size)
            found = _mp4_find(data, path[1:], off, off + size, depth + 1)
            if found:
                return found
    return None


def parse_mp4(path):
    data = common.read_bytes(path)
    info = {"format": "m4a", "codec": None, "duration": None, "sample_rate": None,
            "channels": None, "bitrate": None}
    mvhd = _mp4_find(data, [b"moov", b"mvhd"])
    if mvhd:
        off, _ = mvhd
        version = data[off]
        if version == 0:
            timescale = struct.unpack(">I", data[off + 12:off + 16])[0]
            duration = struct.unpack(">I", data[off + 16:off + 20])[0]
        else:
            timescale = struct.unpack(">I", data[off + 20:off + 24])[0]
            duration = struct.unpack(">Q", data[off + 24:off + 32])[0]
        if timescale:
            info["duration"] = duration / float(timescale)
    mdhd = _mp4_find(data, [b"moov", b"trak", b"mdia", b"mdhd"])
    if mdhd:
        off, _ = mdhd
        version = data[off]
        if version == 0:
            timescale = struct.unpack(">I", data[off + 12:off + 16])[0]
            duration = struct.unpack(">I", data[off + 16:off + 20])[0]
        else:
            timescale = struct.unpack(">I", data[off + 20:off + 24])[0]
            duration = struct.unpack(">Q", data[off + 24:off + 32])[0]
        info["sample_rate"] = timescale or None
        if timescale and not info["duration"]:
            info["duration"] = duration / float(timescale)
    stsd = _mp4_find(data, [b"moov", b"trak", b"mdia", b"minf", b"stbl", b"stsd"])
    if stsd:
        off, size = stsd
        if size > 16:
            info["codec"] = data[off + 12:off + 16].decode("latin-1").strip()
            ch = struct.unpack(">H", data[off + 24:off + 26])[0] if size > 26 else None
            info["channels"] = ch
    if info["duration"]:
        info["bitrate"] = int(os.path.getsize(path) * 8 / info["duration"])
    return info


# ------------------------------------------------------- 内嵌歌词 / 标签
def read_metadata(path):
    """返回 {tags: {...}, embedded_lyrics: str|None, synced_lyrics: [...]|None, source: ...}"""
    out = {"tags": {}, "embedded_lyrics": None, "synced_lyrics": None, "source": None}
    head = common.read_bytes(path, 16)
    try:
        if head[:3] == b"ID3":
            out = _read_id3(path)
        elif head[:4] == b"fLaC":
            out = _read_vorbis_comment(path, "flac")
        elif head[:4] == b"OggS":
            out = _read_vorbis_comment(path, "ogg")
        elif head[4:8] == b"ftyp":
            out = _read_mp4_lyrics(path)
    except Exception as exc:
        out["error"] = "%s: %s" % (type(exc).__name__, exc)
    return out


def _decode_text(raw, enc_byte):
    if enc_byte == 0:
        return raw.decode("latin-1", "replace")
    if enc_byte == 1:
        return raw.decode("utf-16", "replace")
    if enc_byte == 2:
        return raw.decode("utf-16-be", "replace")
    return raw.decode("utf-8", "replace")


def _split_null(raw, enc_byte):
    if enc_byte in (1, 2):
        for i in range(0, len(raw) - 1, 2):
            if raw[i:i + 2] == b"\x00\x00":
                return raw[:i], raw[i + 2:]
        return raw, b""
    idx = raw.find(b"\x00")
    if idx < 0:
        return raw, b""
    return raw[:idx], raw[idx + 1:]


def _parse_id3v2(data):
    """只取常用文本帧，返回 {frame_id: text}。"""
    tags = {}
    if len(data) < 10:
        return tags
    version = data[3]
    pos = 10
    if data[5] & 0x40:  # extended header
        ext_size = struct.unpack(">I", data[10:14])[0] if version == 3 else 0
        pos += ext_size + (4 if version == 3 else 0)
    while pos + 10 <= len(data):
        fid = data[pos:pos + 4]
        if not re.match(rb"^[A-Z0-9]{4}$", fid):
            break
        if version >= 4:
            size = 0
            for b in data[pos + 4:pos + 8]:
                size = (size << 7) | (b & 0x7F)
        else:
            size = struct.unpack(">I", data[pos + 4:pos + 8])[0]
        body = data[pos + 10:pos + 10 + size]
        if not body:
            pos += 10 + size
            continue
        if fid in (b"TIT2", b"TPE1", b"TALB", b"TCON", b"TDRC", b"TYER"):
            enc = body[0]
            tags[fid.decode()] = _decode_text(body[1:], enc).strip("\x00")
        elif fid == b"USLT":
            enc = body[0]
            rest = body[4:]
            _, text = _split_null(rest, enc)
            tags["USLT"] = _decode_text(text, enc)
        elif fid == b"SYLT":
            tags["SYLT_raw"] = body
        pos += 10 + size
    return tags


def _parse_sylt(body):
    """SYLT → [{start, text}]。timestamp format 2 = 毫秒。"""
    enc = body[0]
    ts_format = body[4]
    rest = body[6:]
    _, rest = _split_null(rest, enc)
    out = []
    while rest:
        text_raw, rest = _split_null(rest, enc)
        if not text_raw or len(rest) < 4:
            break
        ts = struct.unpack(">I", rest[:4])[0]
        rest = rest[4:]
        text = _decode_text(text_raw, enc).strip()
        if not text:
            continue
        start = ts / 1000.0 if ts_format == 2 else ts * 0.026
        out.append({"start": round(start, 2), "text": text})
    return out


def _read_id3(path):
    data = common.read_bytes(path)
    tags = {}
    synced = None
    if data[:3] == b"ID3":
        tags = _parse_id3v2(data[:min(len(data), _id3v2_size(data[:10]))])
        if "SYLT_raw" in tags:
            try:
                synced = _parse_sylt(tags.pop("SYLT_raw"))
                if not synced:
                    synced = None
            except Exception:
                tags.pop("SYLT_raw", None)
    lyrics = tags.get("USLT")
    return {"tags": {k: v for k, v in tags.items() if k != "USLT"},
            "embedded_lyrics": lyrics, "synced_lyrics": synced, "source": "id3v2"}


def _read_vorbis_comment(path, kind):
    data = common.read_bytes(path)
    tags = {}
    lyrics = None
    start = data.find(b"\x03vorbis") if kind == "ogg" else 4
    if kind == "flac":
        pos = 4
        while pos + 4 <= len(data):
            block = data[pos]
            last = block >> 7
            btype = block & 0x7F
            length = int.from_bytes(data[pos + 1:pos + 4], "big")
            body = data[pos + 4:pos + 4 + length]
            if btype == 4:
                tags = _vorbis_pairs(body)
                break
            pos += 4 + length
            if last:
                break
    else:
        if start >= 0:
            body = data[start + 7:]
            tags = _vorbis_pairs(body)
    for key in ("LYRICS", "UNSYNCEDLYRICS", "UNSYNCHRONISED LYRICS", "LYRIC"):
        if tags.get(key):
            lyrics = tags[key]
            break
    return {"tags": {k: v for k, v in tags.items() if k not in
                     ("LYRICS", "UNSYNCEDLYRICS", "UNSYNCHRONISED LYRICS", "LYRIC")},
            "embedded_lyrics": lyrics, "synced_lyrics": None, "source": "vorbis-comment"}


def _vorbis_pairs(body):
    tags = {}
    try:
        pos = 4
        vendor_len = struct.unpack("<I", body[:4])[0]
        pos = 4 + vendor_len
        count = struct.unpack("<I", body[pos:pos + 4])[0]
        pos += 4
        for _ in range(count):
            length = struct.unpack("<I", body[pos:pos + 4])[0]
            pos += 4
            item = body[pos:pos + length].decode("utf-8", "replace")
            pos += length
            k, _, v = item.partition("=")
            tags[k.upper()] = v
    except Exception:
        pass
    return tags


def _read_mp4_lyrics(path):
    data = common.read_bytes(path)
    tags = {}
    lyrics = None
    for key, name in ((b"\xa9nam", "title"), (b"\xa9ART", "artist"), (b"\xa9alb", "album")):
        found = _mp4_find(data, [b"moov", b"udta", b"meta", b"ilst", key, b"data"])
        if found:
            off, size = found
            if size > 8:
                tags[name] = data[off + 8:off + size].decode("utf-8", "replace")
    found = _mp4_find(data, [b"moov", b"udta", b"meta", b"ilst", b"\xa9lyr", b"data"])
    if found:
        off, size = found
        if size > 8:
            lyrics = data[off + 8:off + size].decode("utf-8", "replace")
    return {"tags": tags, "embedded_lyrics": lyrics, "synced_lyrics": None, "source": "mp4-ilst"}


# --------------------------------------------------------------- 解码
def decode_to_wav(src, dst, rate=22050, channels=1):
    """把任意音频解成单声道 WAV。返回 (ok, tool, detail)。"""
    if src.lower().endswith(".wav"):
        try:
            info = parse_wav(src)
        except Exception:
            info = {}
        if info.get("sample_rate") == rate and info.get("channels") == channels:
            import shutil as _shutil
            if os.path.abspath(src) != os.path.abspath(dst):
                _shutil.copyfile(src, dst)
            return True, "source-wav", "源本身即单声道 %dHz WAV，直接使用" % rate
        # 需要重采样/混音时仍走外部工具
    if common.which("ffmpeg"):
        rc, out, err = common.run(["ffmpeg", "-v", "error", "-y", "-i", src,
                                   "-ac", str(channels), "-ar", str(rate),
                                   "-f", "wav", dst], timeout=900)
        if rc == 0 and os.path.isfile(dst) and os.path.getsize(dst) > 1024:
            return True, "ffmpeg", ""
    if common.which("afconvert"):
        rc, out, err = common.run(["afconvert", "-f", "WAVE", "-d",
                                   "LEI16@%d" % rate, "-c", str(channels), src, dst], timeout=900)
        if rc == 0 and os.path.isfile(dst) and os.path.getsize(dst) > 1024:
            return True, "afconvert", ""
        return False, "afconvert", (err or out or "").strip()[:400]
    if src.lower().endswith(".wav"):
        return True, "source-wav", "外部解码器缺失，直接读原始 WAV（可能非目标采样率）"
    return False, None, "ffmpeg 与 afconvert 都不可用，无法解码 %s" % os.path.basename(src)
