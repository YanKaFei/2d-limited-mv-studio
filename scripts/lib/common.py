#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""common —— 路径解析、配置装载、外部工具检测、优雅降级日志。

所有脚本共用。设计原则：
  * 任何脚本从任意 cwd 调用都能跑（路径由 __file__ 反推项目根）
  * 缺工具不崩，落到 fallback 并把 fallback 记录进 run log
  * 只读用户原始文件（规则 8）
"""

import io
import json
import os
import shutil
import subprocess
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import miniyaml  # noqa: E402

SCRIPTS_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# 安装目录（脚本住在这里）；PROJECT_ROOT 是**运行时**项目目录，可被 --project 改掉
INSTALL_ROOT = os.path.dirname(SCRIPTS_DIR)
PROJECT_ROOT = INSTALL_ROOT
_JSON_MODE = [False]


def set_project_root(root):
    """--project 覆盖：所有 input/workspace/output 相对新根解析。"""
    global PROJECT_ROOT
    PROJECT_ROOT = os.path.abspath(os.path.expanduser(root))
    _config_cache = None
    globals()["_config_cache"] = None
    return PROJECT_ROOT


def json_mode(flag=True):
    _JSON_MODE[0] = bool(flag)


def _config_candidates():
    return [os.path.join(PROJECT_ROOT, "config", "defaults.yaml"),
            os.path.join(INSTALL_ROOT, "config", "defaults.yaml")]

AUDIO_EXT = [".mp3", ".wav", ".flac", ".m4a", ".aac", ".ogg"]
IMAGE_EXT = [".png", ".jpg", ".jpeg", ".webp"]
LYRIC_EXT = [".lrc", ".srt", ".vtt", ".txt"]

_DEFAULT_CONFIG = {
    "project": {"name": "一个人物生成一条视频", "version": "1.0"},
    "audio": {"max_duration_sec": 180, "extensions": AUDIO_EXT},
    "image": {"extensions": IMAGE_EXT},
    "segment": {"seconds": 15, "max_prompts": 12},
    "paths": {
        "input_music": "input/music",
        "input_character": "input/character",
        "input_lyrics": "input/lyrics",
        "workspace_audio": "workspace/audio",
        "workspace_lyrics": "workspace/lyrics",
        "workspace_character": "workspace/character",
        "workspace_analysis": "workspace/analysis",
        "workspace_temp": "workspace/temp",
        "output_latest": "output/latest",
        "output_archive": "output/archive",
    },
    "external": {
        "artvault_repo": "~/Desktop/art-aesthetic-vault/.repo",
        "artvault_python": "python3",
    },
}

_config_cache = None


def config(reload=False):
    global _config_cache
    if _config_cache is not None and not reload:
        return _config_cache
    cfg = _DEFAULT_CONFIG
    for path in _config_candidates():
        if not os.path.isfile(path):
            continue
        try:
            loaded = miniyaml.load(path) or {}
            cfg = _deep_merge(json.loads(json.dumps(cfg)), loaded)
        except Exception as exc:  # pragma: no cover - 配置坏了也不能让流程死
            warn("config/defaults.yaml 解析失败(%s)，使用内置默认值" % exc)
        break
    _config_cache = cfg
    return cfg


def _deep_merge(base, extra):
    for k, v in (extra or {}).items():
        if isinstance(v, dict) and isinstance(base.get(k), dict):
            _deep_merge(base[k], v)
        else:
            base[k] = v
    return base


def path(key):
    """取配置里的路径，返回绝对路径。"""
    rel = config()["paths"][key]
    if os.path.isabs(rel):
        return rel
    return os.path.join(PROJECT_ROOT, rel)


def abspath(p):
    if os.path.isabs(p):
        return p
    return os.path.abspath(os.path.join(os.getcwd(), p))


def ensure_dirs():
    for key in config()["paths"]:
        d = path(key)
        if not os.path.exists(d):
            os.makedirs(d, exist_ok=True)


def which(name):
    return shutil.which(name)


def run(cmd, timeout=600, capture=True):
    """跑外部命令，永不抛异常。返回 (rc, stdout, stderr)。"""
    try:
        proc = subprocess.run(
            cmd,
            stdout=subprocess.PIPE if capture else None,
            stderr=subprocess.PIPE if capture else None,
            timeout=timeout,
        )
        out = proc.stdout.decode("utf-8", "replace") if capture and proc.stdout else ""
        err = proc.stderr.decode("utf-8", "replace") if capture and proc.stderr else ""
        return proc.returncode, out, err
    except FileNotFoundError:
        return 127, "", "command not found: %s" % cmd[0]
    except subprocess.TimeoutExpired:
        return 124, "", "timeout after %ss: %s" % (timeout, " ".join(map(str, cmd)))
    except Exception as exc:
        return 1, "", "%s: %s" % (type(exc).__name__, exc)


def have_python_module(name):
    try:
        __import__(name)
        return True
    except Exception:
        return False


def read_json(path, default=None):
    try:
        with open(path, "r", encoding="utf-8") as fh:
            return json.load(fh)
    except Exception:
        return default


def write_json(path, data):
    ensure_parent(path)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=2)
        fh.write("\n")


def write_text(path, text):
    ensure_parent(path)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(text)


def read_text(path):
    with open(path, "r", encoding="utf-8", errors="replace") as fh:
        return fh.read()


def read_bytes(path, limit=None):
    with open(path, "rb") as fh:
        return fh.read() if limit is None else fh.read(limit)


def ensure_parent(path):
    d = os.path.dirname(os.path.abspath(path))
    if d and not os.path.exists(d):
        os.makedirs(d, exist_ok=True)


def stamp():
    return time.strftime("%Y%m%d_%H%M%S")


def mmss(seconds):
    if seconds is None:
        return "--:--"
    seconds = float(seconds)
    return "%d:%02d" % (int(seconds // 60), int(round(seconds % 60)) if seconds % 60 < 59.5 else 0)


def fmt_clock(seconds):
    if seconds is None:
        return "--:--.--"
    seconds = float(seconds)
    return "%02d:%05.2f" % (int(seconds // 60), seconds % 60)


class Log(object):
    """结构化 run log —— 记录每一步用了什么、降级到什么、是否影响结果。"""

    def __init__(self, name):
        self.name = name
        self.steps = []
        self.warnings = []
        self.errors = []
        self.fallbacks = []

    def step(self, action, status="ok", detail="", source=None):
        self.steps.append({
            "action": action,
            "status": status,
            "detail": detail,
            "source": source,
        })
        if status != "ok":
            echo("[%s] %s: %s" % (status, action, detail))
        return self

    def fallback(self, wanted, used, impact):
        entry = {"wanted": wanted, "used": used, "impact": impact}
        self.fallbacks.append(entry)
        echo("[fallback] %s 不可用 → 改用 %s（影响：%s）" % (wanted, used, impact))
        return self

    def warn(self, msg):
        self.warnings.append(msg)
        echo("[warn] %s" % msg)
        return self

    def error(self, msg):
        self.errors.append(msg)
        echo("[error] %s" % msg)
        return self

    def to_dict(self):
        return {
            "script": self.name,
            "steps": self.steps,
            "fallbacks": self.fallbacks,
            "warnings": self.warnings,
            "errors": self.errors,
        }

    def save(self):
        out = os.path.join(path("workspace_analysis"), "runlog_%s.json" % self.name)
        write_json(out, self.to_dict())
        return out


def echo(msg):
    """--json 模式下人类可读信息走 stderr，保证 stdout 是**纯 JSON**。"""
    stream = sys.stderr if _JSON_MODE[0] else sys.stdout
    stream.write(str(msg) + "\n")
    stream.flush()


def emit(obj, as_json):
    """统一输出：--json 给机器（stdout 纯 JSON），默认给人。"""
    if as_json:
        sys.stdout.write(json.dumps(obj, ensure_ascii=False, indent=2) + "\n")
        sys.stdout.flush()
    return obj


def add_common_args(parser):
    """所有脚本共用的两个参数：--json / --project。"""
    parser.add_argument("--json", action="store_true", help="机器可读输出（stdout 纯 JSON）")
    parser.add_argument("--project", default=None,
                        help="覆盖项目根目录（默认=脚本所在项目）")
    return parser


def apply_common_args(args):
    if getattr(args, "project", None):
        set_project_root(args.project)
    if getattr(args, "json", False):
        json_mode(True)
    ensure_dirs()


def die(msg, code=2):
    echo("FATAL: %s" % msg)
    sys.exit(code)


def stdout_utf8():
    try:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    except Exception:
        pass
