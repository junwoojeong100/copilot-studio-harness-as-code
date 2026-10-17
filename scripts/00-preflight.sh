#!/usr/bin/env bash
# 사전 점검: 도구 버전 · 로그인 · 환경 · 라이선스 · Copilot Credits(과금 정책) 상태를 읽기 전용으로 확인한다.
set -uo pipefail
source "$(dirname "$0")/env.sh"
ok()   { printf '  \033[32m✔\033[0m %s\n' "$*"; }
warn() { printf '  \033[33m!\033[0m %s\n' "$*"; }

log "1) 도구 버전"
printf '  pac     : %s\n' "$(pac --version 2>&1 | sed -n 2p)"
printf '  az      : %s\n' "$(az version --query '"azure-cli"' -o tsv 2>/dev/null)"
printf '  node    : %s\n  python  : %s\n  dotnet  : %s\n' "$(node --version)" "$("$PY" --version 2>&1)" "$(dotnet --version)"
PACV=$(pac --version 2>&1 | sed -n 2p | sed -E 's/Version: ([0-9]+\.[0-9]+).*/\1/')
python3 - "$PACV" <<'PYEOF' && ok "pac 버전 조건 충족 (≥ 2.13)" || warn "pac 2.13 이상 필요: dotnet tool update -g Microsoft.PowerApps.CLI.Tool"
import sys; a,b=map(int,sys.argv[1].split('.')[:2]); sys.exit(0 if (a,b)>=(2,13) else 1)
PYEOF

log "2) 로그인 상태"
az account show --query '{user:user.name, tenant:tenantId, subscription:id}' -o tsv 2>/dev/null | tr '\t' ' ' | sed 's/^/  az  : /' || warn "az 로그인 필요"
pac auth list 2>/dev/null | grep '\*' | sed 's/^/  pac : /' || warn "pac 프로필 필요"

log "3) 환경 (Copilot Studio / Dataverse)"
pac env who 2>&1 | grep -E "Friendly Name|Environment ID|Org URL|User Email" | sed 's/^/  /'
az rest --resource https://api.bap.microsoft.com/ --method get \
  --url "https://api.bap.microsoft.com/providers/Microsoft.BusinessAppPlatform/scopes/admin/environments/${CSLAB_ENV_ID}?api-version=2021-04-01" \
  --query '{region:properties.azureRegion, sku:properties.environmentSku, dataverse:properties.linkedEnvironmentMetadata.instanceState}' -o tsv 2>/dev/null | sed 's/^/  region·sku·dataverse: /'

log "4) 라이선스 (Microsoft Graph)"
az rest --resource https://graph.microsoft.com --method get --url "https://graph.microsoft.com/v1.0/me/licenseDetails" \
  --query "value[].servicePlans[?contains(servicePlanName,'COPILOT_STUDIO') || servicePlanName=='VIRTUAL_AGENT_USL' || servicePlanName=='M365_COPILOT_BUSINESS_CHAT' || servicePlanName=='AGENT_365'].servicePlanName" -o tsv 2>/dev/null | sort -u | sed 's/^/  /'

log "5) Copilot Credits 과금 정책 (Power Platform API) — 비어 있어도 선불 용량으로 동작할 수 있음"
az rest --resource https://api.powerplatform.com --method get \
  --url "https://api.powerplatform.com/licensing/billingPolicies?api-version=2024-10-01" --query "length(value)" -o tsv 2>/dev/null | sed 's/^/  billingPolicies: /'

log "6) 환경에 이미 있는 다른 에이전트 수 (실습은 이 에이전트들을 건드리지 않음)"
printf '  %s 개\n' "$(pac copilot list --environment "$ENV_URL" 2>/dev/null | awk 'NR>1 && NF' | grep -vc 'Issue Triage')"
