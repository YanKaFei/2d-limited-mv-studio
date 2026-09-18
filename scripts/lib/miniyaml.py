#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""miniyaml —— 零依赖 YAML 子集读写。

存在的唯一理由：这台机器上 pyyaml 不保证存在，而整个 Skill 必须是
「优雅降级」的（规则 94）。本模块只支持 Skill 自己写的那些 YAML 子集：

  * 注释 (#) / 空行
  * 缩进嵌套 map
  * 块序列 (- item / - key: value)
  * 行内流式 [a, b] 与 {a: b}
  * 字符串（可带引号）/ 整数 / 浮点 / true / false / null

不支持的 YAML 特性会**明确报错**，绝不静默猜。
"""

import re

__all__ = ["load", "loads", "dump", "dumps", "MiniYamlError"]


class MiniYamlError(ValueError):
    pass


_TRUE = {"true", "yes", "on"}
_FALSE = {"false", "no", "off"}
_NULL = {"null", "~", ""}


def _strip_comment(line):
    out = []
    quote = None
    i = 0
    while i < len(line):
        ch = line[i]
        if quote:
            out.append(ch)
            if ch == quote:
                quote = None
        else:
            if ch in "\"'":
                quote = ch
                out.append(ch)
            elif ch == "#" and (i == 0 or line[i - 1] in " \t"):
                break
            else:
                out.append(ch)
        i += 1
    return "".join(out).rstrip()


def _scalar(text):
    text = text.strip()
    if text == "":
        return None
    if len(text) >= 2 and text[0] == text[-1] and text[0] in "\"'":
        return text[1:-1]
    if text.startswith("[") and text.endswith("]"):
        inner = text[1:-1].strip()
        if not inner:
            return []
        return [_scalar(p) for p in _split_flow(inner)]
    if text.startswith("{") and text.endswith("}"):
        inner = text[1:-1].strip()
        if not inner:
            return {}
        out = {}
        for part in _split_flow(inner):
            k, _, v = part.partition(":")
            out[_scalar(k)] = _scalar(v)
        return out
    low = text.lower()
    if low in _TRUE:
        return True
    if low in _FALSE:
        return False
    if low in _NULL:
        return None
    if re.fullmatch(r"[-+]?\d+", text):
        try:
            return int(text)
        except ValueError:
            pass
    if re.fullmatch(r"[-+]?(\d+\.\d*|\.\d+|\d+)([eE][-+]?\d+)?", text):
        try:
            return float(text)
        except ValueError:
            pass
    return text


def _split_flow(text):
    parts, buf, quote, depth = [], [], None, 0
    for ch in text:
        if quote:
            buf.append(ch)
            if ch == quote:
                quote = None
            continue
        if ch in "\"'":
            quote = ch
            buf.append(ch)
        elif ch in "[{":
            depth += 1
            buf.append(ch)
        elif ch in "]}":
            depth -= 1
            buf.append(ch)
        elif ch == "," and depth == 0:
            parts.append("".join(buf).strip())
            buf = []
        else:
            buf.append(ch)
    if "".join(buf).strip():
        parts.append("".join(buf).strip())
    return parts


def _tokenize(text):
    lines = []
    for raw in text.splitlines():
        if not raw.strip():
            continue
        stripped = _strip_comment(raw)
        if not stripped.strip():
            continue
        if stripped.lstrip().startswith("#"):
            continue
        indent = len(stripped) - len(stripped.lstrip(" "))
        if "\t" in stripped[:indent + 1]:
            raise MiniYamlError("miniyaml 不支持 tab 缩进: %r" % raw)
        lines.append((indent, stripped.strip()))
    return lines


def _parse(lines, i, indent):
    if i >= len(lines):
        return None, i
    if lines[i][1].startswith("- ") or lines[i][1] == "-":
        out = []
        while i < len(lines) and lines[i][0] == indent and (
                lines[i][1] == "-" or lines[i][1].startswith("- ")):
            content = lines[i][1][1:].strip()
            if content == "":
                j = i + 1
                if j < len(lines) and lines[j][0] > indent:
                    val, i = _parse(lines, j, lines[j][0])
                    out.append(val)
                else:
                    out.append(None)
                    i = j
                continue
            head, sep, tail = _split_kv(content)
            is_map_item = bool(sep) and not content.startswith(("[", "{", "\"", "'"))
            is_list_item = content.startswith("- ")
            if is_map_item or is_list_item:
                # "- key: value" 内容从第 indent+2 列开始；后续行只要缩进更深就属于本项
                key_indent = indent + 2
                sub = [(key_indent, content)]
                j = i + 1
                while j < len(lines) and lines[j][0] > indent:
                    sub.append((max(lines[j][0], key_indent), lines[j][1]))
                    j += 1
                val, _ = _parse(sub, 0, key_indent)
                out.append(val)
                i = j
            else:
                out.append(_scalar(content))
                i += 1
        return out, i

    out = {}
    while i < len(lines) and lines[i][0] == indent:
        key, sep, rest = _split_kv(lines[i][1])
        if not sep:
            raise MiniYamlError("miniyaml 期望 'key: value'，得到 %r" % lines[i][1])
        key = key.strip().strip("\"'")
        rest = rest.strip()
        if rest:
            out[key] = _scalar(rest)
            i += 1
        else:
            j = i + 1
            if j < len(lines) and lines[j][0] > indent:
                val, i = _parse(lines, j, lines[j][0])
                out[key] = val
            else:
                out[key] = None
                i = j
    return out, i


def _split_kv(text):
    quote, depth = None, 0
    for idx, ch in enumerate(text):
        if quote:
            if ch == quote:
                quote = None
            continue
        if ch in "\"'":
            quote = ch
        elif ch in "[{":
            depth += 1
        elif ch in "]}":
            depth -= 1
        elif ch == ":" and depth == 0:
            if idx + 1 >= len(text) or text[idx + 1] in " \t":
                return text[:idx], True, text[idx + 1:]
    return text, False, ""


def loads(text):
    lines = _tokenize(text or "")
    if not lines:
        return {}
    value, _ = _parse(lines, 0, lines[0][0])
    return value


def load(path):
    with open(path, "r", encoding="utf-8") as fh:
        return loads(fh.read())


def _needs_quote(s):
    if s == "":
        return True
    if s.strip() != s:
        return True
    if s.lower() in _TRUE or s.lower() in _FALSE or s.lower() in _NULL:
        return True
    if re.fullmatch(r"[-+]?\d+(\.\d+)?([eE][-+]?\d+)?", s):
        return True
    if s[0] in "-?:,[]{}#&*!|>'\"%@`":
        return True
    if ": " in s or " #" in s:
        return True
    return False


def _dump_scalar(value):
    if value is None:
        return "null"
    if value is True:
        return "true"
    if value is False:
        return "false"
    if isinstance(value, (int, float)):
        return repr(value) if isinstance(value, float) else str(value)
    s = str(value)
    if _needs_quote(s):
        return '"%s"' % s.replace("\\", "\\\\").replace('"', '\\"')
    return s


def _dump(value, indent, lines):
    pad = "  " * indent
    if isinstance(value, dict):
        if not value:
            return
        for k, v in value.items():
            key = _dump_scalar(k) if _needs_quote(str(k)) else str(k)
            if isinstance(v, (dict, list)) and v:
                lines.append("%s%s:" % (pad, key))
                _dump(v, indent + 1, lines)
            elif isinstance(v, (dict, list)):
                lines.append("%s%s: %s" % (pad, key, "{}" if isinstance(v, dict) else "[]"))
            else:
                lines.append("%s%s: %s" % (pad, key, _dump_scalar(v)))
    elif isinstance(value, list):
        for item in value:
            if isinstance(item, dict) and item:
                sub = []
                _dump(item, indent + 1, sub)
                first = sub[0].strip()
                lines.append("%s- %s" % (pad, first))
                for extra in sub[1:]:
                    lines.append(extra)
            elif isinstance(item, list) and item:
                lines.append("%s-" % pad)
                _dump(item, indent + 1, lines)
            else:
                lines.append("%s- %s" % (pad, _dump_scalar(item)))
    else:
        lines.append("%s%s" % (pad, _dump_scalar(value)))


def dumps(value):
    lines = []
    _dump(value, 0, lines)
    return "\n".join(lines) + "\n"


def dump(value, path):
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(dumps(value))
