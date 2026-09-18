#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""pack —— 打「上传交付包」，让这条 MV 在任何画布上都能跑。

架构现实（不绕）：本技能是**本地 agent 宿主**读的 skill，托管画布（MiniMax H3 官网 /
即梦 / 可灵 / 小云雀）读不到它，也不会替你切音频。所以交付包要把「用户只剩贴」这件事
做到位：

    00-材料清单.txt          缺哪个会卡住哪一步
    01-上传顺序与操作单.md    照着做
    02-画布智能体指令.txt     整段贴进平台的「自定义提示词 / Skill」字段
    segments/C01.wav …       切好的音频段（14.5s，切在小节线上）
    prompts/PROMPT-01.txt …  逐条提示词（H3 原生格式）
    prompts/全部提示词.txt    连着的一份
"""

import os
import shutil
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common  # noqa: E402
import chain as chain_mod  # noqa: E402
import h3render  # noqa: E402
import platforms as platforms_mod  # noqa: E402

PACK_DIRNAME = u"交付包"


def _copy_segments(seg_dir, dest):
    if not os.path.isdir(seg_dir):
        return []
    os.makedirs(dest, exist_ok=True)
    out = []
    for name in sorted(os.listdir(seg_dir)):
        if not name.lower().endswith((".wav", ".mp3", ".m4a", ".flac")):
            continue
        shutil.copyfile(os.path.join(seg_dir, name), os.path.join(dest, name))
        out.append(name)
    return out


def _material_list(plan, seg_files, cut_manifest=None):
    segs = plan.get("segments") or []
    meta = plan.get("meta") or {}
    lines = [u"本项目需要的材料（缺哪个会卡住哪一步）", ""]
    lines.append(u"必需：")
    lines.append(u"  1. 人物参考图 1 张 —— 没有它，%d 条提示词会各画各的" % len(segs))
    lines.append(u"  2. 音频 —— 没有它所有卡点都是猜的")
    lines.append(u"建议：")
    lines.append(u"  3. 三视图（人物转面表）—— 显著降低转身掉脸的概率")
    lines.append(u"  4. 人工核对过的歌词时间轴 —— 没有它，歌词↔画风呼应降级")
    lines.append(u"     ⚠️ 不要用 ASR 转写当定稿：实测把「王子」转成过「滑走」")
    lines.append("")
    lines.append(u"本次材料：")
    lines.append(u"  音频 %.2fs ｜ %s BPM ｜ 切成 %d 段 ｜ 每段音乐 %.1fs，"
                 u"提交给 MiniMax H3 的 duration 为整数秒"
                 % (meta.get("duration") or 0, meta.get("bpm") or u"未测出",
                    len(segs), meta.get("segment_target_seconds") or 14.5))
    lines.append(u"  已切好的音频段：%d 个%s"
                 % (len(seg_files), (u"（在 segments/ 目录）" if seg_files
                                     else u"（⚠️ 本机没有 ffmpeg/afconvert，"
                                          u"请照 01 操作单自己在 DAW 里切）")))
    if cut_manifest:
        lines.append(u"  切分清单：%s" % cut_manifest)
    lines.append("")
    lines.append(u"重要：MiniMax H3 的 duration 参数**只接受 4–15 的整数**。")
    lines.append(u"本技能按 14.5 秒切音乐，因此每一段都填 **15**——"
                 u"多出来的约 0.58 秒是留给你藏接缝的重叠量。")
    lines.append("")
    return "\n".join(lines) + "\n"


def _ops_sheet(plan, seg_files, route="ref"):
    segs = plan.get("segments") or []
    lines = [u"# 上传顺序与操作单", ""]
    lines.append(u"> 只要你的画布支持「上传素材 + 逐条提示词」就能用。")
    lines.append("")
    lines.append(u"## 第 1 步 · 先提交材料")
    lines.append("")
    lines.append(u"| 顺序 | 材料 | 说明 |")
    lines.append(u"|------|------|------|")
    lines.append(u"| 1 | 人物原始参考图 | **每一条都要重新上传**，编号为第 1 张 |")
    lines.append(u"| 2 | 三视图（人物转面表） | 没有就跳过；编号为第 2 张 |")
    lines.append(u"| 3 | 本段音频 | 编号为第 1 段音频 |")
    lines.append("")
    lines.append(u"## 第 2 步 · 把智能体指令贴进平台的「自定义提示词 / Skill」字段")
    lines.append("")
    lines.append(u"文件：`02-画布智能体指令.txt`（整段复制）")
    lines.append("")
    lines.append(u"## 第 3 步 · 逐条提交")
    lines.append("")
    lines.append(u"| 条 | 音频段 | 提示词 | 音乐时长 | 歌曲位置 | H3 duration | 起唱歌词 |")
    lines.append(u"|----|--------|--------|---------|---------|-------------|---------|")
    for i, s in enumerate(segs, 1):
        audio = seg_files[i - 1] if i - 1 < len(seg_files) else u"（自行切）"
        lyric = (s.get("lyrics") or [u"〔器乐〕"])[0]
        lines.append(u"| C%d | `segments/%s` | `prompts/PROMPT-%02d.txt` | %.3fs | "
                     u"%.3f–%.3fs | **%s** | %s |"
                     % (i, audio, i, s.get("audio_seconds") or 0,
                        s.get("time_start") or 0, s.get("time_end") or 0,
                        s.get("request_seconds"), lyric))
    lines.append("")
    lines.append(u"## 第 4 步 · 剪辑")
    lines.append("")
    lines.append(u"1. 按上表顺序拼接，**不要加淡入淡出**——接缝要严丝合缝；")
    lines.append(u"2. 每条生成的片子会比音乐长约 0.58 秒："
                 u"把画面裁到音乐长度，多出来的那一小段正好用来盖住接缝"
                 u"（在**最快的那一下动作**里切）；")
    lines.append(u"3. 配乐用**上传的原曲**，不要让模型生成配乐。")
    lines.append("")
    if any(s.get("is_tail_pad") for s in segs):
        lines.append(u"## 末段特别说明")
        lines.append("")
        for s in segs:
            if s.get("is_tail_pad"):
                advice = s.get("tail_advice")
                lines.append(u"- %s：音乐在 %.3fs 结束，但本条 prompt 覆盖 %s 秒。"
                             u"%.3f 秒之后**没有声音**：用 hold frame / 视觉衰减 / "
                             u"纸张质感 / 最后一张定格赛璐珞补足，"
                             u"**不要创造新音乐、不要加节拍**。"
                             % (s.get("label"), s.get("audio_seconds"),
                                s.get("request_seconds"),
                                s.get("audio_seconds")))
                if advice == "still_frame_in_edit":
                    lines.append(u"  - 💡 余下不足 2.5 秒：**建议干脆不交给视频模型**，"
                                 u"直接在剪辑里放一张静帧更快也更稳。")
        lines.append("")
    lines.append(u"## 接缝在哪藏（条与条之间）")
    lines.append("")
    lines.append(u"- 优先藏在**正在发生最快动作**的时刻：转身中途、跳跃最高点、"
                 u"画面被某个花纹或墨块盖满的那一帧。")
    lines.append(u"- 运动模糊与遮挡会替你盖住不连续。")
    lines.append("")
    return "\n".join(lines) + "\n"


def _canvas_instruction(plan, route="ref"):
    segs = plan.get("segments") or []
    meta = plan.get("meta") or {}
    canon = plan.get("character_canon") or {}
    ad = plan.get("art_direction") or {}
    total = meta.get("duration") or 0
    lines = []
    lines.append(u"【任务】把已上传的音频与人物参考图，做成一条 %.0f 秒的二维手绘"
                 u"风格化 MV，共 %d 段，每段对应一条提示词。" % (total, len(segs)))
    lines.append("")
    lines.append(u"【硬约束 · 人物】")
    lines.append(u"人物参考图是唯一的 Character Canon。全片只出现这一个角色，"
                 u"保持同一张脸、同一五官比例、同一发型发色、同一瞳色、同一年龄感、"
                 u"同一身体比例、同一服装结构、同一核心配饰。")
    lines.append(u"**不要**因为换画风或换场景而重新设计角色。变化发生在**世界**，"
                 u"不发生在**人物身份**。")
    lines.append(u"禁止：换脸 / 发色变化 / 五官漂移 / 年龄变化 / 服装重构 / "
                 u"写实化 / 3D 化 / 为了「丰富」而给她加新衣服首饰。")
    if canon.get("stable_identifiers"):
        lines.append(u"绝不可变的识别物：%s。"
                     % u"、".join(canon["stable_identifiers"]))
    lines.append("")
    lines.append(u"【硬约束 · 时长】")
    lines.append(u"MiniMax H3 的 duration **只接受 4–15 的整数**。每段音乐切在 "
                 u"%.1f 秒，所以 duration 一律填 **15**。多出来的约 0.58 秒"
                 u"是留给你藏接缝的。" % (meta.get("segment_target_seconds") or 14.5))
    lines.append("")
    lines.append(u"【硬约束 · 节奏】")
    if meta.get("bpm"):
        lines.append(u"音乐 %.2f BPM，4/4，1 拍 %.4fs，1 小节 %.4fs。"
                     % (meta["bpm"], meta.get("beat_sec") or 0, meta.get("bar_sec") or 0))
        lines.append(u"动作的重音必须落在拍上；小鼓点用线条跳动、局部抖动、错拍重影表现，"
                     u"**不要每个点都切镜头**。每段建议 2–4 个镜头。")
    else:
        lines.append(u"BPM 未测出：按每段 2–4 个镜头、动作落在可听的重音上。")
    lines.append("")
    lines.append(u"【硬约束 · 画风与歌词的呼应】")
    lines.append(u"画风路线：%s。逐段画风：%s。"
                 % (ad.get("route_name") or u"—",
                    u" → ".join(ad.get("movement_per_segment") or []) or u"—"))
    lines.append(u"画面**不做歌词图解**，而是让歌词里的**实物进到背景里**："
                 u"每一段背景都必须由这一段歌词里的物件构成。")
    lines.append(u"同时保持 2D 限制感：limited animation / 平面构图 / 手绘线条，"
                 u"不是实拍、不是 3D。")
    lines.append("")
    lines.append(u"【硬约束 · 运镜】")
    lines.append(u"只能用 MiniMax H3 官方运镜词：Static Shot / Push In / Pull Out / "
                 u"Zoom In / Zoom Out / Pan Left / Pan Right / Truck Left / Truck Right / "
                 u"Tilt Up / Tilt Down / Pedestal Up / Pedestal Down / Arc Shot / "
                 u"Tracking Shot / Roll Clockwise / Roll Counterclockwise / "
                 u"Shake Slightly / Shake Strongly / POV。")
    lines.append(u"每条运镜写全「类型 + 幅度 + 速度」，写成自然英文动作，"
                 u"**不要自造词**（graphic push-in / snap zoom / dolly / 3D orbit 都不认）。")
    lines.append(u"**静止镜头 + 强动作**优先于复杂摄影机运动。不要每个镜头都动。")
    lines.append("")
    lines.append(u"【硬约束 · 动画感】")
    lines.append(u"主动使用 limited animation：on twos / held frame / stepped motion / "
                 u"pose-to-pose / smear frame / 突然的姿势替换。"
                 u"**不要追求丝滑**——丝滑会变成「真人套了动漫滤镜」。")
    lines.append("")
    lines.append(u"【执行顺序】")
    lines.append(u"1. 上传人物参考图（+ 三视图）与**对应的那一段音频**；")
    lines.append(u"2. 把该段的提示词整段贴进提示词框；")
    lines.append(u"3. duration 填 15，逐条生成；")
    lines.append(u"4. 按 C1→C%d 顺序拼接，配乐用已上传的原曲。" % len(segs))
    lines.append("")
    lines.append(u"【不要做的事】")
    lines.append(u"- 不要让模型生成配乐（音轨是原曲，1:1 复用）；")
    lines.append(u"- 不要把不同条拼成一条（每条 ≤15s 是硬上限）；")
    lines.append(u"- 不要在粘贴区里加 Markdown、批注或中文说明。")
    lines.append("")
    return "\n".join(lines) + "\n"


def pack(plan, seg_dir=None, out_dir=None, route="mv", lang="zh",
         platform=None, cut_manifest=None, prompts_text=None):
    seg_dir = seg_dir or common.path("workspace_segments")
    out_dir = out_dir or os.path.join(common.path("output_latest"), PACK_DIRNAME)
    if os.path.isdir(out_dir):
        shutil.rmtree(out_dir)
    os.makedirs(out_dir, exist_ok=True)
    seg_files = _copy_segments(seg_dir, os.path.join(out_dir, "segments"))
    seg_files = [f for f in seg_files if f.lower().endswith(".wav")]
    seg_files.sort()

    prompts_dir = os.path.join(out_dir, "prompts")
    os.makedirs(prompts_dir, exist_ok=True)
    segs = plan.get("segments") or []
    all_parts = []
    for i, s in enumerate(segs, 1):
        text = h3render.render_segment(plan, s, route=route, lang=lang)
        common.write_text(os.path.join(prompts_dir, "PROMPT-%02d.txt" % i), text)
        all_parts.append(u"===== C%d ｜ 音乐 %.3f–%.3fs ｜ H3 duration %ss =====\n\n%s\n"
                         % (i, s.get("time_start") or 0, s.get("time_end") or 0,
                            s.get("request_seconds"), text))
    common.write_text(os.path.join(prompts_dir, u"全部提示词.txt"),
                      u"\n".join(all_parts))

    pid = platform or platforms_mod.default_platform()
    common.write_text(os.path.join(out_dir, "00-材料清单.txt"),
                      _material_list(plan, seg_files, cut_manifest))
    common.write_text(os.path.join(out_dir, "01-上传顺序与操作单.md"),
                      platforms_mod.ops_sheet(pid, plan, seg_files, route, lang))
    common.write_text(os.path.join(out_dir, "02-画布智能体指令.txt"),
                      platforms_mod.canvas_instruction(pid, plan, route, lang))
    common.write_text(os.path.join(out_dir, "04-尾帧续接链.md"),
                      chain_mod.render_md(plan))
    if prompts_text:
        common.write_text(os.path.join(out_dir, "03-完整提示词包.md"), prompts_text)

    return {"ok": True, "dir": out_dir, "segments": seg_files,
            "prompts": len(segs), "platform": pid,
            "files": sorted(os.listdir(out_dir))}


def main(argv=None):
    import argparse
    ap = argparse.ArgumentParser(description="打上传交付包")
    common.add_common_args(ap)
    ap.add_argument("--plan", default=None)
    ap.add_argument("--route", choices=["mv", "ref", "i2va", "t2va"], default="mv")
    ap.add_argument("--lang", choices=["en", "zh"], default="zh")
    ap.add_argument("--platform", default=None)
    ap.add_argument("--out", default=None)
    args = ap.parse_args(argv)
    common.apply_common_args(args)
    plan_path = args.plan or os.path.join(common.path("workspace_analysis"),
                                          "director_plan.json")
    plan = common.read_json(plan_path, {}) or {}
    if not (plan.get("segments") or []):
        common.echo(u"没有分段，先跑 scripts/prism.py segments")
        return 2
    res = pack(plan, out_dir=args.out, route=args.route, lang=args.lang,
               platform=getattr(args, "platform", None))
    if args.json:
        common.emit(res, True)
    else:
        common.echo(u"交付包 → %s" % res["dir"])
        for f in res["files"]:
            common.echo(u"  %s" % f)
        common.echo(u"  音频段 %d 个 ｜ 提示词 %d 条" % (len(res["segments"]), res["prompts"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
