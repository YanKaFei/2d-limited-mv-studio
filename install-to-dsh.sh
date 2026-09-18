#!/usr/bin/env bash
# 把 anime-mv-studio 装到某个 DSH 项目（软链，便于原地修改）
#
#   bash install-to-dsh.sh                     # 默认装到当前目录
#   bash install-to-dsh.sh /path/to/project
set -euo pipefail

SRC="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEST_ROOT="${1:-$(pwd)}"
DEST="$DEST_ROOT/.dsh/skills"

mkdir -p "$DEST"

if [ -e "$DEST/anime-mv-studio" ] || [ -L "$DEST/anime-mv-studio" ]; then
  echo "已存在 $DEST/anime-mv-studio —— 先备份为 anime-mv-studio.bak"
  rm -rf "$DEST/anime-mv-studio.bak"
  mv "$DEST/anime-mv-studio" "$DEST/anime-mv-studio.bak"
fi

ln -s "$SRC" "$DEST/anime-mv-studio"
echo "✅ 已安装：$DEST/anime-mv-studio → $SRC"
echo
echo "自检："
python3 "$SRC/scripts/mvstudio.py" doctor || true
echo
echo "在 DSH 里说「做一条 MV」即可加载本技能。"
