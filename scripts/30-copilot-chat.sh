#!/usr/bin/env bash
# Copilot chat harness: 선언형 에이전트를 코드(JSON 매니페스트)로 만들고 Microsoft Graph 로 배포
#   사용: 30-copilot-chat.sh [버전]   예) 30-copilot-chat.sh 1.0.1   (재배포 시 버전을 올려야 함)
set -euo pipefail
source "$(dirname "$0")/env.sh"
VER="${1:-1.0.0}"; D="$LAB_ROOT/labs/03-copilot-chat"

log "1) 패키지 생성 (manifest.json + declarativeAgent.json + 아이콘 → zip)"
"$PY" "$D/build_package.py" --version "$VER"

log "2) 공식 JSON Schema 로 오프라인 검증"
"$PY" "$D/validate_package.py"

log "3) Graph 로 조직 카탈로그 게시 + 관리자 본인에게 설치 (최초 1회 디바이스 코드 로그인)"
"$PY" "$D/m365_publish.py"

cat <<MSG

▶ 4) 런타임 확인: https://m365.cloud.microsoft/chat → 왼쪽 'Agents' → 'Issue Triage Copilot' 에서 shared/test-cases.yaml 의 입력을 붙여 넣어 보세요.
   (Copilot chat harness 에이전트는 SDK/REST 로 직접 대화할 수 없어 UI 로 최종 확인합니다)
MSG
