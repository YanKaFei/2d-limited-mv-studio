#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""endings —— 全片怎么结束（给用户挑，不是默认站定）。

为什么需要这个：
  「最后定格站好」是最偷懒、也最容易让整条片子泄气的收尾。
  一支 MV 的最后一个动作，决定了观众记住的是什么。

所以这里给的是**一组可直接写进【内容提示词】的收尾效果**，
每一条都写明「镜头看得见什么」，而不是「要很酷」。

八种收尾（覆盖三种音乐收束性格）：

  跳跃类   jump_freeze          跃起定格 → 一张海报
  接触类   reach_and_crack      伸手触屏 → 画面裂开
           swipe_to_black        手一滑 → 卡点切黑
  消失类   frame_drop_vanish    逐帧抽掉身体 → 只剩轮廓 → 没有
           misregistration_exit  像印版一样「退印」：掉色 → 掉线 → 只剩套印标记
           spin_to_line          旋转中简化成一根线 → 被擦掉
  材质类   paper_tear_exit      画面从中撕开 → 跟着纸的裂口走出去
           look_back_fade        回头看镜头 → 定格成一张褪色照片

⚠️ 这些效果都必须**不改变人物身份**：不允许融化、变粒子、换脸、换服装。
   消失的是「画」，不是「人」。
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common  # noqa: E402

CATALOG = [
    {
        "id": "jump_freeze",
        "name_zh": u"跃起定格",
        "name_en": "Jump & Freeze",
        "what_zh": u"跳到最高点定格，整屏变成一张海报。",
        "what_en": "Freeze at the apex of a jump; the whole frame becomes a poster.",
        "prompt_zh": (
            u"收尾：音乐最后一拍，她全力向上跳起；在最高点整幅画面定格，"
            u"人物的赛璐璐停止不动，背景在定格的同时被抽掉，只剩一圈错位的套色轮廓；"
            u"定格保持到结束。"),
        "prompt_en": (
            "Ending: on the final beat she jumps straight up with full effort; at the apex "
            "the entire frame freezes, her cel stops moving, the background is pulled away "
            "in the same frame, leaving only one offset misregistered contour ring; the "
            "freeze holds to the last frame."),
        "best_for": [u"hard stop", u"sustained"],
        "needs": u"前一段已经积累起足够大的动作幅度",
        "beat_hint": u"起跳落在最后一拍的前半拍上，定格正好压在重拍",
    },
    {
        "id": "reach_and_crack",
        "name_zh": u"伸手裂屏",
        "name_en": "Reach & Crack",
        "what_zh": u"她伸手向镜头，指尖触到画面的一瞬间，整幅画像玻璃一样裂开。",
        "what_en": "She reaches toward the lens; the instant her fingertip touches the frame, "
                   "the whole image cracks like glass.",
        "prompt_zh": (
            u"收尾：她向画面（镜头）方向伸手，指尖往前推；指尖接触到画面的一瞬间，"
            u"整幅画从触点开始像玻璃一样裂开，裂缝是硬边的深色线，"
            u"裂缝里透出下一层的纯白；裂纹在最后一拍铺满全屏后停住。"),
        "prompt_en": (
            "Ending: she reaches toward the lens and pushes her fingertip forward; the "
            "instant it touches the frame the whole image cracks outward from that point "
            "like glass, the cracks are hard-edged dark lines, and pure white shows through "
            "from the layer behind; the cracks finish spreading across the full frame on the "
            "final beat and stop."),
        "best_for": [u"hard stop"],
        "needs": u"画面必须是一个**平面**（正片叠底的世界），否则裂的是空间不是画",
        "beat_hint": u"触点压在最后一拍，裂纹铺满压在尾音上",
    },
    {
        "id": "swipe_to_black",
        "name_zh": u"手一滑黑屏卡点",
        "name_en": "Swipe to Black on the Beat",
        "what_zh": u"手横向划过画面，跟着重拍整屏切黑，只留下一道轨迹残影。",
        "what_en": "Her hand swipes across the frame; the whole screen cuts to black on the "
                   "downbeat, leaving one motion-trail afterimage.",
        "prompt_zh": (
            u"收尾：她的手臂横向划过画面挡住镜头，在最后一拍重拍上整屏切黑；"
            u"黑屏之后只留一道她手臂的轨迹残影停留几帧，然后也消失。"
            u"全片在这一拍结束，不要淡出。"),
        "prompt_en": (
            "Ending: her arm sweeps horizontally across the frame and covers the lens; on the "
            "final downbeat the whole screen cuts to black. After the black, one motion-trail "
            "afterimage of her arm lingers for a few frames and then disappears. The film "
            "ends on that beat; do not fade out."),
        "best_for": [u"hard stop"],
        "needs": u"手臂动作足够快，能在两帧内盖满画幅",
        "beat_hint": u"切黑必须精确压在重拍上，早一帧都泄气",
    },
    {
        "id": "frame_drop_vanish",
        "name_zh": u"逐帧抽掉",
        "name_en": "Frame-Drop Vanish",
        "what_zh": u"一帧一帧把她抽掉：先丢手臂，再丢躯干，最后只剩轮廓。",
        "what_en": "She is removed frame by frame: first the arms, then the torso, until only "
                   "an outline is left.",
        "prompt_zh": (
            u"收尾：她继续跳舞，但身体被一帧一帧地抽掉——先是手臂消失，"
            u"再是躯干消失，动作还在继续（衣服与头发跟着动），最后只剩一圈轮廓线；"
            u"轮廓线在最后一拍也停下。"),
        "prompt_en": (
            "Ending: she keeps dancing while her body is removed frame by frame - first the "
            "arms are gone, then the torso, while the motion continues (the clothes and hair "
            "still move), until only one contour line remains; the contour also stops on the "
            "final beat."),
        "best_for": [u"fade/decay", u"hard stop"],
        "needs": u"人物在这段里动作不要太大，否则会看成崩坏",
        "beat_hint": u"每抽掉一层压在相邻的重拍上",
    },
    {
        "id": "misregistration_exit",
        "name_zh": u"印版退位",
        "name_en": "Misregistration Exit",
        "what_zh": u"像印版一样一层层退印：掉色 → 掉线 → 只剩套印标记。",
        "what_en": "She de-prints like a press plate: first the colour drops, then the line, "
                   "until only registration marks remain.",
        "prompt_zh": (
            u"收尾：她像一块印刷印版一样分层退印——先掉色（只剩黑白线稿），"
            u"再掉线（只剩色块），最后整幅画只剩下四角的套印标记与几条参考线；"
            u"她在最后一拍完全退出画面，标记留在原地。"),
        "prompt_en": (
            "Ending: she de-prints in layers like a press plate - first the colour drops "
            "(leaving only a black-and-white line drawing), then the line drops (leaving only "
            "flat colour blocks), until only the registration marks in the four corners and a "
            "few guide lines remain; she exits the frame completely on the final beat and the "
            "marks stay."),
        "best_for": [u"fade/decay"],
        "needs": u"整条片子最好本来就是印刷/错版语汇（print-decay 路线）",
        "beat_hint": u"每一层退印压在相邻的重拍上",
    },
    {
        "id": "spin_to_line",
        "name_zh": u"旋转成线",
        "name_en": "Spin to a Line",
        "what_zh": u"旋转过程中身体逐渐简化成一根线，最后线被擦掉。",
        "what_en": "While spinning, her body simplifies into a single line; the line is then "
                   "erased.",
        "prompt_zh": (
            u"收尾：她原地旋转，旋到第二圈时身体开始简化——先是五官收成符号，"
            u"再是身体收成一根竖直的黑线；线在最后一拍停住，"
            u"然后像被橡皮擦一样从下往上被擦掉，留下纸底。"),
        "prompt_en": (
            "Ending: she spins on the spot; on the second rotation her body begins to "
            "simplify - first the features collapse into symbols, then the whole body "
            "collapses into one vertical black line; the line stops on the final beat and is "
            "then erased from the bottom upward like a rubber eraser, leaving bare paper."),
        "best_for": [u"fade/decay"],
        "needs": u"适合线描/水墨语汇；不适合超扁平硬边路线",
        "beat_hint": u"收成线的那一下压在重拍，擦除压在尾音",
    },
    {
        "id": "paper_tear_exit",
        "name_zh": u"纸撕离场",
        "name_en": "Paper Tear Exit",
        "what_zh": u"画面从中撕开，她跟着纸的裂口一起走出去。",
        "what_en": "The frame tears open down the middle; she walks out through the rip.",
        "prompt_zh": (
            u"收尾：画面像一张纸一样从中间被撕开，撕裂的边缘是毛边的白纸纤维；"
            u"她一边跳一边从裂口走进纸的后面，最后裂口合上，画面只剩那张被撕过的纸背。"),
        "prompt_en": (
            "Ending: the frame tears open down the middle like a sheet of paper, the torn edge "
            "showing fuzzy white paper fibre; she dances through the rip and disappears behind "
            "the paper, and the tear closes, leaving only the torn paper backing."),
        "best_for": [u"fade/decay", u"sustained"],
        "needs": u"适合纸与剪/拼贴语汇（paper-world 路线）",
        "beat_hint": u"撕裂起身压在重拍，合上压在最后一拍",
    },
    {
        "id": "look_back_fade",
        "name_zh": u"回望褪色",
        "name_en": "Look Back, Fade",
        "what_zh": u"她停住回头看一眼镜头，画面定格成一张褪色照片。",
        "what_en": "She stops and looks back at the lens; the frame freezes into a faded "
                   "photograph.",
        "prompt_zh": (
            u"收尾：她停住（全片唯一一次完全停止），回头看向镜头；"
            u"在最后一拍整幅画面褪色成一张旧照片——饱和度抽干、"
            u"四边出现轻微的曝光吃边，然后保持不动到结束。"),
        "prompt_en": (
            "Ending: she stops - the only complete stop in the whole film - and looks back at "
            "the lens; on the final beat the whole frame fades into an old photograph, the "
            "saturation draining out and the four edges slightly burned away by exposure, then "
            "holds still to the end."),
        "best_for": [u"fade/decay", u"sustained"],
        "needs": u"人物与镜头之间要已经建立过「被观看」的关系，否则回望没有重量",
        "beat_hint": u"停住压在最后一拍前一拍，褪色压在最后一拍",
    },
]

_BY_ID = dict((e["id"], e) for e in CATALOG)


def catalog():
    return [dict(e) for e in CATALOG]


def ids():
    return [e["id"] for e in CATALOG]


def get(ending_id):
    if ending_id not in _BY_ID:
        raise KeyError(ending_id)
    return dict(_BY_ID[ending_id])


def _ending_character(analysis):
    st = (analysis or {}).get("structure") or {}
    return (st.get("ending_character") or "").lower()


def _density(analysis):
    return float((analysis or {}).get("rhythmic_density") or 0)


def build_menu(analysis, plan=None):
    """按音乐的收束性格给收尾效果排序。返回带 `why` 的列表。"""
    char = _ending_character(analysis)
    dens = _density(analysis)
    last_energy = None
    segs = (plan or {}).get("segments") or []
    if segs:
        last_energy = segs[-1].get("energy")

    out = []
    for e in CATALOG:
        score = 0
        why = []
        for key, weight in ((u"hard stop", 3), (u"fade/decay", 2), (u"sustained", 2)):
            if key in char and key in e["best_for"]:
                score += weight
                why.append(u"音乐的收束是「%s」" % key)
        if dens >= 2.0 and e["id"] in ("swipe_to_black", "frame_drop_vanish",
                                       "reach_and_crack"):
            score += 2
            why.append(u"起音密度 %.2f/s，切点型收尾接得住" % dens)
        if dens and dens < 1.2 and e["id"] in ("look_back_fade", "misregistration_exit",
                                              "spin_to_line", "paper_tear_exit"):
            score += 2
            why.append(u"起音密度 %.2f/s 偏低，渐变型收尾更合" % dens)
        if last_energy == "peak" and e["id"] in ("jump_freeze", "reach_and_crack",
                                                 "swipe_to_black"):
            score += 1
            why.append(u"末段是能量峰值，适合给一个「炸点」")
        if last_energy == "quiet" and e["id"] in ("look_back_fade", "misregistration_exit"):
            score += 1
            why.append(u"末段是低谷，适合收得安静")
        item = dict(e)
        item["score"] = score
        item["why"] = u"；".join(why) if why else u"通用选择，任何收束都成立"
        out.append(item)
    out.sort(key=lambda x: (-x["score"], x["id"]))
    for i, e in enumerate(out, 1):
        e["rank"] = i
    return out


def apply_ending(plan, ending_id):
    """把选定的收尾效果写进导演稿。幂等。"""
    e = get(ending_id)          # 未知名会 KeyError，交给调用方处理
    plan = plan or {}
    plan["ending"] = {
        "id": e["id"], "name_zh": e["name_zh"], "name_en": e["name_en"],
        "prompt_zh": e["prompt_zh"], "prompt_en": e["prompt_en"],
    }
    return plan


def ending_block(plan, lang="zh"):
    """渲染器要插进**末段内容提示词**的收尾块。没选就返回空串。"""
    e = (plan or {}).get("ending") or {}
    if not e:
        return ""
    if lang == "zh":
        body = e.get("prompt_zh") or ""
        return (body if body.startswith(u"收尾") else u"收尾：" + body)
    body = e.get("prompt_en") or ""
    return body if body.lower().startswith("ending") else "Ending: " + body


def render_md(menu, chosen_id=None):
    """给用户挑的菜单（中英双语）。"""
    lines = [u"# 收尾效果 · 请挑一个", ""]
    lines.append(u"> The ending does not have to be a standing pose. "
                 u"Pick the last gesture — it is what the audience remembers.")
    lines.append(u">")
    lines.append(u"> 全片结束**不一定**要站定。最后一个动作决定观众记住什么，所以给你挑。")
    lines.append("")
    lines.append(u"| # | 效果 / Effect | 一句话 / What | 为什么推荐 / Why |")
    lines.append(u"|---|----------------|---------------|------------------|")
    for e in menu:
        mark = u" ← 已选" if chosen_id == e["id"] else ""
        lines.append(u"| %d | **%s** / %s%s | %s | %s |"
                     % (e["rank"], e["name_zh"], e["name_en"], mark,
                        e["what_zh"], e["why"]))
    lines.append("")
    for e in menu:
        lines.append("---")
        lines.append("")
        lines.append(u"## %d. %s　`%s`" % (e["rank"], e["name_zh"], e["id"]))
        lines.append(u"### %s" % e["name_en"])
        lines.append("")
        lines.append(u"**%s**　%s" % (e["what_zh"], e["what_en"]))
        lines.append("")
        lines.append(u"- 前置条件 / Needs：%s" % e["needs"])
        lines.append(u"- 卡点 / Beat：%s" % e["beat_hint"])
        lines.append(u"- 为什么推荐：%s" % e["why"])
        lines.append("")
        lines.append(u"**中文收尾（进【内容提示词】）**")
        lines.append("")
        lines.append(u"```text")
        lines.append(e["prompt_zh"])
        lines.append(u"```")
        lines.append("")
        lines.append(u"**English ending (goes into content_prompt)**")
        lines.append("")
        lines.append(u"```text")
        lines.append(e["prompt_en"])
        lines.append(u"```")
        lines.append("")
    lines.append("---")
    lines.append("")
    lines.append(u"## 怎么选 / How to choose")
    lines.append("")
    lines.append(u"```bash")
    lines.append(u"python3 scripts/mvstudio.py endings --pick reach_and_crack")
    lines.append(u"python3 scripts/mvstudio.py confirm --step ending")
    lines.append(u"```")
    lines.append("")
    lines.append(u"> ⚠️ 所有收尾都**不允许改变人物身份**：不许融化、变粒子、换脸、换服装。"
                 u"消失的是「画」，不是「人」。")
    lines.append("")
    return "\n".join(lines) + "\n"


def main(argv=None):
    import argparse
    ap = argparse.ArgumentParser(description="收尾效果菜单")
    common.add_common_args(ap)
    ap.add_argument("--pick", default=None, help=u"选定效果 id")
    ap.add_argument("--list", action="store_true", help=u"只列 id 与名字")
    ap.add_argument("--plan", default=None)
    args = ap.parse_args(argv)
    common.apply_common_args(args)

    if args.list:
        for e in CATALOG:
            common.echo(u"  %-22s %s / %s" % (e["id"], e["name_zh"], e["name_en"]))
        return 0

    plan_path = args.plan or os.path.join(common.path("workspace_analysis"),
                                          "director_plan.json")
    plan = common.read_json(plan_path, {}) or {}
    analysis = common.read_json(os.path.join(common.path("workspace_analysis"),
                                             "music.json"), {}) or {}
    menu = build_menu(analysis, plan)

    if args.pick:
        if args.pick not in _BY_ID:
            common.echo(u"没有这个收尾效果：%s" % args.pick)
            common.echo(u"可选：%s" % u"、".join(ids()))
            return 2
        apply_ending(plan, args.pick)
        common.write_json(plan_path, plan)
        common.write_text(os.path.join(common.path("output_latest"), "endings.md"),
                          render_md(menu, chosen_id=args.pick))
        e = get(args.pick)
        common.echo(u"已选收尾：%s / %s" % (e["name_zh"], e["name_en"]))
        common.echo(u"  然后确认这一步：python3 scripts/mvstudio.py confirm --step ending")
        return 0

    md = render_md(menu)
    common.write_text(os.path.join(common.path("output_latest"), "endings.md"), md)
    if args.json:
        common.emit({"menu": menu, "md": os.path.join(common.path("output_latest"),
                                                      "endings.md")}, True)
    else:
        common.echo(md)
    return 0


if __name__ == "__main__":
    sys.exit(main())
