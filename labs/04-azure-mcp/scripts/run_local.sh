#!/usr/bin/env bash
# Runs the MCP server locally on http://127.0.0.1:8000/mcp (no Docker, no Azure needed).
set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/_common.sh"

sync_shared
ensure_api_key

if [[ ! -x "$LAB_DIR/.venv/bin/python" ]]; then
  log "[venv] creating $LAB_DIR/.venv (set PYTHON=python3.12 to pick an interpreter)"
  "${PYTHON:-python3}" -m venv "$LAB_DIR/.venv"
fi
"$LAB_DIR/.venv/bin/python" -m pip install --quiet --disable-pip-version-check -r "$SERVER_DIR/requirements.txt"

API_KEY="$(env_get API_KEY)"
export API_KEY
export HOST="${HOST:-127.0.0.1}" PORT="${PORT:-8000}"
log "[run] serving http://$HOST:$PORT/mcp  (health: /healthz, Ctrl+C to stop)"
exec "$LAB_DIR/.venv/bin/python" "$SERVER_DIR/server.py"
