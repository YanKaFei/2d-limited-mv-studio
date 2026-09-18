#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""fixtures.py —— 合成素材（零依赖：只用标准库造 WAV / PNG / 歌词）。

不下载、不联网、不依赖 PIL/numpy，这样测试在任何机器上都能跑。
"""

import math
import os
import struct
import wave
import zlib


# ------------------------------------------------------------------ 音频
def write_click_track(path, duration=20.0, bpm=120.0, sr=22050, tone=440.0,
                      click_ms=25.0, seed=7):
    """造一段「节拍轨」：每拍一个短促正弦 burst，其余静音。

    这样 onset envelope 上有清晰的周期性峰值，自相关测速能找到 bpm。
    """
    n = int(duration * sr)
    data = [0] * n
    beat_sec = 60.0 / bpm
    click_n = int(sr * click_ms / 1000.0)
    t = 0.0
    while t < duration:
        start = int(t * sr)
        for i in range(click_n):
            idx = start + i
            if idx >= n:
                break
            env = math.exp(-3.0 * i / float(click_n))
            data[idx] = int(20000 * env * math.sin(2 * math.pi * tone * i / sr))
        t += beat_sec
    # 轻微抖动，避免完全数字化的死寂
    for i in range(0, n, 997):
        data[i] = int(data[i] * 0.99)
    _write_wav(path, data, sr)
    return path


def write_tone_wav(path, duration=5.0, sr=22050, freq=220.0):
    n = int(duration * sr)
    data = [int(12000 * math.sin(2 * math.pi * freq * i / sr)) for i in range(n)]
    _write_wav(path, data, sr)
    return path


def _write_wav(path, samples, sr):
    d = os.path.dirname(os.path.abspath(path))
    if d and not os.path.isdir(d):
        os.makedirs(d, exist_ok=True)
    with wave.open(path, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        wf.writeframes(struct.pack("<%dh" % len(samples), *samples))
    return path


def wav_duration(path):
    with wave.open(path, "rb") as wf:
        return wf.getnframes() / float(wf.getframerate())


# ------------------------------------------------------------------ 图片
def write_png(path, w=64, h=96, rgb=(90, 140, 210)):
    """写一张纯色 PNG（手写 chunk，不依赖 PIL）。"""
    raw = b""
    row = bytes(bytearray(rgb)) * w
    for _ in range(h):
        raw += b"\x00" + row

    def chunk(tag, payload):
        body = tag + payload
        return (struct.pack(">I", len(payload)) + body
                + struct.pack(">I", zlib.crc32(body) & 0xFFFFFFFF))

    png = b"\x89PNG\r\n\x1a\n"
    png += chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0))
    png += chunk(b"IDAT", zlib.compress(raw, 9))
    png += chunk(b"IEND", b"")
    d = os.path.dirname(os.path.abspath(path))
    if d and not os.path.isdir(d):
        os.makedirs(d, exist_ok=True)
    with open(path, "wb") as fh:
        fh.write(png)
    return path


# ------------------------------------------------------------------ 歌词
LYRICS_TXT = u"""\
[00:00.00]（前奏）
[00:04.20]我把影子留在水面
[00:09.10]波纹一圈一圈散开
[00:14.30]夕阳把池塘染成蓝色
[00:19.40]它跳起舞来就像被王子附体了
[00:24.60]我数着荷叶上的光
[00:29.70]一圈两圈三圈不见了
[00:34.90]谁在岸边叫我的名字
[00:40.10]我假装听不见
[00:45.30]越过蓝色的夕阳
[00:50.40]我还在跳
"""


def write_lyrics(path, text=LYRICS_TXT):
    d = os.path.dirname(os.path.abspath(path))
    if d and not os.path.isdir(d):
        os.makedirs(d, exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(text)
    return path
