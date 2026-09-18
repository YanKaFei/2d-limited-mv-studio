#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""chain —— 把 N 个独立生成的段，串成一条接得上的片子。

核心机制：**上一段的最后一帧 = 下一段的第一帧。**
这是唯一真正硬的连续性证据——比任何文字描述都强，因为模型看到的是同一张图。

链条长这样：

    C1  ──尾帧──▶ C2  ──尾帧──▶ C3  ──尾帧──▶ C4

上传顺序随之变化（模型按**上传顺序**编号，不读路径）：

    C1        : [1] 人物参考图  [2] 三视图        [3] 音频段
    C2 及以后 : [1] 人物参考图  [2] 三视图  [3] 上一段尾帧  [4] 音频段

⚠️ 与「每段换画风」的关系（这是本技能最要紧的一处设计）：
    尾帧续接会把上一段的**画风**也带进来。如果下一段硬要换成另一种画风，
    两者会打架。正确做法不是二选一，而是——**让画风转换发生在段内**：
      前 1.5 秒延续上一帧（同画风、同姿势，动作连上），
      之后在段内转场到本段的新画风。
    这样「接得上」和「换画风」同时成立，而且转场本身成了视觉事件。

⚠️ 现场经验（第三方实测，**未经官方证实**，见 references/platform-playbook.md）：
    首尾两帧之间**垂直位移超过画面高度 12%** 时容易肢体撕裂。
    所以续接段**不要换姿势**——只做连续的同族动作。宁可不换姿势，也不要撕裂。
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common  # noqa: E402

DEFAULT_CONTINUE_SECONDS = 1.5


def _cfg():
    try:
        return common.config().get("chain", {}) or {}
    except Exception:
        return {}


def frame_path(seg_label, out_dir=None, at="last"):
    out_dir = out_dir or common.path("workspace_frames")
    return os.path.join(out_dir, "%s_%s.png" % (seg_label, at))


def build_chain(plan, out_dir=None, continue_seconds=None, enabled=None):
    """给每一段挂上 chain 信息。原地修改并返回 plan。

    第 1 段没有前帧；第 k 段接第 k-1 段的尾帧。
    """
    cfg = _cfg()
    if enabled is None:
        enabled = bool(cfg.get("enabled", True))
    if continue_seconds is None:
        continue_seconds = float(cfg.get("continue_seconds", DEFAULT_CONTINUE_SECONDS))
    segs = plan.get("segments") or []
    prev = None
    for seg in segs:
        label = seg.get("label") or ("C%s" % seg.get("id"))
        existing = seg.get("chain") or {}
        if not enabled or prev is None:
            seg["chain"] = None
            prev = label
            continue
        seg["chain"] = {
            "from_segment": prev,
            "frame": existing.get("frame") or frame_path(prev, out_dir),
            "label": existing.get("label") or "<Picture 3>",
            "declared": bool(existing.get("declared")),
            "describe": existing.get("describe") or "",
            "continue_seconds": existing.get("continue_seconds") or continue_seconds,
            "max_vertical_displacement_ratio": cfg.get(
                "max_vertical_displacement_ratio", 0.12),
        }
        prev = label
    plan["_chain_enabled"] = bool(enabled)
    return plan


def attach_frame(plan, seg_label, frame_path_, describe=None, declared=True):
    """把 `seg_label` 这一段的尾帧，挂到**它后面那一段**的首帧上。

    注意方向：尾帧是 `seg_label` 产出的，但它属于**下一段**的 chain
    （下一段才是这张图的消费者）。
    """
    segs = plan.get("segments") or []
    for i, seg in enumerate(segs):
        if (seg.get("label") or "") != seg_label:
            continue
        if i + 1 >= len(segs):
            return None                      # 末段没有后继，不需要尾帧
        nxt = segs[i + 1]
        ch = nxt.get("chain") or {
            "from_segment": seg_label, "label": "<Picture 3>",
            "continue_seconds": float(_cfg().get("continue_seconds",
                                                 DEFAULT_CONTINUE_SECONDS)),
        }
        ch["from_segment"] = seg_label
        ch["frame"] = frame_path_
        if describe:
            ch["describe"] = describe
        ch["declared"] = bool(declared)
        nxt["chain"] = ch
        return ch
    return None


def upload_order(plan, seg):
    """这一段的**上传顺序表**（顺序即编号）。"""
    rows = [(1, u"人物原始参考图", "character reference", "<Picture 1>")]
    turn = ((plan.get("assets") or {}).get("turnaround_sheet") or {}).get("path")
    nxt = 2
    if turn:
        rows.append((nxt, u"三视图（人物转面表）",
                     "character turnaround reference", "<Picture %d>" % nxt))
        nxt += 1
    ch = seg.get("chain") or {}
    if ch and ch.get("declared"):
        rows.append((nxt, u"上一段（%s）的尾帧" % ch.get("from_segment"),
                     "first_frame reference", ch.get("label") or "<Picture %d>" % nxt))
        nxt += 1
    rows.append((nxt, u"本段音频（切好的段）", "original song, reused 1:1",
                 "<Audio 1>"))
    return rows


def chain_label_for(seg):
    """这一段链上的是第几张图（<Picture N>）。"""
    return ((seg.get("chain") or {}).get("label")) or None


def validate_chain(plan):
    """链条的机器可判问题。返回 (problems, warnings)。"""
    problems, warnings = [], []
    segs = plan.get("segments") or []
    if not segs:
        return [u"没有分段"], []
    first = segs[0]
    if first.get("chain"):
        problems.append(u"第 1 段不该有前帧（它是最开头）")
    for i, seg in enumerate(segs[1:], 2):
        label = seg.get("label") or ("#%s" % seg.get("id"))
        ch = seg.get("chain")
        if not ch:
            warnings.append(u"%s 没有续接上一帧 —— 会与上一段断开" % label)
            continue
        if not ch.get("declared"):
            warnings.append(u"%s 的尾帧还没取（chain.declared=false）："
                            u"请用 mvstudio.py lastframe 取帧，或在平台上导出" % label)
        elif not ch.get("frame") or not os.path.isfile(ch.get("frame") or ""):
            problems.append(u"%s 声明了尾帧但文件不存在：%s"
                            % (label, ch.get("frame")))
        if not str(ch.get("describe") or "").strip():
            warnings.append(u"%s 的 chain.describe 为空 —— "
                            u"【内容提示词】里写不出「延续上一帧」到底延续什么" % label)
        if not str(seg.get("chain_continuity") or "").strip():
            warnings.append(u"%s 缺 chain_continuity（起手怎么接上一帧的姿势）" % label)
    return problems, warnings


def render_md(plan):
    segs = plan.get("segments") or []
    lines = [u"# 尾帧续接链", ""]
    lines.append(u"> 上一段的**最后一帧**作为下一段的**首帧**。"
                 u"这是唯一真正硬的连续性证据——模型看到的是同一张图。")
    lines.append("")
    lines.append(u"| 段 | 接哪一段 | 尾帧文件 | 已取帧 | 前 %.1fs 延续 |"
                 % float(_cfg().get("continue_seconds", DEFAULT_CONTINUE_SECONDS)))
    lines.append(u"|----|---------|---------|--------|--------------|")
    for seg in segs:
        ch = seg.get("chain")
        label = seg.get("label") or ("#%s" % seg.get("id"))
        if not ch:
            lines.append(u"| %s | —（第一段） | — | — | — |" % label)
        else:
            lines.append(u"| %s | %s | `%s` | %s | %s |"
                         % (label, ch.get("from_segment"),
                            os.path.basename(ch.get("frame") or ""),
                            u"✅" if ch.get("declared") else u"❌ 待取",
                            ch.get("describe") or u"**待填**"))
    lines.append("")
    lines.append(u"## 每段的上传顺序")
    lines.append("")
    for seg in segs:
        label = seg.get("label") or ("#%s" % seg.get("id"))
        lines.append(u"**%s**" % label)
        lines.append("")
        lines.append(u"| 顺序 | 素材 | 职责声明 | 编号 |")
        lines.append(u"|------|------|----------|------|")
        for n, name, role, tag in upload_order(plan, seg):
            lines.append(u"| %d | %s | %s | `%s` |" % (n, name, role, tag))
        lines.append("")
    lines.append(u"## 取帧怎么做")
    lines.append("")
    lines.append(u"```bash")
    lines.append(u"python3 scripts/mvstudio.py lastframe --video out/C1.mp4 --segment C1")
    lines.append(u"# 或者：python3 scripts/mvstudio.py lastframe --scan out/   # 扫整个目录")
    lines.append(u"```")
    lines.append("")
    lines.append(u"平台上也行：小云雀 / MiniMax Design 都能在时间轴上定位到最后一帧"
                 u"导出图片，存成 `workspace/frames/C1_last.png` 即可。")
    lines.append("")
    lines.append(u"## ⚠️ 两条必须遵守的约束")
    lines.append("")
    lines.append(u"1. **画面风格转换放在段内**：前 %.1f 秒延续上一帧（同画风、同姿势），"
                 u"之后在段内转场到本段新画风。不要一上来就换风格——那会跟首帧打架。"
                 % float(_cfg().get("continue_seconds", DEFAULT_CONTINUE_SECONDS)))
    lines.append(u"2. **续接段不要换姿势**：第三方实测，首尾帧之间垂直位移超过画面高度 "
                 u"%.0f%% 时容易肢体撕裂。只做连续的同族动作。"
                 % (float(_cfg().get("max_vertical_displacement_ratio", 0.12)) * 100))
    lines.append("")
    return "\n".join(lines) + "\n"


def main(argv=None):
    import argparse
    ap = argparse.ArgumentParser(description="构建尾帧续接链")
    common.add_common_args(ap)
    ap.add_argument("--plan", default=None)
    ap.add_argument("--md", action="store_true")
    ap.add_argument("--off", action="store_true", help="关闭尾帧续接")
    args = ap.parse_args(argv)
    common.apply_common_args(args)
    path = args.plan or os.path.join(common.path("workspace_analysis"),
                                     "director_plan.json")
    plan = common.read_json(path, {}) or {}
    if not plan.get("segments"):
        common.echo(u"没有分段：先跑 scripts/mvstudio.py segments")
        return 3
    build_chain(plan, enabled=not args.off)
    common.write_json(path, plan)
    md = render_md(plan)
    common.write_text(os.path.join(common.path("output_latest"), "chain.md"), md)
    if args.json:
        common.emit({"chain": [s.get("chain") for s in plan["segments"]],
                     "md": os.path.join(common.path("output_latest"), "chain.md")}, True)
    elif args.md:
        common.echo(md)
    else:
        for seg in plan["segments"]:
            ch = seg.get("chain")
            common.echo(u"  %s → %s" % (seg.get("label"),
                                        (u"接 %s" % ch["from_segment"]) if ch else u"（首段）"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
