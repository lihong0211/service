#!/usr/bin/env bash
# 部署脚本：SSH 到阿里云服务器（密码登录），git pull 最新代码后执行 start.sh 重启服务。
#
# 用法：./deploy.sh
# 配置（DEPLOY_HOST/DEPLOY_USER/DEPLOY_PASSWORD/DEPLOY_PATH）读取自 .env
# （已加入 .gitignore，不会被提交到 git 历史；改 IP/密码直接编辑 .env）。
set -euo pipefail

cd "$(dirname "$0")"

ENV_FILE=".env"
if [ ! -f "$ENV_FILE" ]; then
  echo "缺少 $ENV_FILE，请在其中配置 DEPLOY_HOST / DEPLOY_USER / DEPLOY_PASSWORD / DEPLOY_PATH" >&2
  exit 1
fi
# shellcheck disable=SC1090
source "$ENV_FILE"

: "${DEPLOY_HOST:?.env 缺少 DEPLOY_HOST}"
: "${DEPLOY_USER:?.env 缺少 DEPLOY_USER}"
: "${DEPLOY_PASSWORD:?.env 缺少 DEPLOY_PASSWORD}"
: "${DEPLOY_PATH:?.env 缺少 DEPLOY_PATH}"

if ! command -v sshpass >/dev/null 2>&1; then
  echo "缺少 sshpass（密码方式非交互 SSH 需要），先执行：brew install sshpass" >&2
  exit 1
fi

echo "==> 连接 ${DEPLOY_USER}@${DEPLOY_HOST}，部署 ${DEPLOY_PATH}"

sshpass -p "$DEPLOY_PASSWORD" ssh -o StrictHostKeyChecking=accept-new "${DEPLOY_USER}@${DEPLOY_HOST}" bash -s <<REMOTE_SCRIPT
set -e
cd "${DEPLOY_PATH}"
echo "==> git pull"
git pull
echo "==> 执行 start.sh"
bash start.sh
REMOTE_SCRIPT

echo "==> 部署完成"
