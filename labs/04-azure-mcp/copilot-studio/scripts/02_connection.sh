#!/usr/bin/env bash
# 커넥터용 연결(API 키) 만들기 — 같은 이름의 Connected 연결이 있으면 재사용. 키는 .env.local 에서 읽고 출력하지 않는다.
# (음성 테스트: API_KEY_ENV=NEG_KEY NEG_KEY=wrong ./scripts/02_connection.sh)
. "$(dirname "$0")/_env.sh"
. "$STATE_DIR/connector.env"
extra=()
[ -n "${API_KEY_ENV:-}" ] && extra=(--api-key-env "$API_KEY_ENV")
CONNECTION_ID="$(python3 "$HERE/create_connection.py" --connector-id "$CONNECTOR_NAME" --env-id "$CSLAB_ENV_ID" --name "$CONNECTION_NAME" "${extra[@]+"${extra[@]}"}" | tail -1)"
printf 'CONNECTION_ID=%s\n' "$CONNECTION_ID" > "$STATE_DIR/connection.env"
log "connection id=$CONNECTION_ID"
