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

# 整个部署过程的超时兜底：正常 git pull + 重启几秒到几十秒内完成，
# 给够余量但不无限等——万一远端卡在某个交互输入（凭据失效/host key 确认等）
# 不会一直挂着，超时会中止并报错，而不是静默无响应。
DEPLOY_TIMEOUT="${DEPLOY_TIMEOUT:-180}"
TIMEOUT_BIN="$(command -v timeout || command -v gtimeout || true)"
if [ -z "$TIMEOUT_BIN" ]; then
  echo "缺少 timeout/gtimeout（超时兜底需要），先执行：brew install coreutils" >&2
  exit 1
fi

echo "==> 连接 ${DEPLOY_USER}@${DEPLOY_HOST}，部署 ${DEPLOY_PATH}（超时 ${DEPLOY_TIMEOUT}s）"

set +e
"$TIMEOUT_BIN" "$DEPLOY_TIMEOUT" sshpass -p "$DEPLOY_PASSWORD" \
  ssh -o StrictHostKeyChecking=accept-new -o ConnectTimeout=15 \
  "${DEPLOY_USER}@${DEPLOY_HOST}" bash -s <<REMOTE_SCRIPT
set -e
# 关掉 git 的交互式凭据提示：需要输入用户名/密码或确认 host key 时直接失败，
# 而不是在没有 TTY 的非交互 shell 里挂住等一个永远不会来的输入
export GIT_TERMINAL_PROMPT=0
export GIT_SSH_COMMAND="ssh -o BatchMode=yes -o ConnectTimeout=15"
cd "${DEPLOY_PATH}"
echo "==> git pull"
git pull
echo "==> 执行 start.sh"
bash start.sh
REMOTE_SCRIPT
STATUS=$?
set -e

if [ "$STATUS" -eq 124 ]; then
  echo "==> 部署超时（${DEPLOY_TIMEOUT}s），已中止。可能卡在网络或需要交互输入，请登录服务器手动排查" >&2
  exit 124
elif [ "$STATUS" -ne 0 ]; then
  echo "==> 部署失败，退出码 $STATUS" >&2
  exit "$STATUS"
fi

echo "==> 部署完成"
