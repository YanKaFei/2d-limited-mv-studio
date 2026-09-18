#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""platforms —— 平台适配：小云雀 / MiniMax Design / 通用。

两个平台各自的能力与坑写在这里，操作单（01-上传顺序与操作单.md）与
画布智能体指令（02-画布智能体指令.txt）按平台生成。

**信息来源与可信度**（不能凭记忆编）：
  * MiniMax Design：一篇完整动手实测（光子星球 / OFweek 转载，
    2026-08-24）。它明确写了三栏结构、Agent 会**先反问确认**、
    3D 导演台、AI 剪辑（自然语言指令：加字幕／加转场／**裁掉最后 2 秒**）、
    资产中心（人物锚 / 产品锚）。
  * 小云雀：检索到的公开信息提到 **智能分镜**、**3D 导演台**、**局部重改**、
    **角色库**、**首尾帧模式**。零散且会随版本变。
  * 因此：**具体按钮名称以你所用版本为准**，本文件描述的是「按功能找」的路径，
    不假装是官方说明书。

⚠️ 一条第三方现场经验的引用（**未经官方证实**）：
    首尾两帧之间**垂直位移超过画面高度 12%** 时容易肢体撕裂；
    解决办法是插入过渡姿势，而不是调参数。
    我们据此把「续接段不换姿势」写成硬规则 —— 这是保守的一侧，宁可不换姿势。
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common  # noqa: E402

PLATFORMS = {
    "xiaoyunque": {
        "id": "xiaoyunque",
        "name": u"小云雀",
        "cut_feature": u"智能分镜 / 时间轴切割",
        "cut_how": (u"在分镜面板里按时间轴把片子切成镜头段；"
                    u"也可以直接让它按你给的提示词逐段生成，"
                    u"再用**裁剪**把每条多出来的约 0.58 秒尾巴去掉。"),
        "first_last_frame": True,
        "first_last_how": (u"有**首尾帧模式**：上一段的尾帧直接当下一段的首帧上传，"
                           u"这是本技能尾帧续接链首选的做法。"),
        "agent_confirm": True,
        "agent_confirm_how": (u"它的 Agent 会先规划分镜再出片；"
                              u"每一段提交前先确认，别让它一口气跑完。"),
        "asset_lock": u"角色库 / 局部重改",
        "notes": [
            u"分镜容易被切得过碎（公开实测反馈），所以**每段镜头数控制在 2–4 个**，"
            u"不要让它自动细分。",
            u"局部重改适合改单帧或单段，不适合改人物身份——人物靠 Canon + 参考图锁。",
        ],
        "sources": [
            "https://www.youtube.com/watch?v=XAzC8Hly6kk",
            "https://zhuanlan.zhihu.com/p/2004523300588643639",
        ],
    },
    "minimax-design": {
        "id": "minimax-design",
        "name": u"MiniMax Design",
        "cut_feature": u"AI 剪辑（自然语言指令）",
        "cut_how": (u"直接用自然语言下剪辑指令——实测通过的三条是"
                    u"「加字幕」「加转场」「**裁掉最后 2 秒**」。"
                    u"所以本技能建议的「把每条多出来的约 0.58 秒裁掉」"
                    u"在这里就是一句话的事。"),
        "first_last_frame": True,
        "first_last_how": (u"把上一段尾帧作为本段的**首帧参考**上传；"
                           u"或在 3D 导演台里把姿势摆成上一帧的状态再生成。"),
        "agent_confirm": True,
        "agent_confirm_how": (u"它的 Agent **本来就是先反问确认**再动手的"
                              u"（实测原话：整个过程里我们能做的只有两件事，"
                              u"**确认**，以及等）。所以逐步骤确认跟它的工作方式天然合拍。"),
        "asset_lock": u"资产中心（人物锚 / 产品锚）",
        "notes": [
            u"画布上生成内容与上传素材会**自动按流程连线**——把每段的音频段、"
            u"尾帧、提示词放在同一条链上，不要散着扔。",
            u"可以把角色存成资产复用；下一次开新项目时人物一致性会好很多。",
            u"语义级视频编辑目前**不够准**（实测：调色几乎无变化、换背景时主体变形），"
            u"所以**不要靠事后改**，要在提示词阶段就写对。",
        ],
        "sources": [
            "https://cloud.ofweek.com/news/2026-08/ART-178802-8330-30699796.html",
        ],
    },
    "generic": {
        "id": "generic",
        "name": u"通用画布",
        "cut_feature": u"平台的裁剪 / 切割",
        "cut_how": (u"任何支持「上传素材 + 逐条提示词」的画布都能用："
                    u"逐条生成，再按时间轴裁剪拼接。"),
        "first_last_frame": True,
        "first_last_how": u"若平台支持首帧参考，把上一段尾帧作为首帧上传。",
        "agent_confirm": False,
        "agent_confirm_how": u"逐条提交即可，每一条都让用户先确认。",
        "asset_lock": u"—",
        "notes": [u"不同平台提示词格式不同，**不要混着粘**。"],
        "sources": [],
    },
}


def known():
    return sorted(PLATFORMS.keys())


def get(platform_id):
    return PLATFORMS.get(platform_id or "", PLATFORMS["generic"])


def default_platform():
    try:
        return common.config().get("platform", {}).get("default") or "xiaoyunque"
    except Exception:
        return "xiaoyunque"


def cut_feature(platform_id):
    return get(platform_id)["cut_feature"]


def _upload_rows(plan, seg):
    """这一段的实际上传顺序（与 chain.upload_order 一致）。"""
    import chain as chain_mod  # noqa: E402
    return chain_mod.upload_order(plan, seg)


def ops_sheet(platform_id, plan, seg_files=None, route="mv", lang="zh"):
    """按平台生成「上传顺序与操作单」。"""
    spec = get(platform_id)
    segs = (plan or {}).get("segments") or []
    meta = (plan or {}).get("meta") or {}
    seg_files = seg_files or []
    lines = [u"# 上传顺序与操作单 · %s" % spec["name"], ""]
    lines.append(u"> 平台：**%s** ｜ 切割功能：**%s**" % (spec["name"], spec["cut_feature"]))
    lines.append("")
    lines.append(u"## 这个平台怎么切")
    lines.append("")
    lines.append(u"%s" % spec["cut_how"])
    lines.append("")
    lines.append(u"## 第 1 步 · 先提交材料")
    lines.append("")
    lines.append(u"| 顺序 | 材料 | 说明 |")
    lines.append(u"|------|------|------|")
    lines.append(u"| 1 | 人物原始参考图 | **每一条都要重新上传** |")
    lines.append(u"| 2 | 三视图（人物转面表） | 没有就跳过 |")
    lines.append(u"| 3 | 本段音频（切好的段） | 原曲 1:1 复用 |")
    if spec["first_last_frame"]:
        lines.append(u"| 4 | **上一段的尾帧** | 从第 2 条起才有；作为本段**首帧**参考 |")
    lines.append("")
    lines.append(u"> %s" % spec["first_last_how"])
    lines.append("")
    lines.append(u"## 第 2 步 · 逐条提交（每条都先让用户确认）")
    lines.append("")
    lines.append(u"| 条 | 音频段 | 提示词 | 音乐时长 | 歌曲位置 | H3 duration | 延续上一帧 | 起唱歌词 |")
    lines.append(u"|----|--------|--------|---------|---------|-------------|-----------|---------|")
    for i, seg in enumerate(segs, 1):
        audio = seg_files[i - 1] if i - 1 < len(seg_files) else u"（自行切）"
        lyric = (seg.get("lyrics") or [u"〔器乐〕"])[0]
        ch = seg.get("chain")
        chain_cell = (u"← %s 尾帧" % ch.get("from_segment")) if ch else u"—（首段）"
        lines.append(u"| C%d | `segments/%s` | `prompts/PROMPT-%02d.txt` | %.3fs | "
                     u"%.3f–%.3fs | **%s** | %s | %s |"
                     % (i, audio, i, seg.get("audio_seconds") or 0,
                        seg.get("time_start") or 0, seg.get("time_end") or 0,
                        seg.get("request_seconds"), chain_cell, lyric))
    lines.append("")
    lines.append(u"## 第 3 步 · 每条出片后立刻做两件事")
    lines.append("")
    lines.append(u"1. **截尾帧**：`python3 scripts/prism.py lastframe --video <本段视频> "
                 u"--segment %s`" % ((segs[0].get("label") if segs else u"C1")))
    lines.append(u"   平台上也行：%s" % spec["cut_how"].split(u"。")[0] + u"。")
    lines.append(u"2. **让用户确认这一条**：`python3 scripts/prism.py confirm "
                 u"--step prompt-01` 与 `--step chain-01`")
    lines.append(u"   确认完再生成下一条——尾帧是下一条的首帧，顺序不能乱。")
    lines.append("")
    lines.append(u"## 第 4 步 · 拼接")
    lines.append("")
    lines.append(u"1. 按 C1→C%d 顺序拼接，**不要加淡入淡出**；" % len(segs))
    lines.append(u"2. 每条比音乐长约 0.58 秒：把画面裁到音乐长度，"
                 u"多出来的那一小段正好盖住接缝（在**最快的那一下动作**里切）；")
    lines.append(u"3. 配乐用**已上传的原曲**，不要让模型生成音乐。")
    lines.append("")
    if spec["agent_confirm"]:
        lines.append(u"## 平台特性提醒")
        lines.append("")
        lines.append(u"- **逐步骤确认**：%s" % spec["agent_confirm_how"])
        if spec.get("asset_lock") and spec["asset_lock"] != u"—":
            lines.append(u"- **人物锁定**：%s" % spec["asset_lock"])
        for n in spec.get("notes") or []:
            lines.append(u"- %s" % n)
        lines.append("")
    if spec.get("sources"):
        lines.append(u"## 信息来源")
        lines.append("")
        for u in spec["sources"]:
            lines.append(u"- %s" % u)
        lines.append("")
        lines.append(u"> 平台界面会变；上面是「按功能找」的路径，不是官方说明书。")
        lines.append("")
    return "\n".join(lines) + "\n"


def canvas_instruction(platform_id, plan, route="mv", lang="zh"):
    """贴进平台「自定义提示词 / Skill」字段的那一段。"""
    spec = get(platform_id)
    segs = (plan or {}).get("segments") or []
    meta = (plan or {}).get("meta") or {}
    canon = (plan or {}).get("character_canon") or {}
    ad = (plan or {}).get("art_direction") or {}
    out = []
    out.append(u"【平台】%s ｜ 切割功能：%s" % (spec["name"], spec["cut_feature"]))
    out.append(u"【任务】把已上传的原曲与人物参考图，做成一条 %.0f 秒的二维手绘风格化 MV，"
               u"共 %d 段，每段一条提示词。" % (meta.get("duration") or 0, len(segs)))
    out.append("")
    out.append(u"【硬约束 · 人物】")
    out.append(u"人物参考图是唯一的 Character Canon。全片只出现这一个角色，"
               u"保持同一张脸、同一五官比例、同一发型发色、同一瞳色、同一年龄感、"
               u"同一身体比例、同一服装结构、同一核心配饰。")
    out.append(u"**不要**因为换画风或换场景而重新设计角色。变化发生在**世界**，"
               u"不发生在**人物身份**。")
    if canon.get("stable_identifiers"):
        out.append(u"绝不可变的识别物：%s。" % u"、".join(canon["stable_identifiers"]))
    out.append("")
    out.append(u"【硬约束 · 尾帧续接】**这是本任务的关键**")
    out.append(u"第 1 条出片后，取它的**最后一帧**；第 2 条把这张图作为**首帧参考**上传，"
               u"并在【内容提示词】里写明「延续上一帧」。之后每条同理。")
    out.append(u"续接段**前 1.5 秒保持上一帧的画风与姿势**，只做同族连续动作"
               u"（不要换姿势：首尾帧垂直位移超过画面高度 12% 容易肢体撕裂），"
               u"**1.5 秒之后**才在段内转场到本段的新画风。")
    out.append("")
    out.append(u"【硬约束 · 时长】MiniMax H3 的 duration 只接受 4–15 的整数。"
               u"音乐切在 %.1f 秒，所以一律填 **15**；多出来的约 0.58 秒用来藏接缝。"
               % (meta.get("segment_target_seconds") or 14.5))
    out.append("")
    if meta.get("bpm"):
        out.append(u"【硬约束 · 节奏】%.2f BPM，1 拍 %.4fs，1 小节 %.4fs。"
                   u"动作重音落在拍上；每段 2–4 个镜头，不要每个点都切镜头。"
                   % (meta["bpm"], meta.get("beat_sec") or 0, meta.get("bar_sec") or 0))
        out.append("")
    out.append(u"【硬约束 · 画风与歌词】路线：%s。逐段画风：%s。"
               % (ad.get("route_name") or u"—",
                  u" → ".join(ad.get("movement_per_segment") or []) or u"—"))
    out.append(u"画面**不做歌词图解**，而是把歌词里的**实物放进背景**；"
               u"保持 2D 限制感（limited animation / 平面构图 / 手绘线条）。")
    out.append("")
    out.append(u"【硬约束 · 运镜】只用 MiniMax H3 官方运镜词，"
               u"写全「类型 + 幅度 + 速度」，不自造词；"
               u"静止镜头 + 强动作优先于复杂摄影机运动。")
    out.append("")
    out.append(u"【不要做的事】")
    out.append(u"- **不要生成音乐 / 配乐**：音轨是用户已上传的原曲，1:1 复用；")
    out.append(u"- 不要把不同条拼成一条（每条 ≤15s 是硬上限）；")
    out.append(u"- 不要在粘贴区里加 Markdown、批注或中文说明。")
    out.append("")
    out.append(u"【每一个步骤都要停下让用户确认】")
    for s, (title, what) in sorted(
            __import__("confirm").STEP_LABELS.items(), key=lambda kv: kv[0]):
        out.append(u"- %s：%s" % (title, what))
    out.append(u"确认用：`python3 scripts/prism.py confirm --step <步骤>`")
    out.append("")
    return "\n".join(out) + "\n"


def main(argv=None):
    import argparse
    ap = argparse.ArgumentParser(description="平台适配信息")
    common.add_common_args(ap)
    ap.add_argument("--platform", default=None)
    ap.add_argument("--ops", action="store_true")
    args = ap.parse_args(argv)
    common.apply_common_args(args)
    pid = args.platform or default_platform()
    if args.json:
        common.emit(get(pid), True)
    else:
        spec = get(pid)
        common.echo(u"%s（%s）" % (spec["name"], spec["id"]))
        common.echo(u"  切割功能：%s" % spec["cut_feature"])
        common.echo(u"  %s" % spec["cut_how"])
        common.echo(u"  首尾帧：%s" % spec["first_last_how"])
        if spec.get("notes"):
            common.echo(u"  注意：")
            for n in spec["notes"]:
                common.echo(u"    - %s" % n)
    return 0


if __name__ == "__main__":
    sys.exit(main())
