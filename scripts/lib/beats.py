#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""beats —— 拍网格、小节吸附、14.5 秒分段。

这是整条管线的**时间地基**：卡点必须在写提示词之前就定死，不是先生成再卡。

三条立场（来自两份母技能融合后的结论）：

1. **14.5 秒是生成单元，不是语义单元。**
   一句歌词从 13s 唱到 18s，相邻两条 prompt 都必须表达同一意象。
2. **切点吸附到小节线**，不迁就整数秒。
   为了凑 14.5 整把切点从重拍上挪开，正好毁掉节奏同步。
3. **吸附不许突破 H3 的硬上限（15s）。**
   宁可不吸附，也不生成一条模型收不下的 prompt。

零第三方依赖，Python 3.9 可跑。
"""

import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common  # noqa: E402

DEFAULT_TARGET = 14.5
DEFAULT_HARD_MAX = 15.0
DEFAULT_TOLERANCE_BEATS = 1.5


def defaults():
    """(target_seconds, hard_max_seconds) —— 从 config 读，读不到用内置值。"""
    try:
        seg = common.config().get("segment", {})
        target = float(seg.get("target_seconds", DEFAULT_TARGET))
        hard_max = float(seg.get("hard_max_seconds", DEFAULT_HARD_MAX))
    except Exception:
        target, hard_max = DEFAULT_TARGET, DEFAULT_HARD_MAX
    if target > hard_max:
        target = hard_max
    return target, hard_max


def segments_for_duration(duration, target=None):
    """ceil(duration / target) —— H3 生成单元的条数。"""
    target = float(target or defaults()[0])
    if duration is None or duration <= 0:
        return 0
    return int(math.ceil(round(float(duration) / target, 9)))


# ------------------------------------------------------------------ 网格
def beat_grid(bpm, duration, phase=0.0, beats_per_bar=4, offset=0.0):
    """由 BPM 建拍网格。

    phase  —— 第一拍相对 0 的偏移（秒）
    offset —— 整条网格的平移（秒），用于人工微调
    """
    if not bpm or bpm <= 0:
        return None
    beat_sec = 60.0 / float(bpm)
    bar_sec = beat_sec * int(beats_per_bar)
    start = float(offset) + float(phase)
    beats = []
    i = 0
    while True:
        t = start + i * beat_sec
        if t > duration + 1e-9:
            break
        if t >= -1e-9:
            beats.append(round(t, 6))
        i += 1
    bars = []
    j = 0
    while True:
        t = start + j * bar_sec
        if t > duration + 1e-9:
            break
        if t >= -1e-9:
            bars.append(round(t, 6))
        j += 1
    return {
        "bpm": float(bpm),
        "beat_sec": beat_sec,
        "bar_sec": bar_sec,
        "beats_per_bar": int(beats_per_bar),
        "phase": start,
        "beats": beats,
        "bars": bars,
        "duration": duration,
    }


def _nearest(grid, t):
    """在网格的某个序列里找离 t 最近的元素，返回 (值, 索引, 差值秒)。"""
    seq = grid
    if not seq:
        return None, None, None
    best_i = min(range(len(seq)), key=lambda i: abs(seq[i] - t))
    return seq[best_i], best_i, seq[best_i] - t


def snap_time(t, grid, tolerance_beats=DEFAULT_TOLERANCE_BEATS,
              allow_beat_fallback=True):
    """把 t 吸附到最近的小节线 / 拍线。

    返回 dict：time / snapped_to('bar'|'beat'|'exact') / offset_beats / target
    容差不足时**原样返回**（宁可切在精确秒上，也不要切到听不见的地方）。
    """
    t = float(t)
    out = {"target": round(t, 6), "time": round(t, 6), "snapped_to": "exact",
           "offset_beats": 0.0}
    if not grid:
        return out
    beat_sec = grid.get("beat_sec") or 0
    if beat_sec <= 0:
        return out

    bar, _i, delta = _nearest(grid.get("bars") or [], t)
    if bar is not None and abs(delta) / beat_sec <= tolerance_beats + 1e-9:
        out.update({"time": round(bar, 6), "snapped_to": "bar",
                    "offset_beats": round(delta / beat_sec, 4)})
        return out

    if allow_beat_fallback:
        beat, _j, delta = _nearest(grid.get("beats") or [], t)
        if beat is not None and abs(delta) / beat_sec <= tolerance_beats + 1e-9:
            out.update({"time": round(beat, 6), "snapped_to": "beat",
                        "offset_beats": round(delta / beat_sec, 4)})
    return out


def _candidates(ideal, grid, tolerance_beats):
    """按「离理想切点由近到远」产出候选 (time, mode)。

    小节线优先于拍线：同样距离下先试小节。
    同时收集**邻近的**小节/拍，而不是只取最近的一个——最近那个被硬上限否掉时，
    下一个仍然能救回来。
    """
    seen = []
    if grid and grid.get("beat_sec"):
        beat_sec = grid["beat_sec"]
        # 小节线**整体优先**于拍线：同在小节/拍两级都够得着时，选小节线。
        # 这不是「谁更近选谁」——重拍才是音乐上干净的切点（规则 F3）。
        for key, mode in (("bars", "bar"), ("beats", "beat")):
            seq = grid.get(key) or []
            ranked = sorted(seq, key=lambda v: abs(v - ideal))
            for v in ranked:
                if abs(v - ideal) / beat_sec > tolerance_beats + 1e-9:
                    break
                if any(abs(v - s[0]) < 1e-6 for s in seen):
                    continue
                seen.append((v, mode))
    out = [(round(v, 6), mode) for v, mode in seen]
    out.append((round(float(ideal), 6), "exact"))
    return out


# ------------------------------------------------------------------ 分段
def segment_14_5(duration, grid=None, target=None, hard_max=None,
                 tolerance_beats=DEFAULT_TOLERANCE_BEATS, min_sec=None):
    """把 duration 按 target（默认 14.5s）切成分段，切点尽量落在小节线上。

    返回 [ {index,label,start,end,length,is_tail,target_time,snapped_to,
             offset_beats,bar_index,beat_index} ]
    """
    duration = float(duration)
    target, cfg_max = defaults()
    if target is None:
        target = DEFAULT_TARGET
    hard_max = float(hard_max or cfg_max)
    if min_sec is None:
        try:
            min_sec = float(common.config()["segment"].get("min_seconds", 0.0) or 0.0)
        except Exception:
            min_sec = 0.0

    n = segments_for_duration(duration, target)
    if n <= 0:
        return []
    if n == 1:
        return [_mk_segment(1, 0.0, duration, 0.0, "exact", 0.0, grid, True)]

    bounds = []
    prev = 0.0
    for k in range(1, n):
        ideal = k * target
        remaining = n - k
        chosen = None
        for cand, mode in _candidates(ideal, grid, tolerance_beats):
            if cand <= prev + 1e-6:
                continue
            if cand - prev > hard_max + 1e-9:
                continue
            if duration - cand > remaining * hard_max + 1e-9:
                continue
            chosen = (cand, mode)
            break
        if chosen is None:
            # 硬夹逼：先保证「本段不超上限」，再保证「后面还剩得下」
            cand = min(ideal, prev + hard_max)
            cand = max(cand, duration - remaining * hard_max)
            cand = min(cand, duration - remaining * 1e-3)
            if cand <= prev:
                cand = min(duration, prev + hard_max)
            chosen = (round(cand, 6), "clamped")
        bounds.append(chosen)
        prev = chosen[0]

    bounds.append((duration, "end"))
    out = []
    start = 0.0
    for i, (end, mode) in enumerate(bounds, 1):
        is_tail = (i == n)
        seg = _mk_segment(i, start, end, (i - 1) * target if i < n else (n - 1) * target,
                          mode, None, grid, is_tail)
        out.append(seg)
        start = end
    return out


def _mk_segment(index, start, end, target_time, mode, offset_beats, grid, is_tail):
    if offset_beats is None:
        beat_sec = (grid or {}).get("beat_sec") or 0
        offset_beats = round((end - target_time) / beat_sec, 4) if beat_sec else 0.0
    bar_index = beat_index = None
    if grid:
        bar_index = _index_of(grid.get("bars") or [], end)
        beat_index = _index_of(grid.get("beats") or [], end)
    seg = {
        "index": index,
        "label": "C%d" % index,
        "start": round(start, 6),
        "end": round(end, 6),
        "length": round(end - start, 6),
        "target_time": round(target_time, 6),
        "snapped_to": mode,
        "offset_beats": offset_beats,
        "bar_index": bar_index,
        "beat_index": beat_index,
        "is_tail": bool(is_tail),
    }
    # H3 时长契约：音乐切 14.5s，但提交给 H3 的 duration 必须是整数
    seg.update(duration_contract(seg["length"], is_tail=is_tail))
    return seg


def _index_of(seq, t, tol=1e-6):
    for i, v in enumerate(seq):
        if abs(v - t) <= tol:
            return i
    return None


# ------------------------------------------------------------------ H3 时长契约
# 官方 API（https://platform.minimax.io/docs/guides/video-generation）：
#   Output duration | 4–15 seconds, integer values only
# 所以「按 14.5 秒切音乐」和「填进 H3 的 duration」是两个不同的数：
#   音乐切在 14.5s（用户要求，也是音乐上干净的切点）
#   提交给 H3 的 duration 必须是整数 → 15（向上取整，绝不丢音乐）
# 多出来的 ~0.58s 不是浪费，它是**藏缝的重叠量**。
H3_MIN_SECONDS = 4
H3_MAX_SECONDS = 15
H3_FPS = 24

# 官方实测端点：duration=4 → 107 帧；duration=15 → 362 帧。
# 两点确定 帧数 = 17k + 5，其中 k = round(duration * fps / 17)。
# ⚠️ 这是从端点反推的模型，不是官方文档承诺的公式；用前用一次真机核对。
H3_FRAME_STRIDE = 17
H3_FRAME_OFFSET = 5


def request_seconds(audio_seconds):
    """把音乐段长换算成 H3 的 duration 参数。

    不能只做「向上取整」——因为帧网格（17k+5）会让某些整数秒**实出更短**：
    请求 6s 只吐 5.875s，请求 13s 只吐 12.958s。
    那样用户会**丢音乐**，而且到剪辑台上才发现。

    所以取「实出时长 ≥ 音乐长度」的**最小合法整数**。
    """
    if audio_seconds is None:
        return H3_MIN_SECONDS
    want = round(float(audio_seconds), 6)
    start = max(H3_MIN_SECONDS, min(H3_MAX_SECONDS, int(math.ceil(want - 1e-9))))
    for d in range(start, H3_MAX_SECONDS + 1):
        if delivered_seconds(d) >= want - 1e-9:
            return d
    return H3_MAX_SECONDS


def delivered_frames(duration_seconds):
    """H3 实际吐出的帧数（17k+5 网格）。"""
    d = int(duration_seconds)
    k = int(round(d * H3_FPS / float(H3_FRAME_STRIDE)))
    return H3_FRAME_STRIDE * k + H3_FRAME_OFFSET


def delivered_seconds(duration_seconds):
    """H3 实际吐出的时长（秒）。请求 15 → 362 帧 → 15.083s，不是 15.000s。"""
    return round(delivered_frames(duration_seconds) / float(H3_FPS), 4)


def duration_contract(audio_seconds, is_tail=False, tail_min_for_generation=2.5):
    """一段音乐 → 提交给 H3 的时长契约。"""
    audio_seconds = round(float(audio_seconds or 0.0), 6)
    req = request_seconds(audio_seconds)
    deliv = delivered_seconds(req)
    headroom = round(deliv - audio_seconds, 4)
    pad = bool(is_tail and deliv > audio_seconds + 1e-6)
    advice = "pad_with_hold" if audio_seconds >= tail_min_for_generation else "still_frame_in_edit"
    return {
        "audio_seconds": audio_seconds,
        "usable_seconds": audio_seconds,
        "request_seconds": req,
        "delivered_frames": delivered_frames(req),
        "delivered_seconds": deliv,
        "headroom_seconds": headroom,
        "is_tail_pad": pad,
        # 内部段：多出来的余量用来盖住接缝（在最快运动里切）
        "seam_overlap_seconds": round(headroom, 4) if not is_tail else 0.0,
        "tail_advice": advice if is_tail else None,
    }


def beat_at(grid, t):
    """t 落在第几拍（从 0 数）。无网格返回 None。"""
    if not grid or not grid.get("beat_sec"):
        return None
    return int(round((t - grid.get("phase", 0.0)) / grid["beat_sec"]))


def describe(segments, grid=None):
    """人读的切分说明。"""
    lines = []
    for s in segments:
        tag = {"bar": u"小节线", "beat": u"拍线", "exact": u"精确秒",
               "clamped": u"硬夹逼", "end": u"曲末"}.get(s["snapped_to"], s["snapped_to"])
        lines.append("%s  %7.3f–%7.3f  (%.3fs)  吸附=%s  偏移=%.2f拍"
                     % (s["label"], s["start"], s["end"], s["length"], tag,
                        s["offset_beats"] or 0.0))
    return "\n".join(lines)


def main(argv=None):
    import argparse
    ap = argparse.ArgumentParser(description="14.5 秒分段预览")
    common.add_common_args(ap)
    ap.add_argument("--duration", type=float, required=True)
    ap.add_argument("--bpm", type=float, default=None)
    ap.add_argument("--target", type=float, default=None)
    ap.add_argument("--tolerance-beats", type=float, default=DEFAULT_TOLERANCE_BEATS)
    args = ap.parse_args(argv)
    common.apply_common_args(args)
    grid = beat_grid(args.bpm, args.duration) if args.bpm else None
    segs = segment_14_5(args.duration, grid=grid, target=args.target,
                        tolerance_beats=args.tolerance_beats)
    if args.json:
        common.emit({"grid": grid, "segments": segs}, True)
    else:
        common.echo(describe(segs, grid))
    return 0


if __name__ == "__main__":
    sys.exit(main())
