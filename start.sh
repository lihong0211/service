#!/usr/bin/env bash
# 生产启动脚本：释放旧进程占用的端口，再以 nohup 方式启动 uvicorn（多 worker，日志写入 nohup.out）
set -e

cd "$(dirname "$0")"

PORT="${PORT:-3000}"

fuser -k "${PORT}"/tcp || true
sleep 2
nohup python3 -m uvicorn app.app:app --host 0.0.0.0 --port "${PORT}" --workers 4 > nohup.out 2>&1 &

echo "started uvicorn on port ${PORT} (pid $!)"
