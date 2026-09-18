#!/usr/bin/env bash
# 2d-limited-mv-studio · 可选能力安装（核心管线零依赖，这些只是加分项）
#
#   bash scripts/setup_env.sh            # numpy/librosa/soundfile/scipy
#   bash scripts/setup_env.sh --asr      # 追加 faster-whisper
#   bash scripts/setup_env.sh --demucs   # 追加 demucs（人声分离）
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

ASR=0
DEMUCS=0
for a in "$@"; do
  case "$a" in
    --asr) ASR=1 ;;
    --demucs) DEMUCS=1 ;;
    *) echo "未知参数：$a"; exit 2 ;;
  esac
done

PY=${PYTHON:-python3}
if [ ! -d .venv ]; then
  echo "① 建虚拟环境 .venv"
  "$PY" -m venv .venv
fi
# shellcheck disable=SC1091
source .venv/bin/activate

echo "② 升级 pip"
python -m pip install --quiet --upgrade pip

echo "③ 安装分析依赖"
python -m pip install --quiet numpy scipy soundfile librosa

if [ "$ASR" = "1" ]; then
  echo "④ 安装 ASR（faster-whisper）"
  python -m pip install --quiet faster-whisper
fi
if [ "$DEMUCS" = "1" ]; then
  echo "⑤ 安装人声分离（demucs）"
  python -m pip install --quiet demucs
fi

echo
echo "⑥ 体检"
python scripts/mvstudio.py doctor

cat <<'TIP'

提示：
  * 想要任意格式音频都能自动切分 → brew install ffmpeg
  * 激活环境后再跑：source .venv/bin/activate && python scripts/mvstudio.py all
  * ASR 结果只能当草稿，必须人工核对（实测把「王子」转成过「滑走」）
TIP
