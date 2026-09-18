#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""styleroutes —— 给用户 4 条「画风融合路线」，让他在开工前选一条。

为什么不是「你想什么风格？」：
  直接问用户要风格词，得到的通常是「日系」「赛博朋克」这类**泛化词**。
  真正决定成片差别的是**融合语法**——人物在世界里被什么媒介不断重印。
  所以这里给的是 4 条语法完整的路线（每条都已包含 ≥3 种画风的递进），
  用户只需选一条，或从不同路线里挑几段混。

风格词一律**先查 art-aesthetic-vault**（AGENTS.md 硬规则），不凭记忆编造。
库不在时用内置池降级，并明确标注。

四条路线的共同前提：
  * 画风必须能从歌词推出来（lyric → image → movement），不是随便贴。
  * 必须是 2D 限制感：平面构成 + limited animation，不做 3D 运镜。
  * 人物身份不变，变的只有世界。
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common  # noqa: E402

try:
    import artbridge  # noqa: E402
except Exception:  # pragma: no cover
    artbridge = None

HERE = os.path.dirname(os.path.abspath(__file__))          # <root>/scripts/lib
PKG_ROOT = os.path.dirname(os.path.dirname(HERE))          # <root>
REFS = os.path.join(PKG_ROOT, "references")

MIN_DISTINCT = 3

# ------------------------------------------------------------------ 路线模板
# pool 里的 slug 全部取自 art-aesthetic-vault 的真实流派（经 artvault search 核对）。
ROUTE_TEMPLATES = [
    {
        "id": "print-decay",
        "name": "PRINT DECAY · 印刷衰减",
        "pool": ["pop-art", "constructivism", "bauhaus", "op-art", "hard-edge",
                 "conceptual-art", "ukiyo-e"],
        "medium": "risograph misregistration, xerox grain, halftone dots, offset ink",
        "palette": ["#E8503A", "#1D4ED8", "#F4EFE6", "#111111"],
        "why": (u"歌词讲的是被观看、被复制、被评分——那就用**印刷**说话："
                u"人物是唯一一块清晰的印版，世界在每一段里错版套印一次。"),
        "rationale": (u"身份被外部系统不断复印。适合社评、被评价、自我怀疑、城市/表格/"
                      u"标签类歌词。媒介本身在说『你被复制了』。"),
        "negative": ("smooth gradient, glossy 3D render, photorealistic skin, "
                     "neon bloom, depth of field"),
    },
    {
        "id": "paper-world",
        "name": "PAPER WORLD · 纸与剪",
        "pool": ["cubism", "dada", "pop-art", "constructivism", "memphis-design",
                 "superflat", "arts-and-crafts"],
        "why": (u"歌词把世界切成一片一片——那就让世界**真的是纸片**："
                u"人物在层层剪纸平面上跳舞，深度靠图层，不靠透视。"),
        "medium": "torn paper collage, cut paper layers, photocopy texture, flat cel",
        "palette": ["#F2C14E", "#2E5E4E", "#C24B3A", "#F6F1E7"],
        "rationale": (u"世界可拆可换。适合童年、伙伴、房间、记忆碎片类歌词。"
                      u"剪纸的硬边天然带 2D 限制感，不会漂成实拍。"),
        "negative": ("realistic paper texture photo, volumetric lighting, "
                     "3D paper craft, soft airbrush"),
    },
    {
        "id": "ink-line",
        "name": "INK LINE · 线即世界",
        "pool": ["suiboku-ga", "ink-wash-xieyi", "zen-art", "art-brut", "cyanotype",
                 "gongbi", "expressionism"],
        "why": (u"歌词在讲消散、遗忘、留白——那就让画面**由线构成、由线消失**："
                u"人物动作的轨迹可以被擦掉一半，线在沸腾（boiling line）。"),
        "medium": "graphite and brush ink, erasure, cyanotype wash, boiling lines",
        "palette": ["#1B1B1B", "#8A9BA8", "#E8E4DC", "#2F4858"],
        "rationale": (u"消失与残留。适合孤独、遗忘、告别、水面/影子/风类歌词。"
                      u"线描是最省的媒介，也最容易被抽帧做出动画限制感。"),
        "negative": ("full colour rendering, glossy finish, heavy texture overlay, "
                     "3D shading"),
    },
    {
        "id": "gradient-dream",
        "name": "GRADIENT DREAM · 渐变幻景",
        "pool": ["shin-hanga", "luminism", "surrealism", "retro-anime", "y2k",
                 "cottagecore", "art-nouveau"],
        "why": (u"歌词有光、有季节、有回不去的时刻——那就用**新版画的渐变天空**："
                u"世界在人物背后一整块一整块地换色，人物本身一帧不变。"),
        "medium": "shin-hanga gradation, airbrush banding, film grain, cel overlay",
        "palette": ["#F0A868", "#5B7FA6", "#2B3A55", "#F5E6D3"],
        "rationale": (u"氛围与时间流逝。适合夕阳、季节、思念、旅途类歌词。"
                      u"渐变是平面语言，不是 3D 光——不会破坏 2D 感。"),
        "negative": ("photorealistic landscape, HDR, lens flare, volumetric god rays, "
                     "shallow depth of field"),
    },
    {
        "id": "folk-geometry",
        "name": "FOLK GEOMETRY · 民俗几何",
        "pool": ["minhwa", "rimpa", "islamic-geometric", "de-stijl", "naive-art",
                 "blue-green-landscape", "gongbi"],
        "why": (u"歌词里有吉祥物、有纹样、有反复出现的一句——那就让纹样成为**节拍器**："
                u"每过一个重拍，背景纹样多生成一层。"),
        "medium": "flat pattern fill, gold leaf, mineral pigment, screen-printed repeat",
        "palette": ["#C9A227", "#1F5C4A", "#B23A2E", "#F7F2E4"],
        "rationale": (u"重复与仪式感。适合祝福、团圆、民俗、反复副歌类歌词。"
                      u"纹样天然可以逐拍叠加，是卡点最省力的视觉。"),
        "negative": ("baroque depth, oil impasto, dramatic chiaroscuro, 3D relief"),
    },
    {
        "id": "pop-superflat",
        "name": "POP SUPERFLAT · 平面波普",
        "pool": ["superflat", "pop-art", "kitsch", "pixel-art", "memphis-design",
                 "y2k", "retro-anime"],
        "why": (u"歌词在讲可爱、贴纸、屏幕、消费——那就让画面**彻底平面化**："
                u"一切压成一个贴纸面，人物是这个面上唯一会动的东西。"),
        "medium": "flat vinyl colour, sticker outline, screentone, hard pixel edges",
        "palette": ["#FF4E8A", "#3DD6D0", "#FFD400", "#16161A"],
        "rationale": (u"可爱与异化并存。适合副歌反复、网络、可爱但不安的歌词。"
                      u"贴纸平面感让 2D 限制从缺陷变成风格。"),
        "negative": ("realistic perspective, cast shadow with soft falloff, "
                     "3D bevel, glossy plastic render"),
    },
]

# art-aesthetic-vault 不可用时的降级媒介池（按路线）
FALLBACK_MEDIUM = {
    "print-decay": ["risograph", "xerox", "halftone", "offset misregistration",
                    "newsprint", "editorial grid"],
    "paper-world": ["paper collage", "torn paper", "cut paper", "photocopy collage",
                    "flat cel", "hard-edge abstraction"],
    "ink-line": ["graphite", "brush ink", "charcoal", "erasure", "cyanotype wash",
                 "boiling line"],
    "gradient-dream": ["airbrush banding", "film grain", "colour field",
                       "cel overlay", "gradient wash"],
    "folk-geometry": ["flat pattern fill", "mineral pigment", "gold leaf",
                      "screen print repeat", "geometric repeat"],
    "pop-superflat": ["flat vinyl colour", "sticker outline", "screentone",
                      "hard pixel edge", "colour field"],
}


# ------------------------------------------------------------------ 风格库索引
def load_style_map(path=None):
    p = path or os.path.join(REFS, "style-map.json")
    data = common.read_json(p, {}) or {}
    data.setdefault("entries", [])
    return data


def lookup_image(word, style_map=None):
    """按意象词查流派。返回命中的 entry 列表（含 slug）。"""
    if not word:
        return []
    sm = style_map or load_style_map()
    hits = []
    for e in sm.get("entries", []):
        terms = e.get("image") or []
        if any(word == t or word in t or t in word for t in terms):
            hits.append(e)
    return hits


def lookup_lyric(line, style_map=None, limit=3):
    """按一整句歌词查流派，命中多的排前面。返回 [slug]。"""
    if not line:
        return []
    sm = style_map or load_style_map()
    scored = []
    for e in sm.get("entries", []):
        score = 0
        for t in (e.get("image") or []):
            if t and t in line:
                score += 1
        if score:
            scored.append((score, e.get("slug")))
    scored.sort(key=lambda s: (-s[0], s[1] or ""))
    out = []
    for _s, slug in scored:
        if slug and slug not in out:
            out.append(slug)
    return out[:limit]


# ------------------------------------------------------------------ 路线构造
def _lines_for_segment(lines, segments):
    """把歌词行分配到 segments 个段里（不要求等长，保序）。"""
    buckets = [[] for _ in range(max(1, segments))]
    if not lines:
        return buckets
    n = len(lines)
    for i, ln in enumerate(lines):
        idx = min(segments - 1, int(i * segments / float(n)))
        buckets[idx].append(ln)
    return buckets


def _distinct_enough(assign, target):
    return len(set(assign)) >= min(target, len(assign))


def _force_distinct(assign, pool, target=MIN_DISTINCT):
    """把重复项换成池子里还没用过的成员，直到不同画风数达标。"""
    target = min(target, len(assign), len(pool))
    if target <= 0:
        return assign
    guard = 0
    while not _distinct_enough(assign, target) and guard < 50:
        guard += 1
        used = set(assign)
        spare = [p for p in pool if p not in used]
        if not spare:
            break
        # 找出现次数最多的那个，把它的一项换掉
        counts = {}
        for a in assign:
            counts[a] = counts.get(a, 0) + 1
        victim = None
        for i in range(len(assign) - 1, -1, -1):
            if counts.get(assign[i], 0) > 1:
                victim = i
                break
        if victim is None:
            break
        assign[victim] = spare[0]
    return assign


def _break_consecutive_repeats(assign, pool, protect_distinct=MIN_DISTINCT):
    """相邻两段不要同一个画风 —— 用户要的是「在不同艺术风格环境下跳舞」。

    只在池子里还有没用过的候选时才换，避免把不同画风数换少了。
    """
    if len(assign) < 2:
        return assign
    for i in range(1, len(assign)):
        if assign[i] != assign[i - 1]:
            continue
        used = set(assign)
        spare = [p for p in pool if p not in used]
        if spare:
            assign[i] = spare[0]
            continue
        # 池子用完了：挑一个与前后都不同的
        nxt = assign[i + 1] if i + 1 < len(assign) else None
        for cand in pool:
            if cand != assign[i - 1] and cand != nxt:
                assign[i] = cand
                break
    # 换完之后再确认不同画风数没掉下去
    return _force_distinct(assign, pool, protect_distinct)


def build_route(template, lines, segments, style_map=None, vault_available=None):
    """把一条模板 + 具体歌词，变成一次可执行的画风指派。"""
    sm = style_map or load_style_map()
    buckets = _lines_for_segment(lines, segments)
    pool = list(template["pool"])
    assign = []
    for i in range(segments):
        seg_lines = buckets[i] if i < len(buckets) else []
        picks = []
        for ln in seg_lines:
            text = ln.get("text") if isinstance(ln, dict) else str(ln)
            for slug in lookup_lyric(text, sm, limit=3):
                if slug in pool and slug not in picks:
                    picks.append(slug)
        # 段内首选：命中池子的歌词流派；次选：池子轮转
        pick = None
        if picks:
            # 尽量不和上一段完全一样，让画风真的在动
            for c in picks:
                if not assign or c != assign[-1]:
                    pick = c
                    break
            pick = pick or picks[0]
        if pick is None:
            pick = pool[i % len(pool)]
        assign.append(pick)
    assign = _force_distinct(assign, pool)
    assign = _break_consecutive_repeats(assign, pool)

    hit_count = sum(1 for a in assign if a in pool)
    return {
        "id": template["id"],
        "name": template["name"],
        "movements": sorted(set(assign)),
        "pool": pool,
        "movement_per_segment": assign,
        "medium": template["medium"],
        "palette": template["palette"],
        "why": template["why"],
        "rationale": template["rationale"],
        "negative": template["negative"],
        "lyric_hits": hit_count,
        "vault_available": vault_available,
        "vault_hint": (["python3 %s --json layers %s" % (
            os.path.join((common.config().get("external", {}) or {}).get(
                "artvault_repo", ""), "artvault.py"), slug) for slug in
            sorted(set(assign))] if vault_available else []),
    }


def build_routes(lyrics_lines, analysis=None, size=4, segments=None,
                 style_map=None, vault_available=None):
    """按歌词相关性排序，产出 size 条风格融合路线。"""
    sm = style_map or load_style_map()
    if segments is None:
        segments = max(1, len(lyrics_lines or []))
    if vault_available is None:
        try:
            vault_available = bool(artbridge and artbridge.available())
        except Exception:
            vault_available = False

    routes = [build_route(t, lyrics_lines or [], segments, sm, vault_available)
              for t in ROUTE_TEMPLATES]
    # 歌词命中多的排前面 —— 菜单本身就是「画风与歌词呼应」的第一层证明
    routes.sort(key=lambda r: (-r["lyric_hits"], r["id"]))
    for i, r in enumerate(routes, 1):
        r["rank"] = i
        if not vault_available:
            r["fallback_medium"] = FALLBACK_MEDIUM.get(r["id"], [])
    return routes[:max(1, int(size))]


def apply_route(plan, route):
    """把选定的路线写进导演稿。返回被修改的 plan（原地）。"""
    plan = plan or {}
    segs = plan.get("segments") or []
    per = list(route.get("movement_per_segment") or [])
    if len(per) < len(segs):
        pool = route.get("pool") or ["rimpa"]
        for i in range(len(per), len(segs)):
            per.append(pool[i % len(pool)])
    per = per[:len(segs)]

    ad = plan.setdefault("art_direction", {})
    ad["route_id"] = route["id"]
    ad["route_name"] = route["name"]
    ad["movements"] = sorted(set(per))
    ad["movement_per_segment"] = per
    ad["primary_medium"] = route.get("medium")
    ad["palette"] = route.get("palette")
    ad["why_this_medium"] = route.get("why")
    ad["route_rationale"] = route.get("rationale")
    ad["style_negative"] = route.get("negative")
    ad["vault_available"] = route.get("vault_available")
    for seg, mv in zip(segs, per):
        seg["art_movement"] = mv
    plan["_style_route_applied"] = route["id"]
    return plan


def render_md(routes, chosen_id=None):
    """人读的风格选择菜单 —— 这是要**给用户看、让他挑**的那份。"""
    lines = ["# 画风融合路线 · 请挑一条", ""]
    lines.append(u"> 不是问「你要什么风格」，而是给你 4 条**语法完整**的路线。")
    lines.append(u"> 每条路线都已经包含 ≥3 种画风的递进——因为一条 MV 里"
                 u"人物要在**不同艺术风格环境**下跳舞，风格必须自己会演化。")
    lines.append("")
    lines.append("| # | 路线 | 穿越的画风 | 为什么属于这首歌 |")
    lines.append("|---|------|-----------|------------------|")
    for r in routes:
        mark = u" ← 已选" if chosen_id == r["id"] else ""
        lines.append("| %d | **%s**%s | %s | %s |"
                     % (r["rank"], r["name"], mark,
                        " → ".join(r["movement_per_segment"]),
                        r["rationale"].split(u"。")[0] + u"。"))
    lines.append("")
    for r in routes:
        lines.append("---")
        lines.append("")
        lines.append("## %d. %s　`%s`" % (r["rank"], r["name"], r["id"]))
        lines.append("")
        lines.append(u"**为什么是这条**：%s" % r["why"])
        lines.append("")
        lines.append(u"**适合**：%s" % r["rationale"])
        lines.append("")
        lines.append(u"**媒介**：%s" % r["medium"])
        lines.append("")
        lines.append(u"**色板**：%s" % "　".join(r["palette"]))
        lines.append("")
        lines.append(u"**逐段画风**：")
        lines.append("")
        lines.append("| 段 | 画风 slug |")
        lines.append("|----|-----------|")
        for i, mv in enumerate(r["movement_per_segment"], 1):
            lines.append("| C%d | `%s` |" % (i, mv))
        lines.append("")
        lines.append(u"**负向词**：`%s`" % r["negative"])
        lines.append("")
        if r.get("fallback_medium"):
            lines.append(u"⚠️ art-aesthetic-vault 不可用，已降级到内置媒介池：%s"
                         % "、".join(r["fallback_medium"]))
            lines.append("")
        if r.get("vault_hint"):
            lines.append(u"**取分层提示词**（只在选定这条路线后跑，省时间）：")
            lines.append("")
            lines.append("```bash")
            lines.append(r["vault_hint"][0])
            lines.append("```")
            lines.append("")
    lines.append("---")
    lines.append("")
    lines.append(u"## 怎么选")
    lines.append("")
    lines.append(u"1. 直接回一个编号（1–4）；")
    lines.append(u"2. 或者说「第 2 条的 C1+C3，第 4 条的 C2」——允许按段混搭；")
    lines.append(u"3. 选定后跑：`python3 scripts/prism.py styles --pick <route-id>`")
    lines.append("")
    return "\n".join(lines) + "\n"


def main(argv=None):
    import argparse
    ap = argparse.ArgumentParser(description="生成/应用画风融合路线菜单")
    common.add_common_args(ap)
    ap.add_argument("--size", type=int, default=None)
    ap.add_argument("--segments", type=int, default=None)
    ap.add_argument("--pick", default=None, help="选定路线的 id，写进导演稿")
    ap.add_argument("--plan", default=None)
    ap.add_argument("--md", action="store_true")
    args = ap.parse_args(argv)
    common.apply_common_args(args)

    cfg = common.config()
    size = args.size or int(cfg["style"].get("route_menu_size", 4))
    plan_path = args.plan or os.path.join(common.path("workspace_analysis"),
                                          "director_plan.json")
    plan = common.read_json(plan_path, {}) or {}
    segs = plan.get("segments") or []
    seg_count = args.segments or len(segs) or 1

    import lyricsrc  # noqa: E402
    lines = []
    for s in segs:
        lines.extend(s.get("lyric_lines") or [])
    if not lines:
        for s in segs:
            for t in (s.get("lyrics") or []):
                lines.append({"text": t})

    routes = build_routes(lines, plan.get("meta"), size=size, segments=seg_count)

    if args.pick:
        chosen = None
        for r in routes:
            if r["id"] == args.pick:
                chosen = r
                break
        if chosen is None:
            common.echo(u"找不到路线 %s。可选：%s"
                        % (args.pick, ", ".join(r["id"] for r in routes)))
            return 2
        apply_route(plan, chosen)
        common.write_json(plan_path, plan)
        common.write_text(os.path.join(common.path("output_latest"), "style_routes.md"),
                          render_md(routes, chosen_id=chosen["id"]))
        common.echo(u"已应用路线：%s（%s）" % (chosen["name"], chosen["id"]))
        return 0

    out_md = os.path.join(common.path("output_latest"), "style_routes.md")
    common.write_text(out_md, render_md(routes))
    if args.json:
        common.emit({"routes": routes, "menu": out_md}, True)
    else:
        common.echo(render_md(routes))
    return 0


if __name__ == "__main__":
    sys.exit(main())
