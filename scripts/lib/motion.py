#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""motion —— 「魔性」动作设计：魔性度 + 节拍驱动的循环表 + 全片唯一 hook。

**魔性不是「动作多」，是「同一个动作反复出现」。** 所以这一层的核心不是词表，
而是**重复的排布**。

三层：

  魔性度 viral_level   0 克制 / 1 律动 / 2 魔性 / 3 洗脑
                       逐段由音乐能量推算（低谷→克制，峰值→魔性），可手改
  循环表 schedule      由**拍网格**推：动作单元几拍、几小节一循环、重复几次、
                       第几次变异、用哪种变体（变速/错拍/截断）
  hook                 全片**只有一个**记忆点动作，副歌必出现，逐段变异

为什么循环表要从拍网格推、而不是「每段重复 4 次」拍脑袋：
  公开的音乐驱动舞蹈生成研究（MACE-Dance / Learning2Dance / DanceFormer /
  DanceNet3D / SoulDance）共同的前提就是**动作周期由节拍决定**。
  本技能不接它们的依赖，只采纳这条原理。

动画原则（12 条）用来让重复**有动感**，而不是机械重复——
「挤压拉伸」造憨，「预备动作」造起手，「跟随重叠」造头发衣摆的延迟。
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
PKG_ROOT = os.path.dirname(os.path.dirname(HERE))
_LIB_CACHE = [None]

# 能量 → 魔性度 的自动推算（可手改）
_ENERGY_LEVEL = {
    "quiet": 0,
    "breakdown": 1,
    "mid": 1,
    "build": 2,
    "peak": 3,
}


def _library():
    if _LIB_CACHE[0] is None:
        path = os.path.join(PKG_ROOT, "references", "motion-design.json")
        _LIB_CACHE[0] = common.read_json(path, {}) or {}
    return _LIB_CACHE[0]


def reload():
    _LIB_CACHE[0] = None
    return _library()


# ------------------------------------------------------------------ 库
def viral_levels():
    return list(_library().get("viral_levels") or [])


def hooks():
    return list(_library().get("hooks") or [])


def variations():
    return list(_library().get("variations") or [])


def principles():
    return list(_library().get("principles") or [])


def rules():
    return dict(_library().get("rules") or {})


def _by_id(items, key):
    for it in items:
        if it.get("id") == key:
            return it
    return None


def level(level_id_or_num):
    """支持用 id 或 level 数字查档位。"""
    for lv in viral_levels():
        if lv.get("id") == level_id_or_num or lv.get("level") == level_id_or_num:
            return lv
    return None


def hook(hook_id):
    return _by_id(hooks(), hook_id)


def variation(vid):
    return _by_id(variations(), vid)


def principle(pid):
    return _by_id(principles(), pid)


# ------------------------------------------------------------------ 魔性度
def pick_viral_level(seg, analysis=None, i=None, n=None):
    """按段落能量 + 全片位置自动推魔性度。0–3。

    为什么要看位置：**魔性是攒起来再爆的。**
    实测踩到过——全曲能量平坦时（纯节拍轨、无明显副歌），四段会落在同一档，
    用户根本看不到「魔性」这个词兑现。所以后半段与结尾各加一档，
    保证任何一首歌都能自然形成 主歌克制 → 副歌魔性 → 结尾洗脑 的弧线。
    """
    energy = (seg or {}).get("energy")
    lv = _ENERGY_LEVEL.get(energy)
    if lv is None:
        lv = 2 if (analysis or {}).get("bpm") else 1
    # 起音密度高（音乐碎）→ 更适合高频重复
    dens = (analysis or {}).get("rhythmic_density")
    try:
        if dens is not None and float(dens) >= 2.0 and lv < 3:
            lv += 1
    except (TypeError, ValueError):
        pass
    # 位置推进：后半段 +1，收尾再 +1
    if i is not None and n and int(n) > 1:
        progress = float(i) / float(int(n) - 1)
        if progress >= 0.5:
            lv += 1
        if progress >= 0.85:
            lv += 1
    return max(0, min(3, lv))


# ------------------------------------------------------------------ 循环表
def _beats_available(seg, analysis):
    bs, be = seg.get("beat_start"), seg.get("beat_end")
    if bs is not None and be is not None and be > bs:
        return int(be - bs), True
    # 退化为按秒：没有拍网格也能给出可用的循环次数
    dur = float(seg.get("time_end") or 0) - float(seg.get("time_start") or 0)
    return max(1, int(round(dur / 2.0))), False


def build_schedule(seg, analysis=None, level=None, hook_id=None):
    """由拍网格生成这一段的重复循环表。

    返回 dict：unit_beats / cycle_bars / repeats / mutation_at / variations /
              total_beats / hook_id / degraded
    """
    lib = _library()
    if not lib:
        return {}
    avail, beat_driven = _beats_available(seg, analysis or {})
    if level is None:
        level = pick_viral_level(seg, analysis)
    lv = globals()["level"](level) or (viral_levels() or [None])[0]
    if not lv:
        return {}

    unit = int(lv.get("unit_beats") or 1)
    cycle_bars = int(lv.get("cycle_bars") or 1)
    lo, hi = (lv.get("repeat_range") or [1, 1])[:2]

    # 一个循环占几拍：cycle_bars 小节 × 每小节拍数（默认 4）
    beats_per_bar = 4
    cycle_beats = max(unit, cycle_bars * beats_per_bar)
    fit = max(1, avail // cycle_beats)          # 这一段放得下几个循环
    # 绝不超出可用拍数 —— 宁可少重复，也不要求做不完的动作
    repeats = max(1, min(int(hi), fit))
    if not beat_driven:
        # 降级路径：没有拍网格时 avail 是按秒估的，会算出很小的 fit，
        # 把「洗脑」压成「重复 1 次」——那不是退化，那是**失效**。
        # 所以降级时按档位本身的设计意图给重复次数。
        repeats = max(int(lo), min(int(hi), max(fit, int(lo))))

    # 变异：每 mutation_every 轮一次；最后一次也算一个变异点
    # （洗脑档的「末次截断」本来就是发生在最后一次重复上）
    every = int(lv.get("mutation_every") or 1)
    mutation_at = []
    if repeats > 1 and every > 1:
        mutation_at = [k for k in range(every, repeats + 1, every)]

    # 变体与变异点**一一配对**：最后一次优先用 drop_last_rep，其余轮换
    pool = list(lv.get("variations") or [])
    var_list, seen = [], {}
    for i, at in enumerate(mutation_at):
        if at == repeats and "drop_last_rep" in pool:
            pick = "drop_last_rep"
        elif pool:
            pick = pool[i % len(pool)]
        else:
            pick = None
        if pick:
            seen[pick] = 1
            var_list.append(pick)
    total_beats = repeats * cycle_beats

    return {
        "viral_level": int(lv["level"]),
        "viral_name": lv["id"],
        "viral_name_cn": lv["name_cn"],
        "unit_beats": unit,
        "cycle_bars": cycle_bars,
        "cycle_beats": cycle_beats,
        "repeats": repeats,
        "mutation_at": mutation_at,
        "variations": var_list,
        "total_beats": total_beats,
        "beats_available": avail,
        "hook_id": hook_id,
        "degraded": not beat_driven,
    }


# ------------------------------------------------------------------ hook
def apply_hook(plan, hook_id):
    """全片**只有一个** hook —— 换就是替换，不是新增。未知 id 抛 KeyError。"""
    h = hook(hook_id)                     # 未知会返回 None
    if h is None:
        raise KeyError(hook_id)
    plan = plan or {}
    md = plan.setdefault("motion_design", {})
    md["hook_id"] = h["id"]
    md["hook_name_cn"] = h["name_cn"]
    md["hook_name_en"] = h["name_en"]
    return plan


def hook_for_segment(plan, seg):
    """这一段要不要带 hook：带勾的段落（副歌/峰值）必须带；其余按每 N 次出现。"""
    md = (plan or {}).get("motion_design") or {}
    hid = md.get("hook_id")
    if not hid:
        return None
    if seg.get("energy") == "peak":
        return hid
    every = int(md.get("hook_every") or 2)
    try:
        idx = int(seg.get("id") or 1)
    except (TypeError, ValueError):
        idx = 1
    return hid if (idx % every == 0) else None


def build_all(plan, analysis=None, default_level=None):
    """给全片每一段生成 motion 层。手改过的段保留。"""
    lib = _library()
    if not lib:
        return plan
    md = plan.setdefault("motion_design", {})
    if default_level is not None:
        md["default_level"] = int(default_level)
    segs = plan.get("segments") or []
    n = len(segs)
    for i, seg in enumerate(segs):
        prev = seg.get("motion") or {}
        manual = bool(prev.get("manual"))
        if manual and prev.get("viral_level") is not None:
            lv = int(prev["viral_level"])
        else:
            lv = (int(md["default_level"]) if md.get("default_level") is not None
                  else pick_viral_level(seg, analysis, i=i, n=n))
        hid = hook_for_segment(plan, seg)
        sch = build_schedule(seg, analysis, level=lv, hook_id=hid)
        if manual:
            sch["manual"] = True
        seg["motion"] = sch
    return plan


# ------------------------------------------------------------------ 校验
def validate_plan(plan):
    """返回 (problems, warnings)。库坏掉时两者都空（不拿空库乱判）。"""
    lib = _library()
    problems, warnings = [], []
    if not lib:
        return problems, warnings
    valid_levels = {lv["level"] for lv in viral_levels()}
    valid_ids = {lv["id"] for lv in viral_levels()}
    valid_hooks = {h["id"] for h in hooks()}
    valid_vars = {v["id"] for v in variations()}

    md = (plan or {}).get("motion_design") or {}
    if md.get("hook_id") and md["hook_id"] not in valid_hooks:
        problems.append(u"C 歌词：motion_design.hook_id '%s' 不在 hook 菜单里"
                        % md["hook_id"])

    for seg in (plan or {}).get("segments") or []:
        label = seg.get("label") or ("#%s" % seg.get("id"))
        m = seg.get("motion")
        if not m:
            continue
        lv = m.get("viral_level")
        if lv is None or (lv not in valid_levels and m.get("viral_name") not in valid_ids):
            problems.append(u"C 歌词：段 %s 的魔性度 '%s' 非法（应为 0–3）" % (label, lv))
            continue
        avail = m.get("beat_end", seg.get("beat_end"))
        start = m.get("beat_start", seg.get("beat_start"))
        total = m.get("total_beats")
        if total is not None and avail is not None and start is not None:
            room = int(avail) - int(start)
            if int(total) > room:
                problems.append(u"C 歌词：段 %s 的循环表要 %s 拍，但这一段只有 %s 拍 —— "
                                u"放不下（写不动作的要求等于废纸）"
                                % (label, total, room))
        for v in m.get("variations") or []:
            if v not in valid_vars:
                problems.append(u"C 歌词：段 %s 的变异 '%s' 不在变体库里" % (label, v))
        if seg.get("energy") == "peak" and md.get("hook_id") and not m.get("hook_id"):
            warnings.append(u"段 %s 是峰值段，但没带上全片 hook `%s` —— "
                            u"魔性靠的就是副歌反复出现同一个动作"
                            % (label, md["hook_id"]))
    return problems, warnings


# ------------------------------------------------------------------ 渲染
def render_schedule(plan, seg, lang="zh"):
    """把循环表写成可执行的重复指令（进【内容提示词】）。"""
    m = seg.get("motion") or {}
    if not m:
        return ""
    out = []
    hook_id = m.get("hook_id")
    h = hook(hook_id) if hook_id else None

    if lang == "zh":
        out.append(u"重复设计（魔性档：%s）：这个动作单元 %s 拍做完，"
                   u"每 %s 小节一循环，连续重复 %s 次"
                   % (m.get("viral_name_cn") or m.get("viral_name"),
                      m.get("unit_beats"), m.get("cycle_bars"), m.get("repeats")))
        if h:
            out.append(u"记忆点动作「%s」：%s。每一次重复都必须落在重拍上。"
                       % (h["name_cn"], h["body_zh"]))
        for i, mut in enumerate(m.get("mutation_at") or []):
            vs = m.get("variations") or []
            vid = vs[i % len(vs)] if vs else None
            v = variation(vid) if vid else None
            if v:
                out.append(u"第 %s 次循环做变异：%s" % (mut, v["prompt_zh"]))
            else:
                out.append(u"第 %s 次循环做一次变奏，动作本身不变" % mut)
        if m.get("degraded"):
            out.append(u"（本段没有可靠拍网格，重复按秒对齐，不是按拍）")
    else:
        out.append("Repetition design (viral level: %s): this move unit takes %s beat(s), "
                   "loops every %s bar(s), repeated %s times in a row"
                   % (m.get("viral_name"), m.get("unit_beats"),
                      m.get("cycle_bars"), m.get("repeats")))
        if h:
            out.append("Hook move \"%s\": %s. Every repetition lands on a downbeat."
                       % (h["name_en"], h["body_en"]))
        for i, mut in enumerate(m.get("mutation_at") or []):
            vs = m.get("variations") or []
            vid = vs[i % len(vs)] if vs else None
            v = variation(vid) if vid else None
            out.append("Cycle %s mutates: %s" % (mut, v["prompt_en"]) if v
                       else "Cycle %s varies without changing the move" % mut)
        if m.get("degraded"):
            out.append("(No reliable beat grid in this segment; repetition is aligned "
                       "to seconds, not beats.)")
    return u" ".join(out)


def render_md(plan=None, chosen_hook=None):
    lines = [u"# 魔性动作设计 · 请挑一个记忆点动作", ""]
    lines.append(u"> **魔性不是「动作多」，是「同一个动作反复出现」。**")
    lines.append(u"> 全片只留**一个** hook，副歌每次都出现它，并逐段变异。")
    lines.append("")
    lines.append(u"## 魔性度档位")
    lines.append("")
    lines.append(u"| 档 | id | 动作单元 | 循环 | 重复次数 | 变异 | 适合 |")
    lines.append(u"|----|----|---------|------|---------|------|------|")
    for lv in viral_levels():
        lines.append(u"| %d | `%s` %s | %s 拍 | %s 小节 | %s–%s | 每 %s 轮 | %s |"
                     % (lv["level"], lv["id"], lv["name_cn"], lv["unit_beats"],
                        lv["cycle_bars"], lv["repeat_range"][0], lv["repeat_range"][1],
                        lv["mutation_every"], lv["desc_zh"]))
    lines.append("")
    lines.append(u"默认：**逐段自动推**（低谷→克制，峰值→魔性），可手改。")
    lines.append("")
    lines.append(u"## 记忆点动作菜单")
    lines.append("")
    lines.append(u"| id | 名称 | 做什么 | 为什么魔性 | 用到的手法 |")
    lines.append(u"|----|------|--------|-----------|-----------|")
    for h in hooks():
        mark = u" ← 已选" if chosen_hook == h["id"] else ""
        pr = u"、".join((principle(p) or {}).get("name_cn", p)
                       for p in (h.get("principles") or []))
        lines.append(u"| `%s` | **%s**%s | %s | %s | %s |"
                     % (h["id"], h["name_cn"], mark, h["body_zh"], h["why_zh"], pr))
    lines.append("")
    lines.append(u"## 怎么用")
    lines.append("")
    lines.append(u"```bash")
    lines.append(u"python3 scripts/mvstudio.py motion                      # 看菜单 + 当前设计")
    lines.append(u"python3 scripts/mvstudio.py motion --hook shoulder_pop_8")
    lines.append(u"python3 scripts/mvstudio.py motion --viral 3            # 全片洗脑档")
    lines.append(u"python3 scripts/mvstudio.py motion --segment C2 --viral 0  # 单段克制")
    lines.append(u"python3 scripts/mvstudio.py confirm --step motion")
    lines.append(u"```")
    lines.append("")
    if plan:
        lines.append(u"## 当前逐段设计")
        lines.append("")
        lines.append(u"| 段 | 能量 | 魔性档 | 单元 | 重复 | 变异点 | hook |")
        lines.append(u"|----|------|--------|------|------|--------|------|")
        for seg in plan.get("segments") or []:
            m = seg.get("motion") or {}
            lines.append(u"| %s | %s | %s | %s 拍 | %s 次 | %s | %s |"
                         % (seg.get("label"), seg.get("energy"),
                            m.get("viral_name_cn") or u"—", m.get("unit_beats") or u"—",
                            m.get("repeats") or u"—",
                            u"、".join(str(x) for x in (m.get("mutation_at") or [])) or u"—",
                            m.get("hook_id") or u"—"))
        lines.append("")
    lines.append(u"## 十二动画原则（让重复有动感，不是机械重复）")
    lines.append("")
    for p in principles():
        lines.append(u"- **%s / %s** —— %s" % (p["name_cn"], p["name_en"], p["apply_zh"]))
    lines.append("")
    return "\n".join(lines) + "\n"


def main(argv=None):
    import argparse
    ap = argparse.ArgumentParser(description="魔性动作设计")
    common.add_common_args(ap)
    ap.add_argument("--hook", default=None, help=u"选记忆点动作")
    ap.add_argument("--viral", type=int, default=None, help=u"全片魔性度 0–3")
    ap.add_argument("--segment", default=None, help=u"只改某一段")
    ap.add_argument("--plan", default=None)
    args = ap.parse_args(argv)
    common.apply_common_args(args)

    plan_path = args.plan or os.path.join(common.path("workspace_analysis"),
                                          "director_plan.json")
    plan = common.read_json(plan_path, {}) or {}
    analysis = common.read_json(os.path.join(common.path("workspace_analysis"),
                                             "music.json"), {}) or {}

    if args.hook or args.viral is not None or args.segment:
        if args.hook:
            try:
                apply_hook(plan, args.hook)
            except KeyError:
                common.echo(u"没有这个 hook：%s" % args.hook)
                common.echo(u"可选：%s" % u"、".join(h["id"] for h in hooks()))
                return 2
        if args.segment and args.viral is not None:
            for seg in plan.get("segments") or []:
                if seg.get("label") == args.segment:
                    seg["motion"] = dict(seg.get("motion") or {})
                    seg["motion"]["viral_level"] = args.viral
                    seg["motion"]["manual"] = True
        build_all(plan, analysis,
                  default_level=args.viral if not args.segment else None)
        common.write_json(plan_path, plan)
        md = render_md(plan, chosen_hook=(plan.get("motion_design") or {}).get("hook_id"))
        common.write_text(os.path.join(common.path("output_latest"),
                                       "motion_design.md"), md)
        common.echo(u"已更新魔性动作设计 → %s" % plan_path)
        for seg in plan.get("segments") or []:
            m = seg.get("motion") or {}
            common.echo(u"  %s  档=%s 单元=%s拍 重复=%s次 变异=%s hook=%s"
                        % (seg.get("label"), m.get("viral_name_cn"),
                           m.get("unit_beats"), m.get("repeats"),
                           m.get("mutation_at") or u"—", m.get("hook_id") or u"—"))
        common.echo(u"  然后确认：python3 scripts/mvstudio.py confirm --step motion")
        return 0

    md = render_md(plan)
    common.write_text(os.path.join(common.path("output_latest"), "motion_design.md"), md)
    if args.json:
        common.emit({"levels": len(viral_levels()), "hooks": len(hooks()),
                     "variations": len(variations()),
                     "principles": len(principles()),
                     "hook_id": (plan.get("motion_design") or {}).get("hook_id"),
                     "md": os.path.join(common.path("output_latest"),
                                        "motion_design.md")}, True)
    else:
        common.echo(md)
    return 0


if __name__ == "__main__":
    sys.exit(main())
