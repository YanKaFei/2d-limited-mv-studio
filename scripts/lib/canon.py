#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""canon —— 人物 Canon：一张图 → 可跨 14.5 秒 × N 条复用的身份锚点。

分工（很重要，别越界）：
  * 脚本只做**可以被测量**的部分：格式 / 尺寸 / 画幅 / 主导色 / 明暗与饱和基调。
  * 「看脸、看发型、看服装结构」是 **Agent 的视觉活**——脚本给出空白骨架，
    Agent 必须真的用视觉能力看图再填。
  * 脚本**绝不修改用户原图**，只在 workspace/character/ 放一份工作副本。

为什么 Canon 是必须的：
  一条 MV 会被切成 N 个 14.5 秒独立生成。每一代模型都看不到别人，所以
  唯一能让「始终是同一个人」成立的东西，就是这段 Canon + 三视图参考图。

AGENTS.md 的原则同样适用：**数字是信号，不是结论。**
"""

import os
import shutil
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common  # noqa: E402
import imgprobe  # noqa: E402

# Level A：绝对不可改变
LEVEL_A = [
    "apparent_age_style", "body_proportion", "face_shape", "eye_shape", "eye_color",
    "hair_color", "hair_length", "hair_shape", "bangs", "upper_costume",
    "lower_costume", "signature_accessories", "silhouette",
]
# Level B：高优先保留
LEVEL_B = [
    "head_accessories", "hair_accessories", "sleeves", "collar", "ribbons", "socks",
    "shoes", "small_details", "local_patterns",
]
# 渲染 H3 时必须在场的最小集（缺任何一项渲染器会拒绝输出）
RENDER_CORE = ["hair", "eyes", "face", "costume", "accessories", "silhouette"]

FORBIDDEN_DRIFT = [
    "face change", "identity drift", "different hairstyle", "hair color change",
    "costume redesign", "wardrobe change", "missing signature accessories",
    "new costume", "age shift", "different body proportion", "character redesign",
    "realistic reinterpretation", "different character",
]

MUST_FILL = RENDER_CORE + ["stable_identifiers"]


def inspect_image(path, copy=True):
    """机械测量 + 工作副本。不修改原图。"""
    path = os.path.abspath(os.path.expanduser(path or ""))
    out = {"path": path, "probe": None, "dominant_colors": [], "tone": None,
           "work_copy": None, "error": None}
    if not os.path.isfile(path):
        out["error"] = u"文件不存在：%s" % path
        return out
    out["probe"] = imgprobe.probe(path)
    try:
        out["dominant_colors"] = imgprobe.dominant_colors(path, top=6)
    except Exception as exc:
        out["dominant_colors"] = []
        out["error"] = u"取色失败：%s" % exc
    try:
        out["tone"] = imgprobe.tone_summary(path)
    except Exception:
        out["tone"] = None
    if copy:
        dst_dir = common.path("workspace_character")
        os.makedirs(dst_dir, exist_ok=True)
        ext = os.path.splitext(path)[1].lower() or ".png"
        dst = os.path.join(dst_dir, "canon_reference" + ext)
        try:
            shutil.copyfile(path, dst)
            out["work_copy"] = dst
        except Exception as exc:
            out["error"] = (out["error"] or "") + u" 工作副本失败：%s" % exc
    return out


def skeleton(name="@character"):
    """Canon 骨架：字段全在，语义全空——等 Agent 看图填。"""
    canon = {
        "name": name,
        "level_a_locked": True,
        "forbidden_drift": list(FORBIDDEN_DRIFT),
        "dominant_colors": [],
        "stable_identifiers": [],
    }
    for f in LEVEL_A + LEVEL_B:
        canon[f] = ""
    for f in RENDER_CORE:
        canon.setdefault(f, "")
    canon["_how_to_fill"] = (
        u"用视觉能力真的看 workspace/character/canon_reference.*，然后填满 "
        u"hair / eyes / face / costume / accessories / silhouette 与 stable_identifiers。"
        u"这些字段会被逐条写进每一条 H3 prompt 的参考信息段落。")
    return canon


def build(image_path, turnaround_path=None):
    measure = inspect_image(image_path)
    canon = skeleton()
    if measure.get("dominant_colors"):
        canon["dominant_colors"] = [c.get("hex") if isinstance(c, dict) else c
                                    for c in measure["dominant_colors"]][:6]
        canon["dominant_colors"] = [c for c in canon["dominant_colors"] if c]
    return {"canon": canon, "measure": measure, "turnaround": turnaround_path}


def missing_fields(canon, include_stable=True):
    need = list(RENDER_CORE) + (["stable_identifiers"] if include_stable else [])
    out = []
    for f in need:
        v = (canon or {}).get(f)
        if v is None or (isinstance(v, str) and not v.strip()) or v == []:
            out.append(f)
    return out


def render_md(canon, measure, checklist=None):
    lines = [u"# Character Canon（人物唯一真相）", ""]
    lines.append(u"> 一张图决定「谁在画面里」。风格只能改**世界**，不能改**人**。")
    lines.append("")
    lines.append(u"## 一、机械测量（数字是信号，不是结论）")
    lines.append("")
    p = (measure or {}).get("probe") or {}
    lines.append(u"- 文件：`%s`" % (measure or {}).get("path"))
    lines.append(u"- 格式 / 尺寸：%s ｜ %s×%s ｜ 画幅 %s ｜ %s"
                 % (p.get("format"), p.get("width"), p.get("height"),
                    p.get("aspect_ratio"), p.get("orientation")))
    tone = (measure or {}).get("tone") or {}
    if tone:
        lines.append(u"- 明度基调 / 饱和度基调：%s ｜ %s"
                     % (tone.get("brightness"), tone.get("saturation")))
    cols = (measure or {}).get("dominant_colors") or []
    if cols:
        lines.append(u"- 主导色：%s"
                     % u"　".join(c.get("hex", "") if isinstance(c, dict) else str(c)
                                  for c in cols))
        lines.append("")
        lines.append(u"| 色 | 占比 |")
        lines.append(u"|----|------|")
        for c in cols:
            if isinstance(c, dict):
                lines.append(u"| `%s` | %s |" % (c.get("hex"), c.get("share")))
    lines.append("")
    lines.append(u"## 二、Level A（绝对不可改变）")
    lines.append("")
    lines.append(u"| 字段 | 值 |")
    lines.append(u"|------|----|")
    for f in LEVEL_A:
        lines.append(u"| `%s` | %s |" % (f, (canon or {}).get(f) or u"**待填**"))
    lines.append("")
    lines.append(u"## 三、Level B（高优先保留）")
    lines.append("")
    lines.append(u"| 字段 | 值 |")
    lines.append(u"|------|----|")
    for f in LEVEL_B:
        lines.append(u"| `%s` | %s |" % (f, (canon or {}).get(f) or u"—"))
    lines.append("")
    lines.append(u"## 四、渲染核心字段（缺任何一项渲染器拒绝输出）")
    lines.append("")
    lines.append(u"| 字段 | 值 |")
    lines.append(u"|------|----|")
    for f in RENDER_CORE:
        lines.append(u"| `%s` | %s |" % (f, (canon or {}).get(f) or u"**待填**"))
    ids = (canon or {}).get("stable_identifiers") or []
    lines.append(u"| `stable_identifiers` | %s |"
                 % (u"、".join(ids) if ids else u"**待填**"))
    lines.append("")
    lines.append(u"## 五、禁止漂移清单（会逐条写进每条 prompt）")
    lines.append("")
    for d in (canon or {}).get("forbidden_drift") or FORBIDDEN_DRIFT:
        lines.append(u"- [ ] %s" % d)
    lines.append("")
    if checklist:
        lines.append(u"## 六、三视图检查单")
        lines.append("")
        for c in checklist:
            lines.append(u"- %s `%s`：%s" % (u"✅" if c["ok"] else u"❌",
                                             c["field"], c["hint"]))
        lines.append("")
    miss = missing_fields(canon)
    lines.append(u"## 结论")
    lines.append("")
    if miss:
        lines.append(u"❌ 还缺 %d 项：%s" % (len(miss), u"、".join(miss)))
        lines.append("")
        lines.append(u"**必须补完才能渲染。** 用视觉能力看工作副本后填 "
                     u"`workspace/character/character_canon.json`。")
    else:
        lines.append(u"✅ Canon 完整，可以渲染。")
    lines.append("")
    return "\n".join(lines) + "\n"


def run(image_path, turnaround_path=None, name="@character"):
    built = build(image_path, turnaround_path)
    built["canon"]["name"] = name
    return built


def main(argv=None):
    import argparse
    ap = argparse.ArgumentParser(description="建立 Character Canon 骨架")
    common.add_common_args(ap)
    ap.add_argument("--image", required=True)
    ap.add_argument("--turnaround", default=None)
    ap.add_argument("--name", default="@character")
    args = ap.parse_args(argv)
    common.apply_common_args(args)
    res = run(args.image, args.turnaround, args.name)
    out = os.path.join(common.path("workspace_character"), "character_canon.json")
    common.write_json(out, res["canon"])
    common.write_text(os.path.join(common.path("output_latest"), "character_canon.md"),
                      render_md(res["canon"], res["measure"]))
    if args.json:
        common.emit({"canon_path": out, "measure": res["measure"],
                     "missing": missing_fields(res["canon"])}, True)
    else:
        common.echo(u"Canon 骨架 → %s" % out)
        common.echo(u"工作副本 → %s（用视觉能力看它，然后填字段）"
                    % (res["measure"] or {}).get("work_copy"))
        common.echo(u"还需填：%s" % u"、".join(missing_fields(res["canon"])))
    return 0


if __name__ == "__main__":
    sys.exit(main())
