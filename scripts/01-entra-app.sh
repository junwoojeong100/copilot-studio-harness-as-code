#!/usr/bin/env bash
# SDK/Graph 호출용 Entra 공용 클라이언트 앱 등록 (코드만으로). 결과 appId 를 lab.env 의 CSLAB_CLIENT_ID 에 기록한다.
set -euo pipefail
source "$(dirname "$0")/env.sh"
NAME="csharness-lab-sdk-client"
PPAPI=8578e004-a5c6-46e7-913e-12f58912df43      # Power Platform API
GRAPH=00000003-0000-0000-c000-000000000000       # Microsoft Graph

# Power Platform API 서비스 주체가 테넌트에 없으면 만든다
az ad sp show --id "$PPAPI" >/dev/null 2>&1 || az ad sp create --id "$PPAPI" >/dev/null

scope_id() { az ad sp show --id "$1" --query "oauth2PermissionScopes[?value=='$2'].id | [0]" -o tsv; }

EXISTING=$(az ad app list --display-name "$NAME" --query "[0].appId" -o tsv)
if [ -n "$EXISTING" ]; then APP="$EXISTING"; echo "기존 앱 사용: $APP"; else
  cat > "$BUILD/req-access.json" <<JSON
[{"resourceAppId":"$PPAPI","resourceAccess":[{"id":"$(scope_id $PPAPI CopilotStudio.Copilots.Invoke)","type":"Scope"}]}]
JSON
  APP=$(az ad app create --display-name "$NAME" --sign-in-audience AzureADMyOrg \
        --is-fallback-public-client true --public-client-redirect-uris "http://localhost" \
        --required-resource-accesses @"$BUILD/req-access.json" --query appId -o tsv)
  sleep 5; az ad sp create --id "$APP" >/dev/null
  echo "앱 생성: $APP"
fi
# Copilot chat harness(Teams 앱 카탈로그) 배포용 Graph 위임 권한 추가
for s in AppCatalog.ReadWrite.All TeamsAppInstallation.ReadWriteForUser User.Read; do
  az ad app permission add --id "$APP" --api $GRAPH --api-permissions "$(scope_id $GRAPH $s)=Scope" >/dev/null 2>&1 || true
done
sleep 4; az ad app permission admin-consent --id "$APP" 2>&1 | tail -1 || true
az ad app permission list-grants --id "$APP" --query "[].scope" -o tsv | sed 's/^/동의된 권한: /'

grep -q '^CSLAB_CLIENT_ID=' "$LAB_ROOT/lab.env" \
  && sed -i.bak "s/^CSLAB_CLIENT_ID=.*/CSLAB_CLIENT_ID=$APP/" "$LAB_ROOT/lab.env" && rm -f "$LAB_ROOT/lab.env.bak" \
  || echo "CSLAB_CLIENT_ID=$APP" >> "$LAB_ROOT/lab.env"
echo "lab.env 에 CSLAB_CLIENT_ID=$APP 기록"
