#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""h3render —— 把导演稿渲染成 MiniMax H3 的**原生**格式。

这一层是两份母技能里冲突最大的地方，融合后的裁决如下（不是折中，是有依据的）：

  冲突：母技能 A 说「每条 prompt 必须逐字重申完整 Character Canon」；
        母技能 B 说「绝不描述人物外观，只写素材职责，否则文字与参考图打架」。

  裁决：**两条都对，只是位置不同。** H3 全参考模式（Ref2VA）本来就有两个
        专门放参考信息的段落——`subject_definitions` 与 `retention_analysis`。
        Canon 写在那里，占用的是**官方为它准备的槽位**；
        而 `detailed_description`（正文）里就不再复述外观。
        这样既满足「逐字重申」，又不产生文字与图片互相打架。

  依据：MiniMax-AI/MiniMax-H3 官方 `ref-en.txt`：
        「If an image is used only to define a character, scene, costume, or style,
          do not create a standalone picture entry. Instead, cite the image source
          inside the corresponding <Subject N> definition.」

三条路线：
  ref  —— Ref2VA 全参考模式（默认；人物图 + 三视图 + 原曲 1:1）
  i2va —— 以人物图为第一帧
  t2va —— 纯文字（不传参考图时才用；人物一致性最弱，明确降级）

输出语言：en（官方要求正文英文，默认）/ zh（H3 官网路线用中文自然语言）。
**两种不能混着粘贴**——H3 前面有 Context-IR 做理解与改写，混用会打架。
"""

import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common  # noqa: E402
try:
    import endings as endings_mod
except Exception:  # pragma: no cover
    endings_mod = None
try:
    import camera as camera_mod
except Exception:  # pragma: no cover
    camera_mod = None
try:
    import motion as motion_mod
except Exception:  # pragma: no cover
    motion_mod = None

RENDER_CORE = ["hair", "eyes", "face", "costume", "accessories", "silhouette"]

REQUIRED_SEGMENT_FIELDS = [
    "central_meaning", "character_state", "primary_metaphor", "secondary_motif",
    "background_lyric_elements", "choreography", "environment_system",
    "animation_medium", "art_movement", "style_prompt", "content_prompt",
    "overall_soundscape", "continuity_from_previous", "hook_to_next",
]

# ------------------------------------------------------------------ 官方运镜词表
CAMERA_SURFACE = {
    "Zoom In": [r"\bzoom(?:s|ing)? in\b"],
    "Zoom Out": [r"\bzoom(?:s|ing)? out\b"],
    "Push In": [r"\bpush(?:es|ing)? in\b"],
    "Pull Out": [r"\bpull(?:s|ing)? out\b"],
    "Pan Left": [r"\bpan(?:s|ning)? (?:to the )?left\b"],
    "Pan Right": [r"\bpan(?:s|ning)? (?:to the )?right\b"],
    "Truck Left": [r"\btruck(?:s|ing)? (?:to the )?left\b"],
    "Truck Right": [r"\btruck(?:s|ing)? (?:to the )?right\b"],
    "Tilt Up": [r"\btilt(?:s|ing)? up\b"],
    "Tilt Down": [r"\btilt(?:s|ing)? down\b"],
    "Pedestal Up": [r"\bpedestal(?:s|ing)? up\b"],
    "Pedestal Down": [r"\bpedestal(?:s|ing)? down\b"],
    "Arc Shot": [r"\barc shot\b", r"\barc(?:s|ing)? around\b"],
    "Tracking Shot": [r"\btracking shot\b", r"\btrack(?:s|ing)? (?:her|him|the subject)\b"],
    "Static Shot": [r"\bstatic shot\b", r"\bholds? (?:a )?static\b", r"\bstatic camera\b"],
    "Shake Slightly": [r"\bshake(?:s)? slightly\b"],
    "Shake Strongly": [r"\bshake(?:s)? strongly\b"],
    "POV": [r"\bpov\b", r"\bpoint of view\b"],
    "Roll Clockwise": [r"\broll(?:s|ing)? clockwise\b"],
    "Roll Counterclockwise": [r"\broll(?:s|ing)? (?:counterclockwise|counter-clockwise|anticlockwise)\b"],
}

# 自造词 / 3D 运镜：出现即校验失败
INVENTED_CAMERA = [
    "graphic push-in", "graphic push in", "snap zoom", "canvas rotation",
    "dolly", "dolly zoom", "3d orbit", "360 camera", "drone", "fpv",
    "fly-through", "spiraling camera", "spiral camera", "orbit shot",
]

_NATURAL = {
    "Push In": "pushes in", "Pull Out": "pulls out", "Zoom In": "zooms in",
    "Zoom Out": "zooms out", "Pan Left": "pans left", "Pan Right": "pans right",
    "Truck Left": "trucks left", "Truck Right": "trucks right",
    "Tilt Up": "tilts up", "Tilt Down": "tilts down",
    "Pedestal Up": "pedestals up", "Pedestal Down": "pedestals down",
    "Arc Shot": "arcs around her", "Tracking Shot": "tracks her",
    "Roll Clockwise": "rolls clockwise",
    "Roll Counterclockwise": "rolls counterclockwise",
    "Shake Slightly": "shakes slightly", "Shake Strongly": "shakes strongly",
}


def camera_terms_in(text):
    """文本里实际用到的**官方**运镜词（按官方词表归一化）。"""
    low = (text or "").lower()
    found = []
    for term, pats in CAMERA_SURFACE.items():
        for p in pats:
            if re.search(p, low):
                found.append(term)
                break
    return found


def invented_camera_in(text):
    low = (text or "").lower()
    return [w for w in INVENTED_CAMERA if w in low]


# ------------------------------------------------------------------ 就绪闸门
def check_ready(plan):
    """缺东西就拒绝渲染（绝不替导演瞎编）。返回缺失项列表。"""
    problems = []
    plan = plan or {}
    if plan.get("_draft"):
        problems.append(u"导演稿还是草稿（_draft=true）："
                        u"必须先填 mv_concept / lyric_semantic_map / 逐段创意字段")
    if not str(plan.get("mv_concept") or "").strip():
        problems.append("mv_concept（一句话核心概念）为空")
    canon = plan.get("character_canon") or {}
    if not (canon.get("stable_identifiers") or []):
        problems.append("character_canon.stable_identifiers 为空（跨条唯一锚点）")
    for f in RENDER_CORE:
        if not str(canon.get(f) or "").strip():
            problems.append("character_canon.%s 为空（每条 prompt 都要重申）" % f)
    ad = plan.get("art_direction") or {}
    if not (ad.get("movement_per_segment") or []):
        problems.append("art_direction.movement_per_segment 为空：先跑 scripts/mvstudio.py styles --pick <id>")
    segs = plan.get("segments") or []
    if not segs:
        problems.append("segments 为空：先跑 scripts/mvstudio.py segments")
    cfg = common.config()
    required_words = [w.lower() for w in cfg["output"]["style_required_words"]]
    for seg in segs:
        for f in REQUIRED_SEGMENT_FIELDS:
            val = seg.get(f)
            if val is None or (isinstance(val, str) and not val.strip()) or val == []:
                problems.append("段 %s 缺字段 %s" % (seg.get("label", seg.get("id")), f))
        if not (seg.get("shots") or []):
            problems.append("段 %s 没有 shots（没有镜头就没有运镜与卡点）"
                            % seg.get("label", seg.get("id")))
        sp = (seg.get("style_prompt") or "").lower()
        for w in required_words:
            if w not in sp:
                problems.append("段 %s 的 style_prompt 缺必含词 '%s'"
                                % (seg.get("label", seg.get("id")), w))
    for s in segs:
        for sh in (s.get("shots") or []):
            cam = sh.get("camera")
            if cam and cam not in CAMERA_SURFACE:
                problems.append("段 %s 镜头 %s 的运镜 '%s' 不在 MiniMax H3 官方词表里"
                                % (s.get("label"), sh.get("index"), cam))
            # 草稿占位符绝不能进提示词 —— 模型会把「（草稿：…）」当成画面要求
            for fld in ("action", "purpose"):
                if u"（草稿" in str(sh.get(fld) or ""):
                    problems.append(
                        u"段 %s 镜头 %s 的 %s 还是草稿占位符 —— "
                        u"填成真正的内容再渲染（草稿标记会进提示词）"
                        % (s.get("label"), sh.get("index"), fld))
    return problems


# ------------------------------------------------------------------ 素材
def _assets(plan):
    a = plan.get("assets") or {}
    ch = a.get("character_reference") or {}
    tv = a.get("turnaround_sheet") or {}
    au = a.get("audio") or {}
    return {
        "char_path": ch.get("path"),
        "char_label": ch.get("label") or "<Picture 1>",
        "turn_path": tv.get("path"),
        "turn_label": tv.get("label") or "<Picture 2>",
        "audio_label": au.get("label") or "<Audio 1>",
        "audio_path": au.get("path"),
        "has_turn": bool(tv.get("path")),
    }


def _canon_clause(canon, lang="en"):
    """把 canon 写成一句话（放在官方为参考信息准备的槽位里）。"""
    canon = canon or {}
    name = canon.get("name") or "the character"
    if lang == "zh":
        parts = [u"%s：%s" % (k, canon[k]) for k in RENDER_CORE if canon.get(k)]
        ids = canon.get("stable_identifiers") or []
        s = u"%s——%s。" % (name, u"；".join(parts))
        if ids:
            s += u"绝不可变的识别物：%s。" % u"、".join(ids)
        return s
    parts = [str(canon[k]).strip().rstrip(".") for k in RENDER_CORE if canon.get(k)]
    s = "%s has %s." % (name if name.startswith("<") else name, "; ".join(parts))
    ids = canon.get("stable_identifiers") or []
    if ids:
        s += " Stable identifiers that must never change: %s." % ", ".join(ids)
    return s


def _style_sentence(plan, seg):
    ad = plan.get("art_direction") or {}
    medium = ad.get("primary_medium") or "2D limited animation"
    mv = seg.get("art_movement") or ""
    anim = seg.get("animation_medium") or "limited animation on twos with held frames"
    world = ("The world is drawn in %s%s."
             % (medium, (", movement reference: %s" % mv) if mv else ""))
    return ("2D limited animation, hand-drawn, flat composition. %s %s "
            "The camera never leaves flat two-dimensional space."
            % (world, _sentence(anim)))


def _lyric_line(seg, index):
    lines = seg.get("lyric_lines") or []
    if index < len(lines):
        return lines[index].get("text") or ""
    lyrics = seg.get("lyrics") or []
    return lyrics[0] if lyrics else ""


def _cap(text):
    t = (text or "").strip()
    if not t:
        return t
    return t[0].upper() + t[1:]


def _sentence(text):
    t = (text or "").strip()
    if not t:
        return ""
    if t[-1] not in ".!?":
        t += "."
    return _cap(t)


def _bg_clause(plan, seg, shot):
    """背景里的歌词元素 —— 用户的硬要求：歌词元素必须在画面背景里体现。"""
    els = seg.get("background_lyric_elements") or []
    env = seg.get("environment_system") or ""
    pieces = []
    if els:
        pieces.append("behind her the flat printed background is built out of the "
                      "lyric's own objects: %s" % ", ".join(els))
    if env:
        pieces.append(env)
    cfg = common.config()
    if cfg["output"].get("lyric_typography", True):
        line = shot.get("lyric") or _lyric_line(seg, 0)
        if line and not _is_instrumental(line):
            pieces.append("the lyric line \"%s\" is printed on the background plane as "
                          "hard-edged flat typography" % line)
    return " ".join(_sentence(p) for p in pieces if p.strip())


def _is_instrumental(text):
    t = (text or "").strip()
    if not t:
        return True
    return bool(re.match(r"^[（(\[].*[）)\]]$", t))


def _camera_sentence(shot):
    cam = shot.get("camera") or "Static Shot"
    amp = (shot.get("camera_amplitude") or "").strip()
    speed = (shot.get("camera_speed") or "").strip()
    target = (shot.get("camera_target") or "").strip()
    if cam == "Static Shot":
        return "The camera holds a Static Shot."
    if cam == "POV":
        return "The camera switches to POV."
    verb = _NATURAL.get(cam, cam.lower())
    bits = [b for b in (amp, speed) if b]
    tail = (" " + " ".join(bits)) if bits else ""
    toward = (" toward %s" % target) if target else ""
    return "The camera %s%s%s." % (verb, tail, toward)


def _cut_sentence(shot, is_last, seg):
    cut = (shot.get("cut") or "").strip().lower()
    if is_last:
        hook = seg.get("hook_to_next") or ""
        return ("Final state: %s" % hook) if hook else "Final state: a held cel."
    if cut in ("none", "continuous", "no cut"):
        return "The shot does not cut; the action continues into the next shot."
    return "The shot cuts to the next."


def _shot_body(plan, seg, shot, index, total):
    size = shot.get("shot_size") or ("medium shot" if index == 1 else "close-up")
    action = _sentence(shot.get("action") or "")
    bg = _bg_clause(plan, seg, shot)
    is_last = (index == total)
    tail = ""
    if is_last and seg.get("is_tail_pad"):
        tail = (" After the music ends there is no further sound: hold frame, visual "
                "decay, slow animation, paper texture, final held cel. Do not create "
                "any new music and do not add any beat.")
    if index > 1:
        t = float(shot.get("start") or 0.0)
        head = ("[Shot %d] At %02d:%06.3f, the camera cuts to a %s. %s"
                % (index, int(t // 60), t % 60, size, action))
    else:
        head = "[Shot 1] A %s frames her. %s" % (size, action)
    parts = [head, bg, _camera_sentence(shot), _cut_sentence(shot, is_last, seg) + tail]
    return re.sub(r"\s+", " ", " ".join(p for p in parts if p)).strip()


# ------------------------------------------------------------------ 渲染：ref
def render_ref2va(plan, seg, lang="en"):
    a = _assets(plan)
    canon = plan.get("character_canon") or {}
    meta = plan.get("meta") or {}
    segs = plan.get("segments") or []
    total_sec = float(meta.get("duration") or (segs[-1]["time_end"] if segs else 0) or 0)
    shots = seg.get("shots") or []
    dur = float(seg.get("prompt_seconds")
                or (seg.get("time_end", 0) - seg.get("time_start", 0)) or 0)
    if seg.get("is_tail_pad"):
        dur = float(seg.get("target_seconds") or dur)

    if lang == "zh":
        return _render_ref2va_zh(plan, seg, a, canon, shots, dur)

    # --- subject_definitions（官方：图只定义角色时，引在 Subject 里，不单开 Picture 条目）
    subj = ["<Subject 1> is the only character in the target video. "
            "Her appearance is defined by %s (character reference) and %s "
            "(character turnaround reference: front, three-quarter, side and back "
            "views of the same character). %s "
            "The higher authority for her face and colour is %s; the higher authority "
            "for her silhouette, side profile and back view is %s. "
            "No other character appears at any time, and her design is never altered."
            % (a["char_label"], a["turn_label"], _canon_clause(canon, "en"),
               a["char_label"], a["turn_label"])]
    if not a["has_turn"]:
        subj.append("Note: no turnaround sheet is supplied; %s alone defines her, "
                    "so keep her silhouette strictly consistent with it."
                    % a["char_label"])

    # --- summary
    task = "[reference generation + audio reuse]"
    style_word = (plan.get("art_direction") or {}).get("primary_medium") or "2D animation"
    pictures = ("%s and %s provide her appearance" % (a["char_label"], a["turn_label"])
                if a["has_turn"] else "%s provides her appearance" % a["char_label"])
    summary = ("%s The target video is one %0.1f-second segment of a hand-drawn 2D "
               "music video, drawn in %s. %s dances continuously while the world "
               "around her is redrawn in a different 2D art language; only the world "
               "mutates, never her identity. %s, and %s provides the complete "
               "soundtrack."
               % (task, dur, style_word,
                  (canon.get("name") or "The character"), pictures, a["audio_label"]))

    # --- retention_analysis
    shot_refs = ", ".join("[Shot %d]" % (s.get("index") or i)
                          for i, s in enumerate(shots, 1)) or "[Shot 1]"
    ret = ["<Subject 1> (appears in %s): fully_preserved - her face, feature "
           "proportions, eye shape and iris colour, hairstyle, hair colour, apparent "
           "age, body proportion, costume structure and signature accessories are "
           "identical in every shot. What changes by design is the drawing medium, "
           "the line quality, the palette and the background system." % shot_refs,
           "%s: fully_copy - %s is reused 1:1 as the target video's complete final "
           "audio track. Do not generate, replace, re-perform or re-describe any "
           "music." % (a["audio_label"], a["audio_label"])]

    # --- detailed_description
    body = [_style_sentence(plan, seg)]
    for i, sh in enumerate(shots, 1):
        body.append(_shot_body(plan, seg, sh, i, len(shots)))
    if seg.get("is_tail_pad"):
        body.append("The reference audio ends before this segment ends; the remaining "
                    "time is held frame, visual decay and paper texture only, with no "
                    "new sound and no new beat.")

    soundscape = seg.get("overall_soundscape") or "Room tone and the soft movement of fabric."

    text = "\n".join([
        "subject_definitions:",
        " ".join(subj),
        "",
        "summary:",
        summary,
        "",
        "retention_analysis:",
        "\n".join(ret),
        "",
        "detailed_description:",
        " ".join(body),
        "",
        "overall_soundscape:",
        soundscape,
        "",
        "non_diegetic_music: N/A",
    ])
    return text


def _render_ref2va_zh(plan, seg, a, canon, shots, dur):
    subj = [u"<Subject 1> 是本片唯一的角色。她的形象由 %s（人物参考图）与 %s"
            u"（人物三视图：正面、四分之三侧面、正侧面、背面）共同定义。%s "
            u"%s 是脸部与色彩的最高依据，%s 是轮廓、侧面与背面的最高依据。"
            u"全片不出现第二个角色，她的设计在任何时刻都不被改写。"
            % (a["char_label"], a["turn_label"], _canon_clause(canon, "zh"),
               a["char_label"], a["turn_label"])]
    medium = (plan.get("art_direction") or {}).get("primary_medium") or u"二维动画"
    summary = (u"[reference generation + audio reuse] 本片是一条手绘二维音乐影像的"
               u"第 %s 段，长度 %.1f 秒，画法为 %s。%s 持续跳舞，"
               u"她周围的世界被不断重画成另一种二维艺术语言——"
               u"变化的只有世界，不是她的身份。%s 提供人物形象，%s 提供完整配乐。"
               % (seg.get("label"), dur, medium,
                  canon.get("name") or u"人物", a["char_label"], a["turn_label"]))
    shot_refs = u"、".join(u"[Shot %d]" % (s.get("index") or i)
                           for i, s in enumerate(shots, 1)) or u"[Shot 1]"
    ret = [u"<Subject 1>（出现在 %s）：fully_preserved —— 脸、五官比例、眼型与瞳色、"
           u"发型、发色、年龄感、身体比例、服装结构与核心配饰在每一个镜头里完全一致。"
           u"按设计改变的只有绘画媒介、线条质感、色板与背景系统。" % shot_refs,
           u"%s：fully_copy —— %s 被 1:1 复用为本片完整的最终音轨。"
           u"不要生成、替换、重唱或重新描述任何音乐。" % (a["audio_label"], a["audio_label"])]
    body = [u"二维 limited animation、手绘、平面构图。世界用 %s 绘制；%s。"
            u"摄影机全程不离开平面二维空间。"
            % (medium, seg.get("animation_medium") or u"on twos 抽帧")]
    for i, sh in enumerate(shots, 1):
        line = sh.get("lyric") or _lyric_line(seg, 0)
        els = u"、".join(seg.get("background_lyric_elements") or [])
        seg_txt = u"[Shot %d]" % i
        if i > 1:
            t = float(sh.get("start") or 0.0)
            seg_txt += u" 在 %02d:%06.3f 切到" % (int(t // 60), t % 60)
        seg_txt += (u" 一个%s。%s 背景是平面的，由 %s 构成；"
                    u"歌词「%s」以硬边平面字体印在背景平面上。%s"
                    % (sh.get("shot_size") or u"中景",
                       (sh.get("action") or u"她持续跳舞") + u"。",
                       els or u"平面图形", line or u"（器乐）",
                       _camera_sentence_zh(sh)))
        body.append(seg_txt)
    return "\n".join([
        "subject_definitions:", u" ".join(subj), "",
        "summary:", summary, "",
        "retention_analysis:", u"\n".join(ret), "",
        "detailed_description:", u" ".join(body), "",
        "overall_soundscape:", seg.get("overall_soundscape") or u"环境音与衣料摩擦声。", "",
        "non_diegetic_music: N/A",
    ])


def _camera_sentence_zh(shot):
    cam = shot.get("camera") or "Static Shot"
    amp = (shot.get("camera_amplitude") or "").strip()
    speed = (shot.get("camera_speed") or "").strip()
    zh = {
        "Static Shot": u"摄影机保持固定（Static Shot）",
        "Push In": u"摄影机推进（Push In）",
        "Pull Out": u"摄影机拉远（Pull Out）",
        "Zoom In": u"变焦推近（Zoom In）",
        "Zoom Out": u"变焦拉远（Zoom Out）",
        "Pan Left": u"摄影机向左摇（Pan Left）",
        "Pan Right": u"摄影机向右摇（Pan Right）",
        "Truck Left": u"机位向左平移（Truck Left）",
        "Truck Right": u"机位向右平移（Truck Right）",
        "Tilt Up": u"镜头上摇（Tilt Up）",
        "Tilt Down": u"镜头下摇（Tilt Down）",
        "Pedestal Up": u"整个机位上升（Pedestal Up）",
        "Pedestal Down": u"整个机位下降（Pedestal Down）",
        "Arc Shot": u"摄影机绕她弧线移动（Arc Shot）",
        "Tracking Shot": u"摄影机跟拍她（Tracking Shot）",
        "Roll Clockwise": u"画面顺时针翻滚（Roll Clockwise）",
        "Roll Counterclockwise": u"画面逆时针翻滚（Roll Counterclockwise）",
        "Shake Slightly": u"画面轻微抖动（Shake Slightly）",
        "Shake Strongly": u"画面强烈抖动（Shake Strongly）",
        "POV": u"主观视角（POV）",
    }.get(cam, cam)
    bits = [b for b in (amp, speed) if b]
    return zh + (u"，" + u"、".join(bits) if bits else u"") + u"。"


# ------------------------------------------------------------------ 渲染：i2va / t2va
I2VA_FIRST_LINE = ("For the target video, at 0.00 seconds into the target video, "
                   "<Picture 1> (from [Shot 1]) is fully referenced.")


def render_i2va(plan, seg, lang="en"):
    a = _assets(plan)
    canon = plan.get("character_canon") or {}
    shots = seg.get("shots") or []
    body = [_style_sentence(plan, seg),
            "%s This is the same character as in %s." % (_canon_clause(canon, "en"),
                                                         a["char_label"])]
    for i, sh in enumerate(shots, 1):
        body.append(_shot_body(plan, seg, sh, i, len(shots)))
    soundscape = seg.get("overall_soundscape") or "Room tone and the soft movement of fabric."
    return "\n".join([
        I2VA_FIRST_LINE,
        "",
        "integrated_multimodal_description: " + " ".join(body),
        "",
        "overall_soundscape: " + soundscape,
        "",
        "non_diegetic_music: N/A",
    ])


def render_t2va(plan, seg, lang="en"):
    canon = plan.get("character_canon") or {}
    shots = seg.get("shots") or []
    body = [_style_sentence(plan, seg), _canon_clause(canon, "en")]
    for i, sh in enumerate(shots, 1):
        body.append(_shot_body(plan, seg, sh, i, len(shots)))
    soundscape = seg.get("overall_soundscape") or "Room tone and the soft movement of fabric."
    return "\n".join([
        "integrated_multimodal_description: " + " ".join(body),
        "",
        "overall_soundscape: " + soundscape,
        "",
        "non_diegetic_music: N/A",
    ])


_ROUTES = {"ref": render_ref2va, "i2va": render_i2va, "t2va": render_t2va}


# ------------------------------------------------------------------ 渲染：mv（用户指定结构）
# 用户指定的每条提示词结构（顺序固定）：
#   人物与参考保持一致性 / 风格提示词 / 内容提示词 /
#   integrated_multimodal_description / overall_soundscape / non_diegetic_music
#
# 且：第一条出片后取尾帧 → 下一条在【内容提示词】里写「延续上一帧」，
# 并把那张图作为**首帧参考**放进提示词。
# 用户已上传原曲 → 全文**不许**出现生成音乐/配乐的要求。
MV_SECTIONS_ZH = [u"人物与参考保持一致性", u"风格提示词", u"内容提示词"]
MV_SECTIONS_EN = ["character_and_reference_consistency", "style_prompt",
                  "content_prompt"]
MV_TAIL_FIELDS = ["integrated_multimodal_description", "overall_soundscape",
                  "non_diegetic_music"]

# 生成音乐的措辞一律禁止（用户自己传原曲）
MUSIC_GEN_FORBIDDEN = [
    u"生成配乐", u"生成音乐", u"创作配乐", u"作曲", u"添加背景音乐", u"配上音乐",
    "generate music", "compose a soundtrack", "add background music",
    "create music", "generate a soundtrack",
]

_CANON_DRIFT_ZH = (u"不得换脸、不得换发型、不得换发色、不得换服装结构、"
                   u"不得删除核心配饰、不得身份漂移、不得写实化重绘、"
                   u"不得出现第二个角色。风格只改世界，不改人。")


def _chain_of(seg):
    return seg.get("chain") or None


def _chain_frame_label(seg):
    ch = _chain_of(seg)
    return (ch.get("label") if ch else None) or None


def _chain_block(seg):
    """有尾帧时：首帧对齐指令（官方 I2VA 硬要求，必须是第一行）。"""
    label = _chain_frame_label(seg)
    if not label:
        return ""
    return ("For the target video, at 0.00 seconds into the target video, "
            "%s (from [Shot 1]) is fully referenced." % label)


def _mv_declaration_line(plan, seg, a):
    """一行紧凑的**官方参考声明**（`<Subject N>` / `<Picture N>` / `<Audio N>`）。

    为什么在中文结构里还要留这一行：
      * H3 的 Context-IR 认的就是这套标签语法；
      * `<Audio 1>: fully_copy` 是**唯一**能明确说清「音轨复用已上传的原曲、
        不要生成音乐」的官方写法——比在任何地方写「不要生成配乐」都干净
        （官方失败模式③：一边要配乐一边禁配乐）；
      * 让「参考职责已声明」这件事可被机器校验，而不是靠中文措辞碰运气。
    """
    label = _chain_frame_label(seg)
    parts = ["[reference declaration] %s: character reference; %s: character "
             "turnaround reference" % (a["char_label"], a["turn_label"])]
    if label:
        parts.append("%s: first_frame reference (the previous segment's final frame)"
                     % label)
    parts.append("<Subject 1> is the only character; her identity is fully_preserved "
                 "in every shot, while the drawing medium, palette and background "
                 "system change by design")
    parts.append("<Audio 1>: fully_copy - the uploaded original song is reused 1:1 as "
                 "the complete final audio track. Do not generate, replace or "
                 "re-perform any music")
    return "".join([parts[0]] + [". " + p for p in parts[1:]]) + "."


def _mv_reference_section(plan, seg, lang, a, canon):
    """【人物与参考保持一致性】—— 参考素材的职责声明 + 完整 Canon。"""
    label = _chain_frame_label(seg)
    ch = _chain_of(seg)
    decl = _mv_declaration_line(plan, seg, a)
    if lang == "zh":
        parts = [u"%s 是本片唯一的角色，全片不出现第二个角色。"
                 % (canon.get("name") or u"人物")]
        parts.append(u"她的形象由 %s（人物参考图）与 %s（人物三视图：正面、四分之三侧面、"
                     u"正侧面、背面）共同定义：%s"
                     % (a["char_label"], a["turn_label"], _canon_clause(canon, "zh")))
        parts.append(u"%s 是脸部与色彩的最高依据，%s 是轮廓、侧面与背面的最高依据。"
                     % (a["char_label"], a["turn_label"]))
        if label and ch:
            parts.append(u"%s 是上一段（%s）的最后一帧，作为本段【首帧】参考"
                         u"（first_frame）：它只提供动作与构图的接续起点，"
                         u"不改变人物身份，也不改变上面这条 Canon。"
                         % (label, ch.get("from_segment")))
        parts.append(_CANON_DRIFT_ZH)
        return u" ".join(parts) + u"\n" + decl
    parts = ["<Subject 1> is the only character in the target video. Her appearance "
             "is defined by %s (character reference) and %s (character turnaround "
             "reference). %s"
             % (a["char_label"], a["turn_label"], _canon_clause(canon, "en"))]
    if label and ch:
        parts.append("%s is the final frame of the previous segment (%s), used as the "
                     "first_frame reference for this segment: it provides the starting "
                     "point for motion and composition only, and does not change the "
                     "character's identity." % (label, ch.get("from_segment")))
    parts.append("No other character appears at any time; her design is never altered.")
    return " ".join(parts) + "\n" + decl


def _mv_style_section(plan, seg, lang):
    """【风格提示词】—— 2D 限制感 + 本段画风 + 负向。"""
    ad = plan.get("art_direction") or {}
    medium = ad.get("primary_medium") or u"二维手绘"
    mv = seg.get("art_movement") or ""
    anim = seg.get("animation_medium") or "limited animation"
    if lang == "zh":
        return (u"2D limited animation、hand-drawn、flat composition。"
                u"本段画风 `%s`，世界用 %s 绘制；%s。"
                u"摄影机全程不离开平面二维空间，不做 3D 运镜、不做写实景深。"
                u"负向：%s。"
                % (mv, medium, anim, ad.get("style_negative") or u"—"))
    return ("2D limited animation, hand-drawn, flat composition. This segment is drawn "
            "in %s (movement reference: %s). %s. The camera never leaves flat "
            "two-dimensional space; no 3D camera, no photorealistic depth of field. "
            "Negative: %s."
            % (medium, mv, anim, ad.get("style_negative") or "n/a"))


def _mv_content_section(plan, seg, lang, shots):
    """【内容提示词】—— 头一段是「延续上一帧」，然后按镜头写。"""
    ch = _chain_of(seg)
    lines = []
    segs_all = plan.get("segments") or []
    is_final_segment = bool(segs_all) and (seg is segs_all[-1])
    end_txt = ""
    if is_final_segment and endings_mod is not None:
        end_txt = endings_mod.ending_block(plan, lang)
    if ch and ch.get("declared"):
        cont = float(ch.get("continue_seconds") or 1.5)
        desc = (ch.get("describe") or "").strip() or u"（上一帧的画面）"
        ratio = float(ch.get("max_vertical_displacement_ratio", 0.12)) * 100
        if lang == "zh":
            lines.append(u"0–%.1fs 延续上一帧：%s。这一段保持上一帧的画风与姿势，"
                         u"只做同族的连续动作（不要换姿势——首尾帧之间垂直位移超过"
                         u"画面高度 %.0f%% 容易肢体撕裂）。" % (cont, desc, ratio))
            if seg.get("chain_continuity"):
                lines.append(u"起手接法：%s。" % seg["chain_continuity"])
            lines.append(u"%.1fs 之后，世界在段内转场到本段画风 `%s`，"
                         u"人物的身份与服装结构在转场中保持不变。"
                         % (cont, seg.get("art_movement") or ""))
        else:
            lines.append("0-%.1fs CONTINUES FROM THE PREVIOUS LAST FRAME: %s. Keep the "
                         "previous segment's drawing style and pose and do only "
                         "same-family continuous motion; do not change the pose, "
                         "because vertical displacement above %.0f%% of frame height "
                         "between the two chained frames tears the limbs."
                         % (cont, desc, ratio))
            if seg.get("chain_continuity"):
                lines.append("Opening continuity: %s." % seg["chain_continuity"])
            lines.append("After %.1fs the world transitions inside the shot into this "
                         "segment's style `%s`, while her identity and costume "
                         "structure stay unchanged."
                         % (cont, seg.get("art_movement") or ""))
    elif lang == "zh":
        if not segs_all or seg is segs_all[0]:
            lines.append(u"这是全片开头：%s。"
                         % (seg.get("continuity_from_previous")
                            or u"建立人物与世界的第一次关系"))
        else:
            # 不是第一段，却也没接上尾帧 —— 如实说，不要冒称「开头」
            lines.append(u"未接上一帧：%s。请尽快用 prism/mvstudio lastframe 取上一段尾帧，"
                         u"否则这一段会与上一段断开。"
                         % (seg.get("continuity_from_previous") or u"按同族动作起手"))
    else:
        if not segs_all or seg is segs_all[0]:
            lines.append("Opening segment: %s"
                         % (seg.get("continuity_from_previous")
                            or "establishes the character"))
        else:
            lines.append("Not chained to the previous last frame: %s. Capture the "
                         "previous tail frame, or this segment will not connect."
                         % (seg.get("continuity_from_previous")
                            or "start from the same motion family"))

    # 魔性动作：重复设计是**段级**指令，放在镜头之前，先定这一整段怎么跳
    if motion_mod is not None:
        _rep = motion_mod.render_schedule(plan, seg, lang)
        if _rep:
            lines.append(_rep)

    for i, sh in enumerate(shots, 1):
        t = float(sh.get("start") or 0.0)
        size = sh.get("shot_size") or ("medium shot" if i == 1 else "close-up")
        action = (sh.get("action") or "").rstrip(u"。. ")
        els = seg.get("background_lyric_elements") or []
        lyric = sh.get("lyric") or _lyric_line(seg, 0)
        typo = ""
        if common.config()["output"].get("lyric_typography", True) and lyric \
                and not _is_instrumental(lyric):
            typo = (u"歌词「%s」以硬边平面字体印在背景平面上。" % lyric if lang == "zh"
                    else u'The lyric line "%s" is printed on the background plane as '
                         u'hard-edged flat typography.' % lyric)
        # 运镜分层：景别 / 角度 / 构图 / 焦 / 2D 招 / 相机与主体的关系 / 揭示目的
        cam_layers, cam_lock = {}, ""
        if camera_mod is not None:
            cam_layers = camera_mod.describe_shot(sh, lang)["layers"]
            if sh.get("camera") == "Static Shot" or not sh.get("camera"):
                cam_lock = camera_mod.static_lock_line(lang)
        cut = _cut_sentence(sh, i == len(shots), seg)
        if end_txt and i == len(shots):
            # 已经选了收尾效果 —— 它比笼统的 "Final state" 具体得多
            cut = (" " + end_txt) if lang != "zh" else (" " + end_txt)
        size_cn = None
        if camera_mod is not None and sh.get("shot_size_id"):
            _it = camera_mod.shot_size(sh["shot_size_id"])
            if _it:
                size_cn = _it.get("name_cn")
        size_disp = (size_cn or size) if lang == "zh" else size
        if lang == "zh":
            head = (u"[Shot %d] %.1fs–%.1fs，%s。" % (i, t, float(sh.get("end") or 0), size_disp)
                    if i > 1 else u"[Shot 1] %s。" % size_disp)
            bg = (u"背景是平面的，由这段歌词里的实物构成：%s。" % u"、".join(els)
                  if els else u"")
            # 中文块里嵌的英文句子要大写开头，且句与句之间要留空格，
            # 否则会出现「…next.[Shot 2]」这种粘在一起的排版
            act = _cap(action) if action else u""
            # 具名取层：缺哪层就跳过，不会错位。景别已在 head 里，不重复。
            mid = [cam_layers.get(k) for k in ("angle", "focus", "framing", "move_2d")]
            mid = [x for x in mid if x]
            layers = (u"，".join(mid) + u"。") if mid else u""
            tail_bits = [x for x in (cam_layers.get("relation"),
                                     cam_layers.get("purpose")) if x]
            tail = (u"。".join(tail_bits) + u"。") if tail_bits else u""
            if cam_lock:
                tail = (tail + cam_lock) if tail else cam_lock
            lines.append(u" ".join(x for x in [
                head, layers, (act + u"。") if act else u"", bg, typo,
                _camera_sentence_zh(sh), tail, cut] if x))
        else:
            head = ("[Shot %d] At %02d:%06.3f, the camera cuts to a %s. "
                    % (i, int(t // 60), t % 60, size) if i > 1
                    else "[Shot 1] A %s frames her. " % size)
            bg = ("Behind her the flat background is built out of the lyric's own "
                  "objects: %s. " % ", ".join(els)) if els else ""
            mid_en = [cam_layers.get(k) for k in ("angle", "focus", "framing", "move_2d")]
            mid_en = [x for x in mid_en if x]
            layers_en = (", ".join(mid_en) + ".") if mid_en else ""
            tail_en_bits = [x for x in (cam_layers.get("relation"),
                                        cam_layers.get("purpose")) if x]
            tail_en = (". ".join(tail_en_bits) + ".") if tail_en_bits else ""
            if cam_lock:
                tail_en = (tail_en + " " + cam_lock) if tail_en else cam_lock
            lines.append(" ".join(x for x in [
                head, layers_en, _sentence(action), bg, typo,
                _camera_sentence(sh), tail_en, cut.strip()] if x))
    if seg.get("is_tail_pad"):
        lines.append(u"音乐在本段中途结束，之后没有声音：只用 hold frame、视觉衰减、"
                     u"慢速动画、纸张质感、最后一张定格赛璐璐补足；"
                     u"不要创造新音乐、不要加节拍。" if lang == "zh" else
                     "The supplied audio ends before this segment ends; the remainder is "
                     "hold frame, visual decay, slow animation, paper texture and a "
                     "final held cel only. Do not create any new music or beat.")
    # 用空格连接：中文块里会嵌英文句子（运镜/切法），不留空格会出现
    # 「…cuts to the next.[Shot 2]」这种粘在一起的排版
    return u" ".join(lines)


def _mv_integrated(plan, seg, canon):
    ad = plan.get("art_direction") or {}
    return (u"人物参考图决定谁在画面里，本段歌词决定画什么，音乐决定什么时候变化，"
            u"画风路线「%s」决定怎么表现。人物稳定性优先于视觉实验性。"
            % (ad.get("route_name") or u"—"))


def render_mv(plan, seg, lang="zh"):
    """用户指定的六段结构 + 尾帧续接。"""
    a = _assets(plan)
    canon = plan.get("character_canon") or {}
    shots = seg.get("shots") or []
    out = []

    align = _chain_block(seg)
    if align:
        out += [align, ""]

    if lang == "zh":
        out += [u"%s：" % MV_SECTIONS_ZH[0],
                _mv_reference_section(plan, seg, lang, a, canon), "",
                u"%s：" % MV_SECTIONS_ZH[1],
                _mv_style_section(plan, seg, lang), "",
                u"%s：" % MV_SECTIONS_ZH[2],
                _mv_content_section(plan, seg, lang, shots), "",
                "integrated_multimodal_description: %s"
                % (seg.get("integrated_multimodal_description")
                   or _mv_integrated(plan, seg, canon)), "",
                "overall_soundscape: %s"
                % (seg.get("overall_soundscape")
                   or u"环境音与身体动作的物理声音。"), "",
                "non_diegetic_music: N/A"]
    else:
        out += ["%s:" % MV_SECTIONS_EN[0],
                _mv_reference_section(plan, seg, lang, a, canon), "",
                "%s:" % MV_SECTIONS_EN[1],
                _mv_style_section(plan, seg, lang), "",
                "%s:" % MV_SECTIONS_EN[2],
                _mv_content_section(plan, seg, lang, shots), "",
                "integrated_multimodal_description: %s"
                % (seg.get("integrated_multimodal_description")
                   or _mv_integrated(plan, seg, canon)), "",
                "overall_soundscape: %s"
                % (seg.get("overall_soundscape")
                   or "Ambient room tone and the physical sounds of the dance."), "",
                "non_diegetic_music: N/A"]
    return "\n".join(out)


_ROUTES["mv"] = render_mv


def render_segment(plan, seg, route="ref", lang="en"):
    fn = _ROUTES.get(route)
    if fn is None:
        raise ValueError("未知 H3 路线：%s（可选 %s）" % (route, ", ".join(_ROUTES)))
    return fn(plan, seg, lang=lang)


# ------------------------------------------------------------------ 中文导演简报
def render_brief(plan, seg):
    """给人看的简报。**不粘贴进模型**——所以这里可以自由写中文和判断。"""
    lines = []
    start = float(seg.get("time_start") or 0)
    end = float(seg.get("time_end") or 0)
    prompt_sec = float(seg.get("prompt_seconds") or (end - start))
    lines.append(u"- **段落**：%s（第 %s 段）" % (seg.get("label"), seg.get("id")))
    lines.append(u"- **乐句时间窗**：歌曲 %.3fs–%.3fs ｜ 本条 prompt 覆盖 %.2fs%s"
                 % (start, end, prompt_sec,
                    u"（末段补足）" if seg.get("is_tail_pad") else ""))
    lines.append(u"- **吸附**：%s（偏移 %.2f 拍）｜ 小节 %s → %s"
                 % (seg.get("snapped_to"), seg.get("offset_beats") or 0,
                    seg.get("bar_start"), seg.get("bar_end")))
    lyr = seg.get("lyrics") or []
    lines.append(u"- **对应歌词**：%s" % (u" ／ ".join(lyr) if lyr else u"（器乐段）"))
    if seg.get("lyric_carry_over"):
        lines.append(u"  - ⚠️ 一句歌词跨段：本段与相邻段必须表达同一意象，不得换场景")
    lines.append(u"- **本段歌词核心意义**：%s" % (seg.get("central_meaning") or ""))
    lines.append(u"- **背景里的歌词元素**：%s"
                 % (u"、".join(seg.get("background_lyric_elements") or []) or u"（无）"))
    bind = seg.get("lyric_action_binding") or []
    if bind:
        lines.append(u"- **舞蹈与歌词的绑定**：")
        for b in bind:
            lines.append(u"  - 「%s」→ %s（第 %s 拍）"
                         % (b.get("lyric"), b.get("action"), b.get("beat")))
    else:
        lines.append(u"- **舞蹈与歌词的绑定**：%s" % (seg.get("choreography") or ""))
    lines.append(u"- **画风**：`%s`" % (seg.get("art_movement") or ""))
    lines.append(u"- **运镜（官方词 + 幅度 + 速度）**：")
    for sh in (seg.get("shots") or []):
        lines.append(u"  - [%s] %.3fs–%.3fs ｜ %s%s%s ｜ %s"
                     % (sh.get("index"), sh.get("start") or 0, sh.get("end") or 0,
                        sh.get("camera") or "",
                        (u" / " + sh["camera_amplitude"]) if sh.get("camera_amplitude") else "",
                        (u" / " + sh["camera_speed"]) if sh.get("camera_speed") else "",
                        sh.get("action") or ""))
    lines.append(u"- **动画机制（2D 限制感）**：%s" % (seg.get("animation_medium") or ""))
    lines.append(u"- **承上 / 启下**：%s ／ %s"
                 % (seg.get("continuity_from_previous") or "—",
                    seg.get("hook_to_next") or "—"))
    return "\n".join(lines)


# ------------------------------------------------------------------ 整包
HEADER = u"""# 2d-limited-mv-studio · MiniMax H3 提示词包

> 每条 prompt 都是 **H3 原生格式**，可整段复制粘贴。
> 「导演简报」是给你看的，**不要**贴进模型——H3 前面有 Context-IR 做理解与改写，
> 塞进人类注记会当成画面要求去理解。

## 一、上传顺序（顺序即编号，模型不读路径）

| 顺序 | 素材 | 用途声明 |
|------|------|----------|
| 1 | 人物原始参考图 | character reference → `<Picture 1>` |
| 2 | 三视图（人物转面表） | character turnaround reference → `<Picture 2>`（没有就跳过） |
| 3 | 本段音频（切好的段） | original song, reused 1:1 → `<Audio 1>` |

## 二、每条怎么用

1. 上传上表第 1、2 项（**每次都要传**，别只传一次）；
2. 上传对应的音频段；
3. 复制该条的「粘贴区」整段，贴进 H3 的提示词框；
4. 时长选 **%s 秒**左右，比例按你的成片定。
5. 生成完按 C1→C2→… 顺序拼接，**不要加淡入淡出**，接缝要严丝合缝。

## 三、不要做的事

- 不要让模型生成配乐：音轨是原曲，1:1 复用（`<Audio 1>: fully_copy`）。
- 不要把不同条拼成一条：每条 ≤15s 是 H3 的硬上限。
- 不要在粘贴区里加 Markdown、加批注、加中文说明。
"""


def render_package(plan, route="ref", lang="en"):
    segs = plan.get("segments") or []
    meta = plan.get("meta") or {}
    target = meta.get("segment_target_seconds") or 14.5
    out = [HEADER % ("%.1f" % float(target))]
    out.append("")
    out.append(u"## 全局设定")
    out.append("")
    out.append(u"- **核心概念**：%s" % (plan.get("mv_concept") or ""))
    if plan.get("logline"):
        out.append(u"- **一句话**：%s" % plan["logline"])
    ad = plan.get("art_direction") or {}
    out.append(u"- **画风路线**：%s（`%s`）" % (ad.get("route_name") or "—",
                                               ad.get("route_id") or "—"))
    out.append(u"- **逐段画风**：%s"
               % " → ".join(ad.get("movement_per_segment") or []))
    canon = plan.get("character_canon") or {}
    out.append(u"- **人物**：%s" % (canon.get("name") or ""))
    out.append(u"- **音乐**：%s BPM ｜ 总长 %ss ｜ 拍网格 %.4fs/拍 ｜ 小节 %.4fs"
               % (meta.get("bpm"), meta.get("duration"), meta.get("beat_sec") or 0,
                  meta.get("bar_sec") or 0))
    out.append("")
    for i, seg in enumerate(segs, 1):
        out.append("---")
        out.append("")
        out.append("## MiniMax H3 Prompt %d" % i)
        out.append("")
        out.append(u"### 导演简报（中文，不要粘贴）")
        out.append("")
        out.append(render_brief(plan, seg))
        out.append("")
        out.append(u"### 粘贴区（%s 路线 · %s）" % (route, lang))
        out.append("")
        out.append("```text")
        out.append(render_segment(plan, seg, route=route, lang=lang))
        out.append("```")
        out.append("")
    return "\n".join(out) + "\n"


def render_storyboard(plan):
    """分镜总表：卡点 / 歌词 / 画风 / 动作 / 运镜 一表看清。"""
    segs = plan.get("segments") or []
    lines = [u"# 分镜总表（卡点 / 歌词 / 画风 / 动作 / 运镜）", ""]
    lines.append(u"| 段 | 歌曲时间 | 小节 | 歌词 | 画风 | 背景歌词元素 | 动作 | 运镜 | 切 |")
    lines.append(u"|----|---------|------|------|------|-------------|------|------|-----|")
    for s in segs:
        lyr = u" ／ ".join(s.get("lyrics") or []) or u"〔器乐〕"
        bg = u"、".join(s.get("background_lyric_elements") or [])
        for j, sh in enumerate(s.get("shots") or []):
            lines.append(u"| %s%s | %.3f–%.3f | %s→%s | %s | `%s` | %s | %s | %s | %s |"
                         % (s.get("label"), (u".%d" % (j + 1)) if j else "",
                            float(s.get("time_start") or 0) + float(sh.get("start") or 0),
                            float(s.get("time_start") or 0) + float(sh.get("end") or 0),
                            s.get("bar_start"), s.get("bar_end"),
                            lyr if j == 0 else u"",
                            s.get("art_movement") or "", bg if j == 0 else u"",
                            sh.get("action") or "", sh.get("camera") or "",
                            sh.get("cut") or ""))
    lines.append("")
    return "\n".join(lines) + "\n"


def main(argv=None):
    import argparse
    ap = argparse.ArgumentParser(description="渲染 MiniMax H3 提示词")
    common.add_common_args(ap)
    ap.add_argument("--plan", default=None)
    ap.add_argument("--route", choices=["ref", "i2va", "t2va"], default="ref")
    ap.add_argument("--lang", choices=["en", "zh"], default="en")
    ap.add_argument("--check", action="store_true", help="只做就绪检查")
    args = ap.parse_args(argv)
    common.apply_common_args(args)
    plan_path = args.plan or os.path.join(common.path("workspace_analysis"),
                                          "director_plan.json")
    plan = common.read_json(plan_path, {}) or {}
    problems = check_ready(plan)
    if problems:
        if args.json:
            common.emit({"ready": False, "problems": problems}, True)
        else:
            common.echo(u"拒绝渲染（缺 %d 项）：" % len(problems))
            for p in problems:
                common.echo(u"  - %s" % p)
        return 2
    if args.check:
        common.emit({"ready": True, "problems": []}, args.json)
        return 0
    text = render_package(plan, route=args.route, lang=args.lang)
    out = os.path.join(common.path("output_latest"), "minimax_h3_prompts.md")
    common.write_text(out, text)
    common.write_text(os.path.join(common.path("output_latest"), "storyboard.md"),
                      render_storyboard(plan))
    if args.json:
        common.emit({"ready": True, "prompts": out, "chars": len(text)}, True)
    else:
        common.echo(u"已渲染 %d 条 → %s" % (len(plan.get("segments") or []), out))
    return 0


if __name__ == "__main__":
    sys.exit(main())
