#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""camera —— 分层运镜库：景别 / 角度 / 运动 / 构图 / 焦 / 2D 专属招。

**为什么要分层，而不是多编几个运镜词：**

MiniMax H3 只认它官方那 20 个运动词。写 `crane shot`、`whip pan`、`dolly zoom`
这类实拍术语，模型不认——校验器也会拦。所以「丰富运镜角度」这件事，
不能靠往词表里塞新词，只能靠**分层**：

    景别 shot_size      → 自然语言，决定情绪距离
    角度 angle          → 自然语言，决定心理关系（**最多人漏掉的一层**）
    运动 camera         → 只能用官方那 20 个词
    构图 framing        → 自然语言，平面构成
    焦   focus          → 自然语言
    关系 relation       → 自然语言，相机与主体的关系
    揭示 purpose        → 自然语言，这一下要说明什么

再加一层实拍没有的东西：**2D 专属运镜**（摄影台推移 / 多层视差 / 赛璐璐滑动 /
套印偏移 / 纸张推移 / 圆形遮罩 / 硬裁切 / 分屏 / 曝光闪白 / 定格微移）。
这一层才是本技能的身份——2D MV 的先锋性来自平面置换，不是摄影机乱飞。

不变量（由测试强制）：`cinematic_to_official` 里**每一个**电影术语都必须映射回
官方 20 词之一。否则就是在教用户写废词。
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
PKG_ROOT = os.path.dirname(os.path.dirname(HERE))
_LIB_CACHE = [None]


def _library():
    if _LIB_CACHE[0] is None:
        path = os.path.join(PKG_ROOT, "references", "camera-library.json")
        data = common.read_json(path, {}) or {}
        _LIB_CACHE[0] = data
    return _LIB_CACHE[0]


def reload():
    _LIB_CACHE[0] = None
    return _library()


# ------------------------------------------------------------------ 各层
def shot_sizes(solo_only=False):
    out = list(_library().get("shot_sizes") or [])
    if solo_only:
        out = [x for x in out if x.get("solo", True)]
    return out


def angles():
    return list(_library().get("angles") or [])


def compositions():
    return list(_library().get("compositions") or [])


def focus_terms():
    return list(_library().get("focus_terms") or [])


def moves_2d():
    return list(_library().get("moves_2d") or [])


def cinematic_map():
    return dict(_library().get("cinematic_to_official") or {})


def relations():
    return list(_library().get("relations") or [])


def rules():
    return dict(_library().get("rules") or {})


def official_cameras():
    """库里的官方运动词条目（24 条，按家族分类）。"""
    return list(_library().get("cameras") or [])


def style_camera_map():
    return dict(_library().get("style_camera_map") or {})


def _by_id(items, key):
    for it in items:
        if it.get("id") == key:
            return it
    return None


def angle(key):
    return _by_id(angles(), key)


def composition(key):
    return _by_id(compositions(), key)


def focus(key):
    return _by_id(focus_terms(), key)


def move2d(key):
    return _by_id(moves_2d(), key)


def relation(key):
    return _by_id(relations(), key)


def shot_size(key):
    return _by_id(shot_sizes(), key)


# ------------------------------------------------------------------ 映射
def map_cinematic(term):
    """把实拍电影术语翻成官方运动词 + 幅度 + 速度。未知术语返回 None。"""
    spec = cinematic_map().get(term)
    if not spec:
        return None
    out = dict(spec)
    official = set(common.config()["output"]["camera_official_terms"])
    if out.get("official") not in official:
        return None
    with_term = out.get("with")
    if with_term and with_term not in official:
        out.pop("with", None)
    return out


def static_lock_line(lang="en"):
    """固定镜头的加锁句。**实测最有用的一条**：模型在固定镜头上会自己飘。"""
    r = (rules().get("static_lock") or {})
    return r.get(lang) or r.get("en") or ""


def needs_static_lock(shot):
    return (shot or {}).get("camera") == "Static Shot" or shot.get("camera") is None


# ------------------------------------------------------------------ 渲染
def _txt(item, lang, field="prompt_en"):
    if not item:
        return ""
    if lang == "zh":
        return item.get("prompt_zh") or item.get("name_cn") or item.get(field) or ""
    return item.get(field) or item.get("name_en") or ""


def describe_shot(shot, lang="en", include_focus=True):
    """把一个镜头拆成**具名**的层。

    为什么具名而不是返回一个数组：层是可以缺的（老稿子没有 angle、库坏了没有
    size）。按下标切数组，一旦缺一层，后面全部错位——踩过这个坑。
    公式：景别 + 角度 + 焦 + 构图 + 2D招 + 关系 + 揭示目的
    """
    layers = {
        "size": _txt(shot_size(shot.get("shot_size_id") or shot.get("shot_size")), lang),
        "angle": _txt(angle(shot.get("angle")), lang),
        "focus": _txt(focus(shot.get("focus")), lang) if include_focus else "",
        "framing": _txt(composition(shot.get("framing")), lang),
        "move_2d": _txt(move2d(shot.get("move_2d")), lang),
        "relation": "",
        "purpose": (shot.get("purpose") or "").strip().rstrip(u"。."),
    }
    rel = relation(shot.get("camera_relation"))
    if rel:
        layers["relation"] = (rel.get(lang) or rel.get("en") or "").strip()
    layers = dict((k, v.strip()) for k, v in layers.items() if v and v.strip())

    order = ["size", "angle", "focus", "framing", "move_2d", "relation", "purpose"]
    bits = [layers[k] for k in order if k in layers]
    joiner = u"。".join if lang == "zh" else ". ".join
    end_p = u"。" if lang == "zh" else "."
    return {
        "layers": layers,
        "bits": bits,
        "text": (joiner(bits) + end_p) if bits else "",
    }


def validate_shot(shot):
    """返回这个镜头的相机层问题列表。

    注意降级行为：如果库根本没加载起来（被改坏/缺文件），
    就**不要**再用库去判 angle/framing 合不合法——那会把整片判成红的，
    而真正的问题其实只有一个：库坏了。不依赖库的规则（相机关系、3D 语汇）照常生效。
    """
    problems = []
    label = "镜头 %s" % (shot.get("index") or "?")
    has_lib = bool(angles() or compositions() or focus_terms() or moves_2d()
                   or relations())
    if has_lib:
        if shot.get("angle") and not angle(shot["angle"]):
            problems.append(u"%s 的角度 '%s' 不在 camera-library 里"
                            % (label, shot["angle"]))
        if shot.get("framing") and not composition(shot["framing"]):
            problems.append(u"%s 的构图 '%s' 不在 camera-library 里"
                            % (label, shot["framing"]))
        if shot.get("focus") and not focus(shot["focus"]):
            problems.append(u"%s 的焦 '%s' 不在 camera-library 里" % (label, shot["focus"]))
        if shot.get("move_2d") and not move2d(shot["move_2d"]):
            problems.append(u"%s 的 2D 运镜 '%s' 不在 camera-library 里"
                            % (label, shot["move_2d"]))
        if shot.get("camera_relation") and not relation(shot["camera_relation"]):
            problems.append(u"%s 的相机关系 '%s' 不在 camera-library 里"
                            % (label, shot["camera_relation"]))
    # 下面两条不依赖库，永远生效
    if shot.get("camera") and shot["camera"] != "Static Shot" \
            and not shot.get("camera_relation"):
        problems.append(u"%s 有运动（%s）但没写相机与主体的关系 —— "
                        u"这是抖动与「人物在飘」的常见根因"
                        % (label, shot["camera"]))
    blob = " ".join(str(shot.get(k) or "") for k in
                    ("purpose", "move_2d", "camera_relation")).lower()
    for bad in ("3d orbit", "drone", "fpv", "fly-through", "spiraling"):
        if bad in blob:
            problems.append(u"%s 里混进了 3D 运镜语汇 '%s'" % (label, bad))
    return problems


def moving_shot_cap(n):
    """每段允许的运动镜头数上限：ceil(n/2)。"""
    return -(-int(n) // 2)


def check_camera_budget(seg):
    """这一段运动镜头有没有超量。返回 problems。"""
    shots = seg.get("shots") or []
    if not shots:
        return []
    cap = moving_shot_cap(len(shots))
    moving = [s for s in shots if s.get("camera") and s["camera"] != "Static Shot"]
    if len(moving) > cap:
        return [u"段 %s 有 %d/%d 个运动镜头，超过上限 %d —— "
                u"运镜丰富不等于运镜展览，其余请压回固定镜头"
                u"（机位锁死、画面用 2D 招动）"
                % (seg.get("label") or seg.get("id"), len(moving), len(shots), cap)]
    return []


# ------------------------------------------------------------------ 选型
# 单人 MV 安全的角度顺序（由「中性 → 有观点 → 极端」递进）
_ANGLE_ROTATION = ["eye_level", "flat_frontal", "low_angle", "three_quarter_soft",
                   "high_angle", "overhead_top", "close_eye_level"]
_ANGLE_FALLBACK = ["eye_level", "flat_frontal", "low_angle", "high_angle",
                   "overhead_top", "over_the_shoulder"]
_COMPOSITION_ROTATION = ["rule_of_thirds", "symmetry_centered", "depth_layering",
                         "negative_space", "frame_within_frame", "poster_layout",
                         "leading_lines", "graphic_occlusion"]


def pick_angle(i, energy=None, available=None):
    """给第 i 个镜头挑角度。相邻不重复；能量高的段落更敢用极端角度。"""
    pool = [a["id"] for a in (angles() or [])]
    if available:
        pool = [a for a in available if a in pool]
    if not pool:
        return None
    rotation = [a for a in _ANGLE_FALLBACK if a in pool] or pool
    if energy == "peak":
        # 峰值段更愿意用有观点的角度
        rotation = [a for a in ("low_angle", "dutch_canted", "worms_eye",
                                "overhead_top") if a in pool] + rotation
    return rotation[i % len(rotation)]


def pick_composition(i, available=None):
    pool = [c["id"] for c in (compositions() or [])]
    if available:
        pool = [c for c in available if c in pool]
    rotation = [c for c in _COMPOSITION_ROTATION if c in pool] or pool
    if not rotation:
        return None
    return rotation[i % len(rotation)]


def pick_focus(shot_size_id, energy=None):
    if shot_size_id in ("close_up", "extreme_close_up", "medium_close_up"):
        return "shallow_focus"
    if energy == "quiet":
        return "soft_focus"
    return "deep_focus"


# 运动 → 关系 的默认搭配（省得每个镜头都手写，但人仍然可以改）
_RELATION_FOR_MOVE = {
    "Static Shot": "observes",
    "Push In": "opposes",
    "Pull Out": "leads",
    "Tracking Shot": "follows",
    "Truck Left": "matches_pace",
    "Truck Right": "matches_pace",
    "Pan Left": "reveals_behind",
    "Pan Right": "reveals_behind",
    "Tilt Up": "reveals_behind",
    "Tilt Down": "reveals_behind",
    "Pedestal Up": "reveals_behind",
    "Pedestal Down": "reveals_behind",
    "Arc Shot": "circles_static_subject",
    "Zoom In": "observes",
    "Zoom Out": "reveals_behind",
}


def default_relation(camera_term):
    return _RELATION_FOR_MOVE.get(camera_term)


def render_catalog_md(lang="zh"):
    """给人看的运镜分层说明（也可当参考资料读）。"""
    lines = [u"# 运镜分层库", ""]
    lines.append(u"> H3 只认官方 20 个运动词。所以「丰富角度」是靠**分层**实现的，"
                 u"不是靠编新词。")
    lines.append("")
    lines.append(u"公式：`%s`" % rules().get("formula", ""))
    lines.append("")
    for title, items, key in ((u"景别", shot_sizes(), "prompt_en"),
                              (u"角度", angles(), "prompt_en"),
                              (u"构图", compositions(), "prompt_en"),
                              (u"焦", focus_terms(), "prompt_en"),
                              (u"2D 专属运镜", moves_2d(), "prompt_en")):
        lines.append(u"## %s（%d）" % (title, len(items)))
        lines.append("")
        lines.append(u"| id | 中文 | English | 提示词 |")
        lines.append(u"|----|------|---------|--------|")
        for it in items:
            lines.append(u"| `%s` | %s | %s | %s |"
                         % (it["id"], it.get("name_cn", ""), it.get("name_en", ""),
                            it.get(key, "")))
        lines.append("")
    lines.append(u"## 实拍术语 → 官方词映射（%d）" % len(cinematic_map()))
    lines.append("")
    lines.append(u"| 术语 | 官方词 | 幅度 | 速度 | 为什么 |")
    lines.append(u"|------|--------|------|------|--------|")
    for term, spec in sorted(cinematic_map().items()):
        official = spec["official"] + ((u" + " + spec["with"]) if spec.get("with") else "")
        lines.append(u"| `%s` | `%s` | %s | %s | %s |"
                     % (term, official, spec.get("amplitude") or "—",
                        spec.get("speed") or "—", spec.get("why", "")))
    lines.append("")
    lines.append(u"## 相机与主体的关系（治抖动）")
    lines.append("")
    for r in relations():
        lines.append(u"- `%s`：%s" % (r["id"], r.get("zh")))
    lines.append("")
    lines.append(u"## 三条硬规矩")
    lines.append("")
    for k in ("static_lock", "dont_stack_verbs", "subject_camera_relationship",
              "dolly_is_not_zoom", "purpose_required"):
        r = rules().get(k)
        if isinstance(r, dict):
            lines.append(u"- **%s**：%s" % (k, r.get("zh") or r.get("en")))
    lines.append("")
    return "\n".join(lines) + "\n"


def main(argv=None):
    import argparse
    ap = argparse.ArgumentParser(description="运镜分层库")
    common.add_common_args(ap)
    ap.add_argument("--md", action="store_true")
    ap.add_argument("--map", default=None, help=u"查一个实拍术语的官方映射")
    args = ap.parse_args(argv)
    common.apply_common_args(args)
    if args.map:
        spec = map_cinematic(args.map)
        if not spec:
            common.echo(u"没有这个术语，或它映射不到官方词：%s" % args.map)
            return 2
        common.echo(u"%s → %s%s%s"
                    % (args.map, spec["official"],
                       (u" + " + spec["with"]) if spec.get("with") else "",
                       (u"（%s %s）" % (spec.get("amplitude") or "",
                                       spec.get("speed") or "")).strip()))
        common.echo(u"  %s" % spec.get("why", ""))
        return 0
    md = render_catalog_md()
    common.write_text(os.path.join(common.path("output_latest"), "camera.md"), md)
    if args.json:
        common.emit({"shot_sizes": len(shot_sizes()), "angles": len(angles()),
                     "compositions": len(compositions()),
                     "focus": len(focus_terms()), "moves_2d": len(moves_2d()),
                     "cinematic_map": len(cinematic_map()),
                     "relations": len(relations())}, True)
    else:
        common.echo(md)
    return 0


if __name__ == "__main__":
    sys.exit(main())
