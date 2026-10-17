#!/usr/bin/env bash
# 실습 리소스 정리. 사용: 99-cleanup.sh --mcp | --agents | --m365 | --entra | --azure | --all  (--yes 필수)
#   --agents : Copilot Studio 에이전트(hlab_IssueTriage*)와 solution, 로컬 workspaces 삭제
#   --m365   : Teams 앱 카탈로그에 게시한 선언형 에이전트 삭제 (Graph)
#   --mcp    : Lab 4 의 커스텀 커넥터·연결·연결 참조·MCP 에이전트 삭제
#   --azure  : Azure 리소스 그룹(rg-csharness-lab) 삭제
#   --entra  : 실습용 Entra 앱 등록(csharness-lab-sdk-client) 삭제
set -euo pipefail
source "$(dirname "$0")/env.sh"
YES=0; DO=()
for a in "$@"; do case "$a" in --yes) YES=1;; --agents|--m365|--entra|--azure|--mcp) DO+=("$a");; --all) DO=(--mcp --agents --m365 --azure --entra);; esac; done
[ ${#DO[@]} -eq 0 ] && { sed -n '2,7p' "$0"; exit 1; }
[ $YES -eq 1 ] || { echo "삭제 대상: ${DO[*]}  →  실제로 삭제하려면 --yes 를 추가하세요."; exit 1; }

for d in "${DO[@]}"; do
  case "$d" in
  --agents)
    log "Copilot Studio 에이전트·solution 삭제"
    for s in hlab_IssueTriageStandard hlab_IssueTriageStdGen hlab_IssueTriageGitHub hlab_IssueTriageMCP; do
      pac copilot delete --bot "$s" --environment "$ENV_URL" --confirm 2>&1 | tail -1 || true
    done
    for s in HarnessLabStandard hlab_IssueTriageStandard hlab_IssueTriageStdGen hlab_IssueTriageGitHub hlab_IssueTriageMCP; do
      pac solution delete --solution-name "$s" --environment "$ENV_URL" 2>&1 | tail -1 || true
    done
    rm -rf "$WS"/* "$BUILD"/*.zip ;;
  --mcp)
    log "Lab 4: 커넥터·연결·연결 참조·MCP 에이전트 삭제"
    "$LAB_ROOT/labs/04-azure-mcp/copilot-studio/scripts/cleanup.sh" --yes
    rm -rf "$HOME/.cs-harness-lab/hlab_IssueTriageMCP" ;;
  --m365)
    log "Teams 앱 카탈로그에서 선언형 에이전트 삭제"
    "$PY" "$LAB_ROOT/labs/03-copilot-chat/m365_publish.py" --uninstall ;;
  --azure)
    log "Azure 리소스 그룹 삭제"
    az group delete -n rg-csharness-lab --subscription "$CSLAB_SUBSCRIPTION_ID" --yes --no-wait && echo "삭제 요청됨(비동기)" ;;
  --entra)
    log "Entra 앱 등록 삭제"
    az ad app delete --id "$CSLAB_CLIENT_ID" && echo "삭제됨: $CSLAB_CLIENT_ID" ;;
  esac
done
