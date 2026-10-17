#!/usr/bin/env bash
# 모든 실습 스크립트가 source 하는 공통 환경 (사용법: source scripts/env.sh)
LAB_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
set -a; [ -f "$LAB_ROOT/lab.env" ] && source "$LAB_ROOT/lab.env"; set +a

# Homebrew 로 설치한 dotnet 은 DOTNET_ROOT 가 필요하다 (공식 설치 프로그램은 불필요)
if [ -z "${DOTNET_ROOT:-}" ] && command -v brew >/dev/null 2>&1 && brew --prefix dotnet >/dev/null 2>&1; then
  export DOTNET_ROOT="$(brew --prefix dotnet)/libexec"
fi
export PATH="$PATH:$HOME/.dotnet/tools"

# 실습용 Azure CLI 로그인은 별도 구성 디렉터리를 쓸 수 있다(개인 az 로그인과 분리). 필요 시 lab.env 에서 지정.
[ -n "${CSLAB_AZURE_CONFIG_DIR:-}" ] && export AZURE_CONFIG_DIR="$CSLAB_AZURE_CONFIG_DIR"

ENV_URL="${CSLAB_DATAVERSE_URL:?lab.env 에 CSLAB_DATAVERSE_URL 이 필요합니다}"
WS="$LAB_ROOT/workspaces"          # pac copilot init 이 만드는 에이전트 작업 폴더 (git 제외)
BUILD="$LAB_ROOT/build"            # pack 산출물 등 (git 제외)
PY="$LAB_ROOT/.venv/bin/python"
PLUGIN_DIR="$LAB_ROOT/.cache/copilot-studio-plugin"   # microsoft/copilot-studio-plugin (고정 커밋)
PLUGIN_SHA="4014ae689d1228d86cb3aaab938b1e66f8e2e10d"
mkdir -p "$WS" "$BUILD" "$LAB_ROOT/evidence"

log() { printf '\n\033[1;34m▶ %s\033[0m\n' "$*"; }

# 에이전트 작업 폴더를 만들고(없을 때만) 클라우드에 에이전트를 생성한다.
#   ws_init <표시이름> <폴더> [classic|cli-copilot] [instructions]
ws_init() {
  local name="$1" dir="$WS/$2" mode="${3:-classic}" instr="${4:-You triage GitHub issues.}"
  if [ -d "$dir/.mcs" ]; then echo "이미 존재: $dir (건너뜀)"; return 0; fi
  local args=(copilot init --name "$name" --environment "$ENV_URL" --project-dir "$dir"
              --publisher-prefix hlab --instructions "$instr")
  if [ "$mode" = "cli-copilot" ]; then args+=(--authoring-mode cli-copilot); else args+=(--template minimal); fi
  pac "${args[@]}"
}
# 안전한 동기화: pull → push (publishedOn 때문에 생기는 거짓 충돌을 피하려면 publish 직후 pull 이 필수)
ws_sync() { local dir="$WS/$1"; pac copilot pull --project-dir "$dir" && pac copilot push --project-dir "$dir"; }
ws_publish() { pac copilot publish --bot "$1" --environment "$ENV_URL" && pac copilot pull --project-dir "$WS/$2"; }
