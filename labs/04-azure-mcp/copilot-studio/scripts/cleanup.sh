#!/usr/bin/env bash
# 이 랩이 만든 것만 지운다: 에이전트 -> (init 이 만든) 솔루션 -> 연결 참조 -> 연결 -> 커스텀 커넥터. 되돌릴 수 없으므로 --yes 가 필요하다.
# Azure 의 MCP 서버(Container App)는 건드리지 않는다 (그건 ../scripts/cleanup.sh).
. "$(dirname "$0")/_env.sh"
[ "${1:-}" = "--yes" ] || { echo "사용법: $0 --yes   (삭제 대상: 에이전트 $AGENT_SCHEMA, 연결 '$CONNECTION_NAME', 커넥터 '$CONNECTOR_TITLE')" >&2; exit 2; }

if [ -n "$(python3 "$HERE/lookup.py" agent --dataverse-url "$CSLAB_DATAVERSE_URL" --schema "$AGENT_SCHEMA")" ]; then
  log "pac copilot delete $AGENT_SCHEMA"
  pac copilot delete --bot "$AGENT_SCHEMA" --environment "$CSLAB_DATAVERSE_URL" --confirm >&2
else
  log "[skip] 에이전트 $AGENT_SCHEMA 없음"
fi
# pac copilot init 은 에이전트와 같은 이름의 (비관리) 솔루션도 만들고, pac copilot delete 는 이를 지우지 않는다.
if pac solution list --environment "$CSLAB_DATAVERSE_URL" 2>/dev/null | awk -v s="$AGENT_SCHEMA" '$1==s{f=1} END{exit !f}'; then
  log "pac solution delete $AGENT_SCHEMA"
  pac solution delete --solution-name "$AGENT_SCHEMA" --environment "$CSLAB_DATAVERSE_URL" >&2
else
  log "[skip] 솔루션 $AGENT_SCHEMA 없음"
fi
python3 "$HERE/cleanup_resources.py" --dataverse-url "$CSLAB_DATAVERSE_URL" --env-id "$CSLAB_ENV_ID" \
  --agent-schema "$AGENT_SCHEMA" --connector-title "$CONNECTOR_TITLE" --connection-name "$CONNECTION_NAME"
rm -rf "$STATE_DIR"
log "로컬 워크스페이스 $WORKDIR 는 직접 지우세요 (rm -rf)."
