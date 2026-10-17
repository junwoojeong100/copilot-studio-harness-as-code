# shellcheck shell=bash
# source 해서 사용한다. 환경 변수로 이름을 바꿀 수 있다 (기본값 = 이 랩의 값).
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CS_DIR="$(cd "$HERE/.." && pwd)"                    # .../labs/04-azure-mcp/copilot-studio
LAB04="$(cd "$CS_DIR/.." && pwd)"                   # .../labs/04-azure-mcp
LAB_ROOT="$(cd "$LAB04/../.." && pwd)"              # .../CopilotStudio_Harness_CodeLab

# pac (dotnet tool). macOS + Homebrew dotnet 이면 DOTNET_ROOT 도 필요하다.
command -v pac >/dev/null 2>&1 || export PATH="$PATH:$HOME/.dotnet/tools"
if [ -z "${DOTNET_ROOT:-}" ] && [ -d /opt/homebrew/opt/dotnet/libexec ]; then export DOTNET_ROOT=/opt/homebrew/opt/dotnet/libexec; fi
command -v pac >/dev/null 2>&1 || { echo "pac 를 찾을 수 없습니다 (dotnet tool install --global Microsoft.PowerApps.CLI.Tool)" >&2; exit 1; }

# lab.env: CSLAB_TENANT_ID / CSLAB_ENV_ID / CSLAB_DATAVERSE_URL ...
set -a; . "$LAB_ROOT/lab.env"; set +a
: "${CSLAB_ENV_ID:?lab.env 에 CSLAB_ENV_ID 가 필요합니다}"
: "${CSLAB_DATAVERSE_URL:?lab.env 에 CSLAB_DATAVERSE_URL 가 필요합니다}"

# 격리된 az 로그인(CSLAB_AZURE_CONFIG_DIR)이 lab.env 에 있으면 그것을 쓴다. 없으면 현재 az 로그인을 그대로 쓴다.
if [ -z "${AZURE_CONFIG_DIR:-}" ] && [ -n "${CSLAB_AZURE_CONFIG_DIR:-}" ]; then export AZURE_CONFIG_DIR="$CSLAB_AZURE_CONFIG_DIR"; fi

AGENT_NAME="${AGENT_NAME:-Issue Triage MCP}"
PUBLISHER_PREFIX="${PUBLISHER_PREFIX:-hlab}"
AGENT_SCHEMA="${AGENT_SCHEMA:-${PUBLISHER_PREFIX}_$(printf '%s' "$AGENT_NAME" | tr -d ' ')}"     # hlab_IssueTriageMCP
CONNECTOR_TITLE="${CONNECTOR_TITLE:-Issue Triage MCP}"                                          # 30자 이하 (pac 제한)
CONNECTION_NAME="${CONNECTION_NAME:-$CONNECTOR_TITLE (API key)}"
WORKDIR="${WORKDIR:-$HOME/.cs-harness-lab/$AGENT_SCHEMA}"                                       # 레포 밖. pac 가 .mcs/ 와 connectors/ 를 만든다
STATE_DIR="$CS_DIR/.state/$AGENT_SCHEMA"                                                         # git 제외, 비밀값 없음(ID 만)
mkdir -p "$STATE_DIR"
export CONNECTOR_TITLE

log() { printf '[%s] %s\n' "$(date '+%H:%M:%S')" "$*" >&2; }
