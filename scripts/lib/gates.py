#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""gates —— 交付前的质量闸门（机器可判定的那些）。

设计立场：**没有断言的规则等于没有规则。**
两份母技能加起来有几十条「必须」，但人记不住。能被机器判定的，全部写进这里；
判定不了的（好不好看、隐喻准不准），写进 SKILL.md 的导演自检。

闸门分四组：
  A 时间   段数 / 时长上限 / 连续性 / 吸附
  B 人物   Canon 完整 / 无漂移词 / 每条重申
  C 歌词   背景歌词元素存在 / 可追溯到本段歌词 / 画风按段变化
  D 格式   H3 官方运镜词 / 画风必含词 / 禁用通用词 / 粘贴区零 Markdown / 字数上限

退出码：0 = 全过；1 = 有问题。**未通过不许说 DONE。**
"""

import math
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common  # noqa: E402
import h3render  # noqa: E402
try:
    import chain as chain_mod
except Exception:  # pragma: no cover
    chain_mod = None

RENDER_CORE = ["hair", "eyes", "face", "costume", "accessories", "silhouette"]

# 注意：continuity_from_previous / hook_to_next 不在这里 ——
# 它们有专门的、更可执行的报错信息（见下面「承上 / 启下」两段）。
# 放进通用「缺字段」检查只会产生重复报错。
REQUIRED_SEGMENT_FIELDS = [
    "central_meaning", "character_state", "primary_metaphor", "secondary_motif",
    "background_lyric_elements", "choreography", "environment_system",
    "animation_medium", "art_movement", "style_prompt", "content_prompt",
    "overall_soundscape",
]

CJK_RE = re.compile(u"[\u3400-\u9fff\uf900-\ufaff]")


# ------------------------------------------------------------------ 文本工具
def _has_cjk(text):
    return bool(CJK_RE.search(text or ""))


def _lcs_len(a, b, cap=240):
    """最长公共子串长度（截断到 cap，够用且不炸内存）。"""
    a = a[:cap]
    b = b[:cap]
    if not a or not b:
        return 0
    prev = [0] * (len(b) + 1)
    best = 0
    for i in range(1, len(a) + 1):
        cur = [0] * (len(b) + 1)
        ai = a[i - 1]
        for j in range(1, len(b) + 1):
            if ai == b[j - 1]:
                cur[j] = prev[j - 1] + 1
                if cur[j] > best:
                    best = cur[j]
            else:
                cur[j] = 0
        prev = cur
    return best


def traceable(element, lyric):
    """这个词能不能从这句歌词推出来？"""
    element = (element or "").strip()
    lyric = (lyric or "").strip()
    if not element or not lyric:
        return False
    if element in lyric or lyric in element:
        return True
    if _has_cjk(element) or _has_cjk(lyric):
        return _lcs_len(element, lyric) >= 2
    words = [w for w in re.findall(r"[a-zA-Z]{3,}", element.lower())]
    low = lyric.lower()
    return any(w in low for w in words)


def _is_instrumental(text):
    t = (text or "").strip()
    if not t:
        return True
    return bool(re.match(r"^[（(\[].*[）)\]]$", t))


def _clip(text, n=120):
    t = re.sub(r"\s+", " ", str(text or "")).strip()
    return t if len(t) <= n else t[:n] + "…"


# ------------------------------------------------------------------ 主校验
def validate(plan, prompts_text="", strict=False):
    plan = plan or {}
    cfg = common.config()
    out_cfg = cfg["output"]
    problems, warnings, stats = [], [], {}

    segments = plan.get("segments") or []
    meta = plan.get("meta") or {}
    target = float(meta.get("segment_target_seconds")
                   or cfg["segment"].get("target_seconds", 14.5))
    hard_max = float(cfg["segment"].get("hard_max_seconds", 15.0))
    duration = meta.get("duration")

    # ---------------------------------------------------------- A 时间
    stats["segments"] = len(segments)
    stats["target_seconds"] = target
    if not segments:
        problems.append(u"A 时间：没有任何分段（先跑 scripts/mvstudio.py segments）")
    if duration:
        expect = int(math.ceil(round(float(duration) / target, 9)))
        if len(segments) != expect:
            problems.append(u"A 时间：段数不对 —— 时长 %ss ÷ %.1fs 应该切 %d 段，实际 %d 段"
                            % (duration, target, expect, len(segments)))
    prev_end = None
    for s in segments:
        label = s.get("label") or ("#%s" % s.get("id"))
        start = float(s.get("time_start") or 0)
        end = float(s.get("time_end") or 0)
        length = end - start
        if length > hard_max + 1e-6:
            problems.append(u"A 时间：段 %s 长 %.3fs，超过 MiniMax H3 单条 15 秒硬上限"
                            % (label, length))
        if length <= 0:
            problems.append(u"A 时间：段 %s 长度非正（%.3fs）" % (label, length))
        if prev_end is not None and abs(start - prev_end) > 1e-3:
            problems.append(u"A 时间：段 %s 的起点 %.3f 与上一段终点 %.3f 不连续"
                            % (label, start, prev_end))
        prev_end = end
        if not (s.get("shots") or []):
            problems.append(u"A 时间：段 %s 没有 shots（没有镜头就没有卡点）" % label)

    # ---------------------------------------------------------- B 人物
    canon = plan.get("character_canon") or {}
    for f in RENDER_CORE:
        if not str(canon.get(f) or "").strip():
            problems.append(u"B 人物：character_canon.%s 为空 —— "
                            u"风格可以换世界，但不能换人" % f)
    if not (canon.get("stable_identifiers") or []):
        problems.append(u"B 人物：character_canon.stable_identifiers 为空 —— "
                        u"跨 14.5 秒的条与条之间没有可校验的锚点")

    # ---------------------------------------------------------- C 歌词
    mv_concept = str(plan.get("mv_concept") or "").strip()
    if not mv_concept:
        problems.append(u"C 歌词：mv_concept 为空 —— 没有核心概念就没有视觉母题")
    style_pool = set()
    min_distinct = int(cfg["style"].get("min_distinct_styles", 3))
    for s in segments:
        label = s.get("label") or ("#%s" % s.get("id"))
        for f in REQUIRED_SEGMENT_FIELDS:
            v = s.get(f)
            if v is None or (isinstance(v, str) and not v.strip()) or v == []:
                problems.append(u"C 歌词：段 %s 缺字段 %s" % (label, f))
        els = s.get("background_lyric_elements") or []
        if not els:
            problems.append(u"C 歌词：段 %s 的背景里没有任何歌词元素 —— "
                            u"用户的硬要求是「歌词里的元素要在画面背景里体现」" % label)
        else:
            lyr = s.get("lyrics") or []
            texts = [t for t in lyr if t and not _is_instrumental(t)]
            if texts:
                hit = [e for e in els if any(traceable(e, t) for t in texts)]
                if not hit:
                    problems.append(
                        u"C 歌词：段 %s 的背景歌词元素（%s）无法从本段歌词（%s）推出，"
                        u"属于随机装饰元素，必须删除或换成歌词里的东西"
                        % (label, u"、".join(map(str, els)), u" ／ ".join(texts)))
        mv = s.get("art_movement")
        if mv:
            style_pool.add(mv)
        # 承上 / 启下
        if not str(s.get("continuity_from_previous") or "").strip():
            problems.append(u"C 歌词：段 %s 缺 continuity_from_previous —— "
                            u"整条 MV 要连成一支持续的舞，不是 N 支 14.5 秒的舞" % label)
        if not str(s.get("hook_to_next") or "").strip():
            problems.append(u"C 歌词：段 %s 缺 hook_to_next —— 整条 MV 要连成一支持续的舞，"
                            u"但这一段没有给下一段留动作接口" % label)
        # 每段至少一个运镜 + 动作
        for sh in (s.get("shots") or []):
            if not str(sh.get("action") or "").strip():
                problems.append(u"C 歌词：段 %s 镜头 %s 没有动作"
                                % (label, sh.get("index")))
    stats["distinct_styles"] = len(style_pool)
    style_target = min(min_distinct, max(1, len(segments)))
    if len(style_pool) < style_target:
        problems.append(u"C 歌词：整条 MV 只穿越了 %d 种画风（%s），"
                        u"少于要求的 %d 种 —— 用户要的是人物在**不同艺术风格环境**下跳舞"
                        % (len(style_pool), u"、".join(sorted(style_pool)) or u"无",
                           style_target))

    # 画风必须按段变化（不能每段同一个 slug）
    if len(segments) > 1:
        seq = [s.get("art_movement") for s in segments]
        if len(set(seq)) == 1 and seq[0]:
            problems.append(u"C 歌词：所有段都用同一画风 `%s` —— 画风没有演化" % seq[0])

    # ---------------------------------------------------------- D 格式
    required_words = [w.lower() for w in out_cfg["style_required_words"]]
    forbidden = [w.lower() for w in out_cfg["style_forbidden"]]
    drift = [w.lower() for w in out_cfg["drift_forbidden_in_body"]]
    for s in segments:
        label = s.get("label") or ("#%s" % s.get("id"))
        sp = s.get("style_prompt") or ""
        low = sp.lower()
        for w in required_words:
            if w not in low:
                problems.append(u"D 格式：段 %s 的 style_prompt 缺必含词 '%s'"
                                % (label, w))
        for w in forbidden:
            if w in low:
                problems.append(u"D 格式：段 %s 的 style_prompt 出现被禁的通用元素 '%s'"
                                % (label, w))
        for sh in (s.get("shots") or []):
            cam = sh.get("camera")
            if not cam:
                problems.append(u"D 格式：段 %s 镜头 %s 没写运镜"
                                % (label, sh.get("index")))
            elif cam not in h3render.CAMERA_SURFACE:
                problems.append(u"D 格式：段 %s 镜头 %s 的运镜 '%s' 不在 MiniMax H3 "
                                u"官方词表里（不得自造）"
                                % (label, sh.get("index"), cam))
            amp = sh.get("camera_amplitude")
            speed = sh.get("camera_speed")
            allowed_amp = out_cfg["camera_amplitude"] + ["", None]
            allowed_speed = out_cfg["camera_speed"] + ["", None]
            if amp not in allowed_amp:
                problems.append(u"D 格式：段 %s 镜头 %s 的幅度 '%s' 不是官方写法"
                                % (label, sh.get("index"), amp))
            if speed not in allowed_speed:
                problems.append(u"D 格式：段 %s 镜头 %s 的速度 '%s' 不是官方写法"
                                % (label, sh.get("index"), speed))

    # ---------------------------------------------------------- 粘贴区
    blocks = extract_paste_blocks(prompts_text)
    stats["paste_blocks"] = len(blocks)
    if blocks:
        joined = "\n".join(blocks)
        if "**" in joined:
            problems.append(u"D 格式：粘贴区里出现了 Markdown 加粗（**）—— "
                            u"模型会把注记当成画面要求")
        max_chars = int(out_cfg.get("prompt_max_chars", 7000))
        for i, b in enumerate(blocks, 1):
            if len(b) > max_chars:
                problems.append(u"D 格式：第 %d 条粘贴区 %d 字符，超过官方上限 %d"
                                % (i, len(b), max_chars))
        n_nda = joined.count("non_diegetic_music: N/A")
        if n_nda != len(blocks):
            problems.append(u"D 格式：non_diegetic_music: N/A 出现 %d 次，"
                            u"应恰好每条一次（音乐由原曲 1:1 复用）" % n_nda)
        low_joined = joined.lower()
        for w in drift:
            if w in low_joined:
                problems.append(u"B 人物：粘贴区出现人物漂移词 '%s'" % w)
        invented = h3render.invented_camera_in(joined)
        if invented:
            problems.append(u"D 格式：粘贴区出现自造/3D 运镜词 %s" % invented)
        for w in forbidden:
            if w in low_joined:
                problems.append(u"D 格式：粘贴区出现被禁的通用元素 '%s'" % w)
        for phrase in out_cfg["canon_required_phrases"]:
            if phrase.lower() not in low_joined:
                problems.append(u"B 人物：粘贴区缺少人物一致性声明 '%s'" % phrase)
        if "fully_copy" not in joined:
            problems.append(u"D 格式：没有声明原曲 1:1 复用（<Audio N>: fully_copy）")
        # 空段落
        if re.search(r":\s*\n\s*\n", joined):
            warnings.append(u"D 格式：粘贴区有空的格式段落")

        # ---- mv 路线：用户指定的六段结构必须齐全且有序 ----
        mv_sections = ([u"人物与参考保持一致性", u"风格提示词", u"内容提示词"]
                       + h3render.MV_TAIL_FIELDS)
        # 判据优先看 plan 的路线，而不是块里的字样 ——
        # 否则「内容提示词被整段删掉」时反而检测不到它是 mv 块。
        plan_route = (meta.get("h3_route") or "").strip()
        for i, b in enumerate(blocks, 1):
            is_mv = (plan_route == "mv") or (u"内容提示词" in b) \
                or ("content_prompt:" in b)
            if not is_mv:
                continue
            pos = []
            for k in mv_sections:
                if k not in b:
                    problems.append(u"D 格式：第 %d 条缺少结构段「%s」——"
                                    u"每条提示词必须是固定六段" % (i, k))
                else:
                    pos.append(b.index(k))
            if len(pos) == len(mv_sections) and pos != sorted(pos):
                problems.append(u"D 格式：第 %d 条的六段顺序不对" % i)

        # ---- 用户已上传原曲：全文禁止出现生成音乐的要求 ----
        for i, b in enumerate(blocks, 1):
            low = b.lower()
            for bad in h3render.MUSIC_GEN_FORBIDDEN:
                if bad.lower() in low:
                    problems.append(u"D 格式：第 %d 条出现生成音乐的要求「%s」——"
                                    u"音轨是用户已上传的原曲，1:1 复用，"
                                    u"提示词里不得要求模型生成音乐" % (i, bad))

        # ---- 续接段必须写明「延续上一帧」 ----
        segs = plan.get("segments") or []
        for i, (seg, b) in enumerate(zip(segs, blocks), 1):
            ch = seg.get("chain")
            if not ch or not ch.get("declared"):
                continue
            if (u"延续上一帧" not in b) and \
                    ("CONTINUES FROM THE PREVIOUS LAST FRAME" not in b):
                problems.append(u"C 歌词：第 %d 条（%s）接了上一段尾帧，"
                                u"但【内容提示词】里没有写「延续上一帧」"
                                % (i, seg.get("label")))

        # 英文路线下正文必须英文（官方 O13）。
        # 逐字引用的歌词／画面文字，以及背景实物名，**按官方规则保留原语言**，
        # 所以先把双引号内的内容摘掉，再看还剩没有整句中文。
        if (meta.get("lang") or "en") == "en":
            for i, b in enumerate(blocks, 1):
                stripped = re.sub(r'"[^"]*"', " ", b)
                runs = re.findall(u"[\u4e00-\u9fff]{4,}", stripped)
                if runs:
                    warnings.append(
                        u"D 格式：第 %d 条粘贴区是英文路线，但正文里夹了整句中文"
                        u"（%s…）——创作字段（environment_system / overall_soundscape / "
                        u"content_prompt / action）必须用**目标语言**写；"
                        u"只有逐字引用的歌词与背景实物名保留原语言"
                        % (i, runs[0][:12]))

    # ---------------------------------------------------------- 收尾效果
    # 只在 mv 路线强制：其它路线是格式保真用途，不强制创作决策
    if (meta.get("h3_route") or "").strip() == "mv":
        end = plan.get("ending") or {}
        if not end.get("id"):
            problems.append(u"C 歌词：还没有选收尾效果 —— 全片结束不一定要站定，"
                            u"请让用户从 endings 菜单里挑一个"
                            u"（python3 scripts/mvstudio.py endings）")
        elif blocks:
            last = blocks[-1]
            probe = (end.get("prompt_zh") or end.get("prompt_en") or "")[:12]
            if probe and probe not in last:
                problems.append(u"C 歌词：末段【内容提示词】没有带上选定的收尾效果"
                                u"「%s」" % end.get("id"))
        elif segments and not (any((s.get("shots") or []) for s in segments[-1:])):
            warnings.append(u"末段没有镜头，无法承载收尾效果")

    # ---------------------------------------------------------- 尾帧续接链
    if chain_mod is not None and segments:
        try:
            cprob, cwarn = chain_mod.validate_chain(plan)
            problems.extend(cprob)
            warnings.extend(cwarn)
        except Exception as exc:
            warnings.append(u"尾帧续接链检查失败：%s" % exc)

    # ---------------------------------------------------------- 统计
    stats["lyric_lines"] = sum(len([t for t in (s.get("lyrics") or [])
                                    if not _is_instrumental(t)]) for s in segments)
    stats["background_elements"] = sum(len(s.get("background_lyric_elements") or [])
                                       for s in segments)
    stats["shots"] = sum(len(s.get("shots") or []) for s in segments)
    cams = {}
    for s in segments:
        for sh in (s.get("shots") or []):
            cams[sh.get("camera")] = cams.get(sh.get("camera"), 0) + 1
    stats["camera_usage"] = cams
    stats["styles"] = sorted(style_pool)
    if stats["shots"]:
        stats["avg_shot_seconds"] = round(
            sum(float(s.get("time_end", 0)) - float(s.get("time_start", 0))
                for s in segments) / stats["shots"], 3)

    return {"passed": not problems, "problems": problems, "warnings": warnings,
            "stats": stats}


PASTE_RE = re.compile(r"```text\s*\n(.*?)```", re.S)


def extract_paste_blocks(prompts_text):
    """从交付文档里抠出**真正要粘贴**的块（```text ... ```）。"""
    if not prompts_text:
        return []
    return [m.group(1).strip() for m in PASTE_RE.finditer(prompts_text)]


def render_md(result):
    lines = [u"# 交付校验报告", ""]
    lines.append(u"## 结论：%s" % (u"✅ 通过" if result["passed"] else u"❌ 未通过"))
    lines.append("")
    st = result.get("stats") or {}
    lines.append(u"## 统计")
    lines.append("")
    for k in ("segments", "shots", "avg_shot_seconds", "distinct_styles", "styles",
              "lyric_lines", "background_elements", "paste_blocks"):
        if k in st:
            v = st[k]
            lines.append(u"- %s：%s" % (k, u"、".join(v) if isinstance(v, list) else v))
    lines.append("")
    if result["problems"]:
        lines.append(u"## 必须修（%d）" % len(result["problems"]))
        lines.append("")
        for p in result["problems"]:
            lines.append(u"- [ ] %s" % p)
        lines.append("")
    if result["warnings"]:
        lines.append(u"## 提醒（%d）" % len(result["warnings"]))
        lines.append("")
        for w in result["warnings"]:
            lines.append(u"- %s" % w)
        lines.append("")
    if result["passed"]:
        lines.append(u"> 全部闸门通过。可以交付。")
        lines.append("")
    return "\n".join(lines) + "\n"


def main(argv=None):
    import argparse
    ap = argparse.ArgumentParser(description="交付校验")
    common.add_common_args(ap)
    ap.add_argument("--plan", default=None)
    ap.add_argument("--prompts", default=None)
    args = ap.parse_args(argv)
    common.apply_common_args(args)

    plan_path = args.plan or os.path.join(common.path("workspace_analysis"),
                                          "director_plan.json")
    plan = common.read_json(plan_path, {}) or {}
    prompts_path = args.prompts or os.path.join(common.path("output_latest"),
                                                "minimax_h3_prompts.md")
    text = common.read_text(prompts_path) if os.path.isfile(prompts_path) else ""
    result = validate(plan, text)
    out = os.path.join(common.path("output_latest"), "validation.md")
    common.write_text(out, render_md(result))
    if args.json:
        common.emit(result, True)
    else:
        common.echo(render_md(result))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
