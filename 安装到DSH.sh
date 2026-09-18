#!/usr/bin/env bash
# 中文别名 —— 真正干活的是 install-to-dsh.sh
exec "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/install-to-dsh.sh" "$@"
