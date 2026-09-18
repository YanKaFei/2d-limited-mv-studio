#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""threeview —— 把用户上传的**一张**人物图，展开成可用的三视图（人物转面表）。

为什么必须有这一步：
  一张正面图丢给视频模型，转个身脸就崩。三视图（正面 / 四分之三 / 侧面 / 背面）
  把发型体积、侧面轮廓、背面服装结构钉死，是**人物一致性**最便宜的一道保险。
  它同时也解决了「用户只有一张图」和「14.5 秒 × N 条各自独立生成」之间的矛盾。

本模块做三件事：
  1. 产出三视图的**生成规格**（构图 / 姿势 / 背景 / 线条一致性）
  2. 产出**可直接粘贴**的图像生成提示词（中英双语）+ 负向提示词
  3. 产出**一致性检查单**：canon 里缺什么字段，三视图就会在哪崩

注意：本模块不生成图片。图要交给用户的图像模型出；出完把文件放进
input/character/，它会作为 <Picture 2> 一起上传给 MiniMax H3。
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common  # noqa: E402

CORE_FIELDS = [
    ("hair", u"发型 / 发长 / 发色 / 刘海", "hairstyle length colour and bangs"),
    ("eyes", u"眼型 / 瞳色 / 眼距", "eye shape iris colour and spacing"),
    ("face", u"脸型 / 五官比例 / 年龄感", "face shape feature proportions apparent age"),
    ("costume", u"服装结构 / 领口 / 袖型 / 下摆", "costume structure collar sleeve hem"),
    ("accessories", u"核心配饰（不可删）", "signature accessories that must not be removed"),
    ("silhouette", u"整体轮廓 / 身体比例", "overall silhouette and body proportion"),
]

_VIEW_EN = {
    "front": "front view",
    "three-quarter": "three-quarter view",
    "side": "full side profile",
    "back": "back view",
}
_VIEW_ZH = {
    "front": u"正面",
    "three-quarter": u"四分之三侧面",
    "side": u"正侧面",
    "back": u"背面",
}


def _tv_cfg():
    try:
        return common.config().get("threeview", {}) or {}
    except Exception:
        return {}


def build_spec(canon, cfg=None):
    """产出三视图的生成规格。canon 只用来判断有没有可渲染的字段。"""
    cfg = cfg or _tv_cfg()
    views = list(cfg.get("views") or ["front", "three-quarter", "side", "back"])
    extra = list(cfg.get("extra") or ["head close-up", "colour chart"])
    panels = len(views)
    base_layout = (cfg.get("layout")
                   or "equal panels in one row, identical scale, "
                      "feet aligned to a common baseline")
    # 只在配置里没写格数时补上，避免「four equal panels …, 4 equal panels …」
    layout = base_layout
    if "panel" not in base_layout.lower():
        layout = "%d %s" % (panels, base_layout)
    spec = {
        "views": views,
        "extra": extra,
        "panels": panels,
        "layout": layout,
        "background": cfg.get("background") or "neutral flat grey, no scenery",
        "pose": cfg.get("pose") or "relaxed A-pose, arms slightly away from the body",
        "line_consistency": cfg.get("line_consistency") or
                            "single consistent line weight, identical rendering pass",
        "has_canon": bool(canon),
    }
    return spec


def _canon_lines(canon):
    out = []
    for field, _zh, _en in CORE_FIELDS:
        val = str((canon or {}).get(field) or "").strip()
        if val:
            out.append("%s: %s" % (field, val))
    ids = (canon or {}).get("stable_identifiers") or []
    if ids:
        out.append("stable identifiers that must stay identical: %s" % ", ".join(ids))
    colors = (canon or {}).get("dominant_colors") or []
    if colors:
        out.append("dominant colours: %s" % ", ".join(colors))
    return out


def render_prompt(spec, canon, lang="en"):
    """可直接粘贴到图像模型的三视图生成提示词。"""
    name = (canon or {}).get("name") or "the character"
    views = spec.get("views") or []
    if lang == "zh":
        return _render_zh(spec, canon, name, views)
    return _render_en(spec, canon, name, views)


def _render_en(spec, canon, name, views):
    order = ", ".join(_VIEW_EN.get(v, v) for v in views)
    lines = [
        "Character turnaround sheet / model sheet of the SAME character, %s." % name,
        "Layout: %s." % spec["layout"],
        "Views, left to right: %s." % order,
        "Extra panels: %s." % ", ".join(spec.get("extra") or []),
        "Pose: %s. Identical pose family across every panel." % spec["pose"],
        "Background: %s." % spec["background"],
        "Rendering: %s. 2D hand-drawn illustration, flat cel shading, "
        "clean confident line work, limited palette." % spec["line_consistency"],
        "",
        "The character must be the same character in every panel: same face, "
        "same feature proportions, same eye shape and iris colour, same hairstyle "
        "and hair colour, same apparent age, same body proportion, same costume "
        "structure, same signature accessories.",
        "",
        "Character sheet facts (these are the source of truth, do not invent new ones):",
    ]
    lines += ["- " + l for l in _canon_lines(canon)]
    lines += [
        "",
        "Do not redesign the character. Do not change the outfit between panels. "
        "Do not add accessories that are not listed. Keep the scale identical across "
        "panels so the sheets can be overlaid.",
    ]
    return "\n".join(lines)


def _render_zh(spec, canon, name, views):
    order = u"、".join(_VIEW_ZH.get(v, v) for v in views)
    lines = [
        u"人物三视图 / 设定表（同一角色的多角度转面），角色：%s。" % name,
        u"排版：%s。" % spec["layout"],
        u"从左到右依次为：%s。" % order,
        u"附加格：%s。" % u"、".join(spec.get("extra") or []),
        u"姿势：%s，所有格使用同一套姿势族。" % spec["pose"],
        u"背景：%s。" % spec["background"],
        u"画法：%s。2D 手绘插画，平面赛璐璐上色，干净肯定的线条，有限色板。"
        % spec["line_consistency"],
        "",
        u"每一格都必须是同一个角色：同一张脸、同一五官比例、同一眼型与瞳色、"
        u"同一发型发色、同一年龄感、同一身体比例、同一服装结构、同一核心配饰。",
        "",
        u"设定表事实（这是唯一真相，不得自行新增）：",
    ]
    lines += [u"- " + l for l in _canon_lines(canon)]
    lines += [
        "",
        u"不要重新设计角色。不要在格与格之间换衣服。不要添加未列出的配饰。"
        u"所有格保持同一比例，保证可以直接叠图比对。",
    ]
    return "\n".join(lines)


def render_negative(spec=None):
    """负向提示词：专治视频模型最容易犯的「三视图综合症」。"""
    return ("multiple characters, different character, different face, "
            "different outfit, wardrobe change, extra accessories, "
            "inconsistent scale, different art style between panels, "
            "3D render, photorealistic, depth of field, motion blur, "
            "watermark, signature, text, cropped limbs, extra limbs, "
            "background scenery, colour cast between panels")


def consistency_checklist(canon):
    """canon 缺哪个字段，三视图就会在哪一维度崩。返回 [{field, ok, hint}]。"""
    out = []
    canon = canon or {}
    for field, zh, en in CORE_FIELDS:
        val = str(canon.get(field) or "").strip()
        out.append({
            "field": field,
            "ok": bool(val),
            "label": zh,
            "hint": (u"已填写" if val else
                     u"缺 %s —— 三视图会在这一维度上各画各的（需要：%s）" % (zh, en)),
        })
    ids = canon.get("stable_identifiers") or []
    out.append({
        "field": "stable_identifiers",
        "ok": bool(ids),
        "label": u"核心识别物清单",
        "hint": (u"%d 项" % len(ids)) if ids else
                u"缺核心识别物 —— 跨 14.5 秒的条与条之间没有可校验的锚点",
    })
    return out


def unusable_fields(canon):
    return [c["field"] for c in consistency_checklist(canon) if not c["ok"]]


def render_md(spec, canon, negative=None, checklist=None):
    """人读版：三视图规格 + 提示词 + 检查单 + 上传说明。"""
    negative = negative if negative is not None else render_negative(spec)
    checklist = checklist if checklist is not None else consistency_checklist(canon)
    lines = ["# 三视图（人物转面表）· 规格与提示词", ""]
    lines.append(u"> 一张正面图丢给视频模型，转个身脸就崩。三视图把发型体积、"
                 u"侧面轮廓、背面服装结构钉死——这是**人物一致性**最便宜的一道保险。")
    lines.append("")
    lines.append("## 一、上传前先补字段")
    lines.append("")
    lines.append("| 字段 | 状态 | 说明 |")
    lines.append("|------|------|------|")
    for c in checklist:
        lines.append("| `%s` | %s | %s |"
                     % (c["field"], u"✅" if c["ok"] else u"❌", c["hint"]))
    lines.append("")
    lines.append("## 二、生成规格")
    lines.append("")
    for k in ("panels", "layout", "pose", "background", "line_consistency"):
        lines.append("- **%s**：%s" % (k, spec.get(k)))
    lines.append("")
    lines.append("## 三、图像模型提示词（英文）")
    lines.append("")
    lines.append("```text")
    lines.append(render_prompt(spec, canon, lang="en"))
    lines.append("```")
    lines.append("")
    lines.append("## 四、图像模型提示词（中文）")
    lines.append("")
    lines.append("```text")
    lines.append(render_prompt(spec, canon, lang="zh"))
    lines.append("```")
    lines.append("")
    lines.append("## 五、负向提示词")
    lines.append("")
    lines.append("```text")
    lines.append(negative)
    lines.append("```")
    lines.append("")
    lines.append("## 六、出图之后怎么用")
    lines.append("")
    lines.append("1. 把生成的三视图存成 `input/character/threeview.png`；")
    lines.append("2. 重新跑 `python3 scripts/mvstudio.py canon` —— 它会自动认出来；")
    lines.append("3. 交付时它会作为 `<Picture 2>`（character turnaround reference）"
                 "与原始人物图 `<Picture 1>` 一起上传；")
    lines.append("4. 官方规则：这张图**只用来定义角色**，所以它会被引在 `<Subject 1>` "
                 "的定义里，而**不是**单独建一条 `<Picture 2>` 帧条目。")
    lines.append("")
    return "\n".join(lines) + "\n"


def main(argv=None):
    import argparse
    ap = argparse.ArgumentParser(description="生成三视图规格与提示词")
    common.add_common_args(ap)
    ap.add_argument("--canon", default=None, help="character_canon.json 路径")
    ap.add_argument("--lang", choices=["en", "zh", "both"], default="both")
    ap.add_argument("--md", action="store_true", help="输出人读 Markdown")
    args = ap.parse_args(argv)
    common.apply_common_args(args)
    canon_path = args.canon or os.path.join(common.path("workspace_character"),
                                            "character_canon.json")
    canon = common.read_json(canon_path, {}) or {}
    spec = build_spec(canon)
    res = {"spec": spec, "prompt_en": render_prompt(spec, canon, "en"),
           "prompt_zh": render_prompt(spec, canon, "zh"),
           "negative": render_negative(spec),
           "checklist": consistency_checklist(canon),
           "unusable_fields": unusable_fields(canon)}
    if args.json:
        common.emit(res, True)
    elif args.md:
        common.echo(render_md(spec, canon))
    else:
        common.echo(res["prompt_en"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
