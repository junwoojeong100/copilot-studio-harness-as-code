#!/usr/bin/env python3
"""Dataverse 에 연결 참조(connectionreferences 행)를 만들고 연결(connection)에 바인딩한다 (멱등).

  python3 scripts/create_connection_reference.py --dataverse-url https://orgXXXX.crm3.dynamics.com/ \
      --logical-name 'hlab_IssueTriageMCP.cr.<connectorName>.<connectionId>' \
      --display-name 'Issue Triage MCP (API key)' \
      --connector-name shared_new-5fissue-... --connection-id beff...

- 이미 같은 logical name 이 있으면 connectionid / connectorid 만 맞춰서 PATCH 한다.
- 이 행이 Dataverse 에 없으면 `pac copilot push` 가
  "A record with the specified key values does not exist in connectionreference entity" 로 실패한다.
- 비밀값은 다루지 않는다(연결 ID 만 사용). 마지막 stdout 줄 = connectionreferenceid.
- 토큰: `az account get-access-token --resource <dataverse-url>` (AZURE_CONFIG_DIR 은 호출자가 설정).
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request


def token(resource: str) -> str:
    out = subprocess.run(["az", "account", "get-access-token", "--resource", resource,
                          "--query", "accessToken", "-o", "tsv"], check=True, capture_output=True, text=True)
    return out.stdout.strip()


def call(method: str, url: str, tok: str, body: dict | None = None) -> tuple[int, dict, dict]:
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method, headers={
        "Authorization": f"Bearer {tok}", "Accept": "application/json", "OData-Version": "4.0",
        "Content-Type": "application/json", "Prefer": "return=representation"})
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            raw = r.read().decode()
            return r.status, (json.loads(raw) if raw else {}), dict(r.headers)
    except urllib.error.HTTPError as e:
        raw = e.read().decode()
        try:
            return e.code, json.loads(raw), {}
        except json.JSONDecodeError:
            return e.code, {"raw": raw[:500]}, {}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataverse-url", required=True)
    ap.add_argument("--logical-name", required=True)
    ap.add_argument("--display-name", required=True)
    ap.add_argument("--connector-name", required=True, help="예: shared_new-5fissue-20triage-20mcp-5f5425e841e7aedf00")
    ap.add_argument("--connection-id", required=True)
    a = ap.parse_args()

    base = a.dataverse_url.rstrip("/") + "/api/data/v9.2/connectionreferences"
    tok = token(a.dataverse_url.rstrip("/"))
    connector_id = f"/providers/Microsoft.PowerApps/apis/{a.connector_name}"
    flt = urllib.parse.quote(f"connectionreferencelogicalname eq '{a.logical_name}'")
    code, found, _ = call("GET", f"{base}?$select=connectionreferenceid,connectionid,connectorid&$filter={flt}", tok)
    if code != 200:
        sys.exit(f"조회 실패 HTTP {code}: {json.dumps(found)[:500]}")

    if found.get("value"):
        row = found["value"][0]
        if row.get("connectionid") != a.connection_id or row.get("connectorid") != connector_id:
            code, upd, _ = call("PATCH", f"{base}({row['connectionreferenceid']})", tok,
                                {"connectionid": a.connection_id, "connectorid": connector_id})
            if code not in (200, 204):
                sys.exit(f"갱신 실패 HTTP {code}: {json.dumps(upd)[:500]}")
            print(f"[update] connectionreference {row['connectionreferenceid']} -> connection {a.connection_id}", file=sys.stderr)
        else:
            print(f"[reuse] connectionreference {row['connectionreferenceid']} (이미 바인딩됨)", file=sys.stderr)
        print(row["connectionreferenceid"])
        return 0

    code, created, _ = call("POST", base, tok, {
        "connectionreferencelogicalname": a.logical_name,
        "connectionreferencedisplayname": a.display_name,
        "connectorid": connector_id,
        "connectionid": a.connection_id,
    })
    if code not in (200, 201):
        sys.exit(f"생성 실패 HTTP {code}: {json.dumps(created)[:700]}")
    print(f"[created] HTTP {code} connectionreferenceid={created.get('connectionreferenceid')}", file=sys.stderr)
    print(created["connectionreferenceid"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
