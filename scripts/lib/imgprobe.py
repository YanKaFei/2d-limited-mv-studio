#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""imgprobe —— 零依赖图片探测 + 主导色提取。

用途：Character Canon（规则 23）里那些**可以被测量**的字段：
  尺寸 / 画幅比 / 格式 / 主导色 / 明度基调 / 饱和度基调。

读图（看懂脸、发型、服装）是 Agent 的视觉能力；本模块只给客观数字，
并且遵循 AGENTS.md 的原则：**数字是信号，不是结论**。
"""

import os
import struct
import sys
import zlib

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common  # noqa: E402


def probe(path):
    path = os.path.abspath(path)
    if not os.path.isfile(path):
        return {"path": path, "error": "文件不存在"}
    size = os.path.getsize(path)
    head = common.read_bytes(path, 32)
    info = {"path": path, "bytes": size, "format": None, "width": None, "height": None,
            "aspect_ratio": None, "megapixels": None, "error": None}
    try:
        if head[:8] == b"\x89PNG\r\n\x1a\n":
            info["format"] = "png"
            w, h = struct.unpack(">II", head[16:24])
            info["width"], info["height"] = w, h
        elif head[:3] == b"\xff\xd8\xff":
            info["format"] = "jpeg"
            w, h = _jpeg_size(path)
            info["width"], info["height"] = w, h
        elif head[:4] == b"RIFF" and head[8:12] == b"WEBP":
            info["format"] = "webp"
            w, h = _webp_size(common.read_bytes(path, 4096))
            info["width"], info["height"] = w, h
        elif head[:6] in (b"GIF87a", b"GIF89a"):
            info["format"] = "gif"
            w, h = struct.unpack("<HH", head[6:10])
            info["width"], info["height"] = w, h
        elif head[:2] == b"BM":
            info["format"] = "bmp"
            w, h = struct.unpack("<ii", head[18:26])
            info["width"], info["height"] = abs(w), abs(h)
        else:
            info["error"] = "未知图片格式（魔数不匹配）"
    except Exception as exc:
        info["error"] = "%s: %s" % (type(exc).__name__, exc)
    if info["width"] and info["height"]:
        info["aspect_ratio"] = _ratio(info["width"], info["height"])
        info["megapixels"] = round(info["width"] * info["height"] / 1e6, 2)
        info["orientation"] = ("portrait" if info["height"] > info["width"] * 1.05
                               else "landscape" if info["width"] > info["height"] * 1.05
                               else "square")
    return info


def _ratio(w, h):
    from math import gcd
    g = gcd(int(w), int(h)) or 1
    rw, rh = int(w) // g, int(h) // g
    if rw > 40 or rh > 40:
        return "%.3f" % (float(w) / h)
    return "%d:%d" % (rw, rh)


def _jpeg_size(path):
    data = common.read_bytes(path)
    i = 2
    while i + 9 < len(data):
        if data[i] != 0xFF:
            i += 1
            continue
        marker = data[i + 1]
        if marker in (0xD8, 0x01) or 0xD0 <= marker <= 0xD7:
            i += 2
            continue
        if i + 4 > len(data):
            break
        seg_len = struct.unpack(">H", data[i + 2:i + 4])[0]
        if 0xC0 <= marker <= 0xCF and marker not in (0xC4, 0xC8, 0xCC):
            h, w = struct.unpack(">HH", data[i + 5:i + 9])
            return w, h
        i += 2 + seg_len
    return None, None


def _webp_size(data):
    if data[12:16] == b"VP8X":
        w = 1 + int.from_bytes(data[24:27], "little")
        h = 1 + int.from_bytes(data[27:30], "little")
        return w, h
    if data[12:16] == b"VP8 ":
        w = struct.unpack("<H", data[26:28])[0] & 0x3FFF
        h = struct.unpack("<H", data[28:30])[0] & 0x3FFF
        return w, h
    if data[12:16] == b"VP8L":
        bits = int.from_bytes(data[21:25], "little")
        return (bits & 0x3FFF) + 1, ((bits >> 14) & 0x3FFF) + 1
    return None, None


# ------------------------------------------------------------ 主导色
def _sips_thumbnail(path, out_png, max_px=256):
    if not common.which("sips"):
        return False
    rc, out, err = common.run(["sips", "-Z", str(max_px), "-s", "format", "png",
                               "--out", out_png, path], timeout=120)
    return rc == 0 and os.path.isfile(out_png) and os.path.getsize(out_png) > 0


def _decode_png(path, stride=1):
    """极简 PNG 解码（8bit，色彩类型 0/2/3/4/6）。返回 (w, h, pixels[RGB list])。"""
    data = common.read_bytes(path)
    if data[:8] != b"\x89PNG\r\n\x1a\n":
        raise ValueError("不是 PNG")
    pos = 8
    width = height = depth = ctype = None
    idat = bytearray()
    palette = []
    while pos + 8 <= len(data):
        length = struct.unpack(">I", data[pos:pos + 4])[0]
        tag = data[pos + 4:pos + 8]
        body = data[pos + 8:pos + 8 + length]
        if tag == b"IHDR":
            width, height, depth, ctype = struct.unpack(">IIBB", body[:10])
            if depth != 8:
                raise ValueError("仅支持 8bit PNG，当前 bit depth=%s" % depth)
        elif tag == b"PLTE":
            palette = [tuple(body[i:i + 3]) for i in range(0, len(body), 3)]
        elif tag == b"IDAT":
            idat += body
        elif tag == b"IEND":
            break
        pos += 12 + length
    channels = {0: 1, 2: 3, 3: 1, 4: 2, 6: 4}.get(ctype)
    if not channels or not width:
        raise ValueError("不支持的 PNG 色彩类型: %s" % ctype)
    raw = zlib.decompress(bytes(idat))
    bpp = channels
    stride_bytes = width * bpp
    prev = bytearray(stride_bytes)
    pixels = []
    off = 0
    for y in range(height):
        ftype = raw[off]
        off += 1
        line = bytearray(raw[off:off + stride_bytes])
        off += stride_bytes
        if ftype == 1:
            for i in range(bpp, stride_bytes):
                line[i] = (line[i] + line[i - bpp]) & 0xFF
        elif ftype == 2:
            for i in range(stride_bytes):
                line[i] = (line[i] + prev[i]) & 0xFF
        elif ftype == 3:
            for i in range(stride_bytes):
                left = line[i - bpp] if i >= bpp else 0
                line[i] = (line[i] + ((left + prev[i]) >> 1)) & 0xFF
        elif ftype == 4:
            for i in range(stride_bytes):
                a = line[i - bpp] if i >= bpp else 0
                b = prev[i]
                c = prev[i - bpp] if i >= bpp else 0
                p = a + b - c
                pa, pb, pc = abs(p - a), abs(p - b), abs(p - c)
                pr = a if (pa <= pb and pa <= pc) else (b if pb <= pc else c)
                line[i] = (line[i] + pr) & 0xFF
        prev = line
        if y % stride:
            continue
        for x in range(0, width, stride):
            i = x * bpp
            if ctype == 2:
                pixels.append((line[i], line[i + 1], line[i + 2]))
            elif ctype == 6:
                pixels.append((line[i], line[i + 1], line[i + 2]))
            elif ctype == 0:
                pixels.append((line[i], line[i], line[i]))
            elif ctype == 4:
                pixels.append((line[i], line[i], line[i]))
            elif ctype == 3:
                idx = line[i]
                if idx < len(palette):
                    pixels.append(palette[idx])
    return width, height, pixels


def dominant_colors(path, top=5, bins=16, max_px=256):
    """返回主导色列表 [{rgb, hex, share, lum}]。失败返回 []。"""
    tmp = None
    src = path
    try:
        if not os.path.abspath(path).lower().endswith(".png") or \
                _png_is_big(path, max_px):
            cand = os.path.join(common.path("workspace_temp"), "_imgprobe_thumb.png")
            if _sips_thumbnail(path, cand, max_px):
                tmp = cand
                src = cand
    except Exception:
        tmp = None
    try:
        w, h, pixels = _decode_png(src)
    except Exception:
        if tmp is None:
            return []
        return []
    if not pixels:
        return []
    counts = {}
    for (r, g, b) in pixels:
        key = (r >> 4 << 4, g >> 4 << 4, b >> 4 << 4)
        entry = counts.get(key)
        if entry is None:
            counts[key] = [1, r, g, b]
        else:
            entry[0] += 1
            entry[1] += r
            entry[2] += g
            entry[3] += b
    total = float(len(pixels))
    ordered = sorted(counts.values(), key=lambda e: -e[0])[:top]
    out = []
    for n, sr, sg, sb in ordered:
        r, g, b = int(sr / n), int(sg / n), int(sb / n)
        out.append({
            "rgb": [r, g, b],
            "hex": "#%02X%02X%02X" % (r, g, b),
            "share": round(n / total, 4),
            "lum": round((0.2126 * r + 0.7152 * g + 0.0722 * b) / 255.0, 3),
            "sat": round(_sat(r, g, b), 3),
        })
    return out


def _png_is_big(path, max_px):
    info = probe(path)
    if not info.get("width"):
        return True
    return max(info["width"], info["height"]) > max_px


def _sat(r, g, b):
    mx, mn = max(r, g, b), min(r, g, b)
    return 0.0 if mx == 0 else (mx - mn) / float(mx)


def tone_summary(path):
    """整体明度/饱和度基调（用于色彩叙事，规则 65）。"""
    colors = dominant_colors(path, top=6)
    if not colors:
        return {"available": False}
    total = sum(c["share"] for c in colors) or 1.0
    lum = sum(c["lum"] * c["share"] for c in colors) / total
    sat = sum(c["sat"] * c["share"] for c in colors) / total
    return {
        "available": True,
        "mean_luminance": round(lum, 3),
        "mean_saturation": round(sat, 3),
        "key": "high-key" if lum > 0.62 else ("low-key" if lum < 0.33 else "mid-key"),
        "chroma": "vivid" if sat > 0.45 else ("muted" if sat > 0.2 else "desaturated"),
    }
