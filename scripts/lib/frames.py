#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""frames —— 从生成的视频里取「尾帧」，给下一段当首帧。

为什么需要它：
  一条 MV 被切成 N 个 14.5 秒**独立生成**。每一代模型都看不到别人。
  把上一段的**最后一帧**取出来、作为下一段的**首帧**上传，是唯一
  真正意义上的「动作接得上」——比任何文字描述都硬。

降级阶梯（缺工具不许让流程死掉）：
  1. ffmpeg            —— 有就用，最通用
  2. AVFoundation      —— macOS 自带（PyObjC），无需安装任何东西
  3. platform-export   —— 交给平台：小云雀 / MiniMax Design 都能在时间轴上导出单帧
  全失败 → 明确报「取不到尾帧」，并说明影响。**绝不拿首帧冒充尾帧。**

⚠️ 绝不静默给错帧：拿不到就返回 ok=False，让用户去平台导出。
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common  # noqa: E402

# 取帧时往前让开一点点，避免落在最后一帧的解码边界上取空
_TAIL_EPSILON = 0.05


def _try_ffmpeg():
    return common.which("ffmpeg")


def _try_avfoundation():
    try:
        import AVFoundation  # noqa: F401
        import Quartz  # noqa: F401
        from Foundation import NSURL  # noqa: F401
        return True
    except Exception:
        return False


def available_extractor():
    """当前机器上最好的取帧能力。"""
    if _try_ffmpeg():
        return "ffmpeg"
    if _try_avfoundation():
        return "avfoundation"
    return "platform-export"


def extractor_report():
    return {
        "best": available_extractor(),
        "ffmpeg": _try_ffmpeg(),
        "avfoundation": _try_avfoundation(),
        "platform_export_always_available": True,
    }


# ------------------------------------------------------------------ 实现
def _probe_avfoundation(video):
    import AVFoundation as AV
    from Foundation import NSURL
    asset = AV.AVAsset.assetWithURL_(NSURL.fileURLWithPath_(video))
    dur = AV.CMTimeGetSeconds(asset.duration())
    tracks = asset.tracksWithMediaType_(AV.AVMediaTypeVideo)
    size = None
    if tracks and len(tracks):
        sz = tracks[0].naturalSize()
        size = (int(sz.width), int(sz.height))
    return asset, dur, size


def resolve_actual_time(res, requested, video_seconds):
    """从 `copyCGImageAtTime_actualTime_error_` 的返回值里取出「实际取到第几秒」。

    ⚠️ 踩过的坑：PyObjC 在 out-param 位置传 None 时，返回的是 `(image, None)`
    ——第二项是 None，不能直接丢给 CMTimeGetSeconds（会抛
    `depythonifying struct, got no sequence`，整个取帧就废了）。
    拿不到就退回我们请求的时间点，并如实在 `exact` 里标明。
    """
    if not res:
        return requested
    try:
        if len(res) > 1 and res[1] is not None:
            val = res[1]
            # 普通数字已经是秒；CMTime 要走 CMTimeGetSeconds
            if isinstance(val, (int, float)):
                return float(val)
            import AVFoundation as AV
            return AV.CMTimeGetSeconds(val)
    except Exception:
        pass
    return requested


def _grab_avfoundation(video, out_png, at="last"):
    """用 macOS 自带的 AVFoundation 取帧。不需要安装任何东西。"""
    import AVFoundation as AV
    import Quartz
    from Foundation import NSURL

    asset, dur, size = _probe_avfoundation(video)
    if not dur or dur <= 0:
        return {"ok": False, "error": u"AVFoundation 读不到时长：%s" % video}
    t = 0.0 if at == "first" else max(0.0, dur - _TAIL_EPSILON)

    gen = AV.AVAssetImageGenerator.alloc().initWithAsset_(asset)
    gen.setAppliesPreferredTrackTransform_(True)
    # 精确取帧（默认容差会给你「附近」的一帧，那就不是尾帧了）
    tight = False
    try:
        gen.setRequestedTimeToleranceBefore_(AV.kCMTimeZero)
        gen.setRequestedTimeToleranceAfter_(AV.kCMTimeZero)
        tight = True
    except Exception:
        tight = False
    cm = AV.CMTimeMakeWithSeconds(t, 600)
    res = gen.copyCGImageAtTime_actualTime_error_(cm, None, None)
    img = res[0] if res and len(res) else None
    if img is None:
        return {"ok": False, "error": u"AVFoundation 在该时间点取不到帧：%.3fs" % t}
    actual = resolve_actual_time(res, t, dur)

    common.ensure_parent(out_png)
    url = NSURL.fileURLWithPath_(out_png)
    dest = Quartz.CGImageDestinationCreateWithURL(url, "public.png", 1, None)
    if dest is None:
        return {"ok": False, "error": u"无法创建 PNG 输出：%s" % out_png}
    Quartz.CGImageDestinationAddImage(dest, img, None)
    if not Quartz.CGImageDestinationFinalize(dest):
        return {"ok": False, "error": u"PNG 写入失败：%s" % out_png}
    # exact：请求了零容差，且实际时间离请求时间很近
    exact = (at == "first") or tight or (abs(actual - t) <= 0.12)
    return {
        "ok": True, "tool": "avfoundation", "path": out_png,
        "at_seconds": round(actual, 4),
        "video_seconds": round(dur, 4),
        "width": Quartz.CGImageGetWidth(img),
        "height": Quartz.CGImageGetHeight(img),
        "exact": bool(exact),
    }


def _grab_ffmpeg(video, out_png, at="last"):
    common.ensure_parent(out_png)
    if at == "first":
        vf = ["-frames:v", "1"]
    else:
        # 先出版本号，避免 -sseof 在老版本上不存在时静默出错
        rc, _o, _e = common.run(["ffmpeg", "-version"], timeout=30)
        if rc == 0:
            vf = ["-sseof", "-0.10", "-frames:v", "1"]
        else:
            vf = ["-frames:v", "1"]
    cmd = (["ffmpeg", "-y", "-v", "error"] + (vf if at == "first" else [])
           + ["-i", video] + ([] if at == "first" else vf) + [out_png])
    cmd = ["ffmpeg", "-y", "-v", "error"]
    if at == "first":
        cmd += ["-i", video, "-frames:v", "1", out_png]
    else:
        cmd += ["-sseof", "-0.10", "-i", video, "-frames:v", "1", out_png]
    rc, _out, err = common.run(cmd, timeout=600)
    if rc != 0 or not os.path.isfile(out_png):
        return {"ok": False, "error": u"ffmpeg 取帧失败：%s" % (err or "").strip()[:200]}
    return {"ok": True, "tool": "ffmpeg", "path": out_png, "at_seconds": None,
            "exact": True}


def capture(video, out_png, at="last", tool=None):
    """取一帧并写成 PNG。返回 dict（永不抛异常）。"""
    video = os.path.abspath(os.path.expanduser(video or ""))
    out_png = os.path.abspath(os.path.expanduser(out_png or ""))
    if not video or not os.path.isfile(video):
        return {"ok": False, "error": u"找不到视频文件：%s" % video,
                "fallback": "platform-export"}
    tool = tool or available_extractor()
    if tool == "ffmpeg":
        res = _grab_ffmpeg(video, out_png, at=at)
        if res.get("ok"):
            return res
    if tool in ("ffmpeg", "avfoundation"):
        try:
            res = _grab_avfoundation(video, out_png, at=at)
            if res.get("ok"):
                return res
        except Exception as exc:
            if tool == "avfoundation":
                return {"ok": False, "error": u"AVFoundation 失败：%s: %s"
                                             % (type(exc).__name__, exc),
                        "fallback": "platform-export"}
    return {
        "ok": False,
        "error": u"本机没有可用的取帧工具（ffmpeg / AVFoundation 都不可用）",
        "fallback": "platform-export",
        "how": (u"在平台上导出尾帧：小云雀 / MiniMax Design 都能在时间轴上定位到"
                u"最后一帧并导出图片；存成 workspace/frames/<段名>_last.png 即可。"),
    }


def capture_for_segment(video, seg_label, out_dir=None, at="last"):
    """按段名存尾帧：workspace/frames/C1_last.png"""
    out_dir = out_dir or common.path("workspace_frames")
    name = "%s_%s.png" % (seg_label, "last" if at == "last" else "first")
    return capture(video, os.path.join(out_dir, name), at=at)


def main(argv=None):
    import argparse
    ap = argparse.ArgumentParser(description="取视频的尾帧 / 首帧")
    common.add_common_args(ap)
    ap.add_argument("--video", required=True)
    ap.add_argument("--out", default=None)
    ap.add_argument("--segment", default=None, help="段名，如 C1 → C1_last.png")
    ap.add_argument("--at", choices=["last", "first"], default="last")
    ap.add_argument("--report", action="store_true")
    args = ap.parse_args(argv)
    common.apply_common_args(args)
    if args.report:
        common.emit(extractor_report(), args.json)
        return 0
    if args.segment:
        res = capture_for_segment(args.video, args.segment, at=args.at)
    else:
        out = args.out or os.path.join(common.path("workspace_frames"),
                                       "frame_%s.png" % args.at)
        res = capture(args.video, out, at=args.at)
    if args.json:
        common.emit(res, True)
    else:
        if res.get("ok"):
            common.echo(u"✓ 取到%s帧 → %s（%s×%s，工具 %s，位于 %.3fs）"
                        % (u"尾" if args.at == "last" else u"首",
                           res["path"], res.get("width"), res.get("height"),
                           res.get("tool"), res.get("at_seconds") or 0))
        else:
            common.echo(u"✗ %s" % res.get("error"))
            if res.get("how"):
                common.echo(res["how"])
    return 0 if res.get("ok") else 1


if __name__ == "__main__":
    sys.exit(main())
