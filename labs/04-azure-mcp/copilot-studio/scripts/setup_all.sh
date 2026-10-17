#!/usr/bin/env bash
# 처음부터 끝까지: 커넥터 -> 연결 -> 에이전트(연결 참조/도구/지시문/게시) -> 테스트. 여러 번 실행해도 안전하다.
set -euo pipefail
D="$(cd "$(dirname "$0")" && pwd)"
"$D/01_connector.sh"
"$D/02_connection.sh"
"$D/03_agent.sh"
"$D/04_test.sh"
