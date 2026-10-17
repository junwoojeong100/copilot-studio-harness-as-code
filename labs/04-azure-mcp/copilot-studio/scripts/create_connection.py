#!/usr/bin/env python3
"""커스텀 커넥터(API 키)용 연결(connection)을 Power Apps 연결 REST API 로 만든다 (멱등).

  python3 scripts/create_connection.py --connector-id shared_new-5fissue-... [--env-id Default-<tenant>] [--name "Issue Triage MCP (API key)"]

- API 키는 labs/04-azure-mcp/.env.local 의 API_KEY 에서 읽어 요청 본문에만 넣는다. 화면/로그에 출력하지 않는다.
- 같은 표시 이름의 연결이 이미 있고 상태가 Connected 이면 새로 만들지 않고 그 ID 를 출력한다.
- 마지막 stdout 줄 = 연결 ID(connection name).  나머지 진행 로그는 stderr.
- 토큰: `az account get-access-token --resource https://service.powerapps.com/` (AZURE_CONFIG_DIR 은 호출자가 설정).
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request
import uuid
from pathlib import Path

LAB04 = Path(__file__).resolve().parent.parent.parent
ENV_FILE = LAB04 / ".env.local"
API_VERSION = "2016-11-01"
HOST = "https://api.powerapps.com"


def log(msg: str) -> None:
    print(msg, file=sys.stderr)


def read_env_local(key: str) -> str:
    for line in ENV_FILE.read_text().splitlines():
        if line.startswith(key + "="):
            return line.split("=", 1)[1].strip()
    sys.exit(f"{key} 를 {ENV_FILE} 에서 찾지 못했습니다.")


def token() -> str:
    out = subprocess.run(
        ["az", "account", "get-access-token", "--resource", "https://service.powerapps.com/",
         "--query", "accessToken", "-o", "tsv"],
        check=True, capture_output=True, text=True)
    return out.stdout.strip()


def call(method: str, url: str, tok: str, body: dict | None = None) -> tuple[int, dict]:
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method, headers={
        "Authorization": f"Bearer {tok}", "Accept": "application/json", "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            raw = r.read().decode()
            return r.status, (json.loads(raw) if raw else {})
    except urllib.error.HTTPError as e:
        raw = e.read().decode()
        try:
            return e.code, json.loads(raw)
        except json.JSONDecodeError:
            return e.code, {"raw": raw[:500]}


def summarize(conn: dict) -> dict:
    p = conn.get("properties", {})
    return {
        "name": conn.get("name"),
        "displayName": p.get("displayName"),
        "createdBy": (p.get("createdBy") or {}).get("userPrincipalName") or (p.get("createdBy") or {}).get("displayName"),
        "statuses": [s.get("status") for s in p.get("statuses", [])],
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--connector-id", required=True, help="예: shared_new-5fissue-20triage-20mcp-5f5425e841e7aedf00")
    ap.add_argument("--env-id", required=True, help="예: Default-8109d700-b6b0-4088-ba33-dc39ef13d7ea")
    ap.add_argument("--name", default="Issue Triage MCP (API key)")
    ap.add_argument("--api-key-env", help="(음성 테스트용) .env.local 대신 이 환경 변수의 값을 키로 사용")
    a = ap.parse_args()

    tok = token()
    base = f"{HOST}/providers/Microsoft.PowerApps/apis/{a.connector_id}/connections"
    flt = urllib.parse.quote(f"environment eq '{a.env_id}'")

    code, listing = call("GET", f"{base}?api-version={API_VERSION}&$filter={flt}", tok)
    if code != 200:
        sys.exit(f"연결 목록 조회 실패 HTTP {code}: {json.dumps(listing)[:400]}")
    for c in listing.get("value", []):
        s = summarize(c)
        if s["displayName"] == a.name and "Connected" in s["statuses"]:
            log(f"[reuse] 같은 이름의 연결이 이미 있습니다: {json.dumps(s)}")
            print(s["name"])
            return 0

    conn_name = uuid.uuid4().hex                      # 연결 ID (32자리 hex)
    body = {"properties": {
        "environment": {"id": f"/providers/Microsoft.PowerApps/environments/{a.env_id}", "name": a.env_id},
        "displayName": a.name,
        "connectionParameters": {"api_key": os.environ[a.api_key_env] if a.api_key_env else read_env_local("API_KEY")},
    }}
    code, created = call("PUT", f"{base}/{conn_name}?api-version={API_VERSION}&$filter={flt}", tok, body)
    if code not in (200, 201):
        sys.exit(f"연결 생성 실패 HTTP {code}: {json.dumps(created)[:600]}")
    log(f"[created] HTTP {code}: {json.dumps(summarize(created))}")
    print(created.get("name", conn_name))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
