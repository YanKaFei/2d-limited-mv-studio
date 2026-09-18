#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""artbridge —— 调用 art-aesthetic-vault（本机 147 个艺术流派的风格库）。

AGENTS.md 的硬规则：视觉/审美/风格词**必须查库**，不许凭记忆编造。
所以艺术方向不是 Agent 拍脑袋，而是：歌词语义 → 检索流派 → 取分层提示词。

库不存在时：明确降级（返回 available=False），由 Agent 用内置的艺术语汇表
（references/art-medium-map.md），绝不报错中断。
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common  # noqa: E402


def repo_dir():
    cfg = common.config().get("external", {})
    raw = cfg.get("artvault_repo") or "~/Desktop/art-aesthetic-vault/.repo"
    return os.path.expanduser(raw)


def script_path():
    return os.path.join(repo_dir(), "artvault.py")


def available():
    return os.path.isfile(script_path())


def _python():
    return common.config().get("external", {}).get("artvault_python") or "python3"


def call(args, timeout=120):
    if not available():
        return {"ok": False, "error": "art-aesthetic-vault 不在 %s" % repo_dir(), "out": ""}
    rc, out, err = common.run([_python(), script_path()] + list(args), timeout=timeout)
    return {"ok": rc == 0, "rc": rc, "out": out, "error": (err or "").strip(), "cmd": args}


def search(query, semantic=False, limit=None):
    args = ["search", query]
    if semantic:
        args.append("--semantic")
    res = call(args)
    return _lines(res)


def categories():
    return _lines(call(["categories"]))


def layers(movement, as_json=True):
    args = ["layers", movement]
    if as_json:
        args = ["--json"] + args
    res = call(args)
    if as_json and res.get("ok"):
        try:
            import json
            return json.loads(res["out"])
        except Exception:
            pass
    return _lines(res)


def show(movement):
    return _lines(call(["show", movement]))


def palette(movement):
    return _lines(call(["palette", movement]))


def related(movement):
    return _lines(call(["related", movement]))


def compose(text, subject=None, style=None, lighting=None, color=None, composition=None):
    args = ["compose", text]
    if subject:
        args += ["--subject", subject]
    for flag, val in (("--style", style), ("--lighting", lighting),
                      ("--color", color), ("--composition", composition)):
        if val:
            args += [flag, val]
    res = call(args)
    return _lines(res) or [res.get("error", "")]


def _lines(res):
    if not res.get("ok"):
        return []
    return [l.rstrip() for l in (res.get("out") or "").splitlines() if l.strip()]


def candidates_for_theme(theme_text, top=6):
    """给一句歌词主题找候选流派（模糊 + 语义各查一次，合并去重）。"""
    if not available():
        return {"available": False, "candidates": []}
    names = []
    for sem in (False, True):
        for line in search(theme_text, semantic=sem):
            name = _movement_from_line(line)
            if name and name not in names:
                names.append(name)
    return {"available": True, "query": theme_text,
            "candidates": names[:top],
            "raw": {"fuzzy": search(theme_text)[:12],
                    "semantic": search(theme_text, semantic=True)[:12]}}


def _movement_from_line(line):
    """从 '  西方古典与近代   48 个流派' 这类行里提取流派名。"""
    text = line.strip()
    if not text:
        return None
    if "个流派" in text:
        return None
    for sep in ("  ", "\t", "|", "—", "·"):
        if sep in text:
            head = text.split(sep)[0].strip()
            if 1 < len(head) <= 24:
                return head
    return text if 1 < len(text) <= 24 else None
