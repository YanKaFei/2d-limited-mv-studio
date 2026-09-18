#!/usr/bin/env bash
# 把 mv-prism 装到某个 DSH 项目（软链，便于原地修改）
#
#   bash install-to-dsh.sh                     # 默认装到当前目录
#   bash install-to-dsh.sh /path/to/project
set -euo pipefail

SRC="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEST_ROOT="${1:-$(pwd)}"
DEST="$DEST_ROOT/.dsh/skills"

mkdir -p "$DEST"

if [ -e "$DEST/mv-prism" ] || [ -L "$DEST/mv-prism" ]; then
  echo "已存在 $DEST/mv-prism —— 先备份为 mv-prism.bak"
  rm -rf "$DEST/mv-prism.bak"
  mv "$DEST/mv-prism" "$DEST/mv-prism.bak"
fi

ln -s "$SRC" "$DEST/mv-prism"
echo "✅ 已安装：$DEST/mv-prism → $SRC"
echo
echo "自检："
python3 "$SRC/scripts/prism.py" doctor || true
echo
echo "在 DSH 里说「做一条 MV」即可加载本技能。"
