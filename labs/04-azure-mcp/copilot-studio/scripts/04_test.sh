#!/usr/bin/env bash
# 테스트 하네스로 확인: (1) 한 줄 대화([step] 에서 도구 호출 확인) (2) 5개 케이스.
# 기본 대상은 harness/targets.yaml 의 github-mcp. 다른 에이전트는 TARGET_SCHEMA=<schemaName> 로 (chat 만 실행).
. "$(dirname "$0")/_env.sh"
PY="$LAB_ROOT/.venv/bin/python"
MSG=$'Classify this GitHub issue. Reply with one JSON object using exactly the keys category, priority, team, summary, needsHumanReview.\nTitle: Checkout API returns 503 for all customers\nBody: Started after the latest deployment. No workaround is available.'
if [ -n "${TARGET_SCHEMA:-}" ]; then
  "$PY" "$HERE/chat_schema.py" --schema "$TARGET_SCHEMA" "$MSG"
else
  (cd "$LAB_ROOT/harness" && "$PY" chat.py --target github-mcp "$MSG")
  (cd "$LAB_ROOT/harness" && "$PY" run_cases.py --target github-mcp --out "$CS_DIR/.state/github-mcp-cases.json")
fi
