#!/usr/bin/env bash
# 커스텀 커넥터(MCP) 만들기 — 이미 있으면 재사용. 결과 ID 는 .state/<agent>/connector.env 에 저장.
. "$(dirname "$0")/_env.sh"
OUT="$STATE_DIR/connector"
python3 "$HERE/render_connector.py" --out "$OUT"

row="$(python3 "$HERE/lookup.py" connector --dataverse-url "$CSLAB_DATAVERSE_URL" --title "$CONNECTOR_TITLE" | head -1)"
if [ -n "$row" ]; then
  log "[reuse] 커넥터 '$CONNECTOR_TITLE' 가 이미 있습니다"
else
  log "pac connector create ($CONNECTOR_TITLE)"
  pac connector create --environment "$CSLAB_DATAVERSE_URL" \
    --api-definition-file "$OUT/apiDefinition.swagger.json" --api-properties-file "$OUT/apiProperties.json" >&2
  row="$(python3 "$HERE/lookup.py" connector --dataverse-url "$CSLAB_DATAVERSE_URL" --title "$CONNECTOR_TITLE" | head -1)"
fi
[ -n "$row" ] || { echo "커넥터를 찾지 못했습니다" >&2; exit 1; }
IFS=$'\t' read -r CONNECTOR_ROW_ID CONNECTOR_LOGICAL CONNECTOR_NAME <<<"$row"
printf 'CONNECTOR_ROW_ID=%s\nCONNECTOR_NAME=%s\n' "$CONNECTOR_ROW_ID" "$CONNECTOR_NAME" > "$STATE_DIR/connector.env"
log "connector row=$CONNECTOR_ROW_ID  apiName(connectorinternalid)=$CONNECTOR_NAME"
