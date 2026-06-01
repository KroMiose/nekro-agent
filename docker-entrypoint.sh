#!/bin/sh
set -e

# 确保数据目录存在且权限正确
if [ -n "$NEKRO_DATA_DIR" ]; then
    mkdir -p "$NEKRO_DATA_DIR"
    chown -R nekro:nekro "$NEKRO_DATA_DIR"
fi

exec "$@"
