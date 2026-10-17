#!/usr/bin/env bash
# GitHub Copilot harness 에이전트 + MCP 도구 만들기/갱신/게시 (멱등).
#  1) pac copilot init (워크스페이스가 없고 에이전트도 없을 때만)
#  2) Dataverse 에 연결 참조 행 생성 + 연결에 바인딩  <- push 전에 반드시 (없으면 push 실패)
#  3) agent-overlay 적용 (도구 YAML + 지시문)
#  4) pull -> push -> publish -> pull
. "$(dirname "$0")/_env.sh"
. "$STATE_DIR/connector.env"; . "$STATE_DIR/connection.env"
URL="$CSLAB_DATAVERSE_URL"

if [ ! -f "$WORKDIR/.mcs/conn.json" ]; then
  if [ -n "$(python3 "$HERE/lookup.py" agent --dataverse-url "$URL" --schema "$AGENT_SCHEMA")" ]; then
    echo "에이전트 $AGENT_SCHEMA 는 이미 있지만 워크스페이스($WORKDIR)가 없습니다." >&2
    echo "  pac copilot clone --bot $AGENT_SCHEMA --environment $CSLAB_DATAVERSE_URL --output-dir <부모폴더>   # <부모폴더>/'$AGENT_NAME' 가 생깁니다" >&2
    echo "  그 뒤: WORKDIR='<부모폴더>/$AGENT_NAME' $0" >&2; exit 1
  fi
  log "pac copilot init  ($AGENT_NAME / $AGENT_SCHEMA)"
  pac copilot init --name "$AGENT_NAME" --schema-name "$AGENT_SCHEMA" --environment "$URL" --project-dir "$WORKDIR" \
    --publisher-prefix "$PUBLISHER_PREFIX" --authoring-mode cli-copilot \
    --instructions "You are a GitHub issue triage assistant. Call the MCP tool classify_issue and return its JSON result unchanged." >&2
else
  log "[reuse] 워크스페이스 $WORKDIR"
fi

CONNREF="$AGENT_SCHEMA.cr.$CONNECTOR_NAME.$CONNECTION_ID"
python3 "$HERE/create_connection_reference.py" --dataverse-url "$URL" --logical-name "$CONNREF" \
  --display-name "$CONNECTION_NAME" --connector-name "$CONNECTOR_NAME" --connection-id "$CONNECTION_ID" >&2
printf 'CONNECTION_REFERENCE=%s\n' "$CONNREF" > "$STATE_DIR/connref.env"

python3 "$HERE/render_overlay.py" --workspace "$WORKDIR" --connection-reference "$CONNREF" --connector-name "$CONNECTOR_NAME" >&2

log "pac copilot pull";    pac copilot pull --project-dir "$WORKDIR" >&2
python3 "$HERE/render_overlay.py" --workspace "$WORKDIR" --fix-settings-conflict >&2
log "pac copilot push";    pac copilot push --project-dir "$WORKDIR" >&2
log "pac copilot publish"; pac copilot publish --bot "$AGENT_SCHEMA" --environment "$URL" >&2
log "pac copilot pull (publishedOn 동기화)"; pac copilot pull --project-dir "$WORKDIR" >&2
python3 "$HERE/render_overlay.py" --workspace "$WORKDIR" --fix-settings-conflict >&2
log "완료: $AGENT_SCHEMA  (connection reference: $CONNREF)"
