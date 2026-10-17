#!/usr/bin/env python3
"""연결 참조 / 연결 / 커스텀 커넥터를 삭제한다 (없으면 건너뜀). 에이전트 삭제는 cleanup.sh 가 pac 로 한다.

  python3 scripts/cleanup_resources.py --dataverse-url URL --env-id Default-<tenant> \
      --agent-schema hlab_IssueTriageMCP --connector-title "Issue Triage MCP" --connection-name "Issue Triage MCP (API key)"

삭제 대상은 이름으로 찾은 이 랩의 객체뿐이다: 연결 참조(논리 이름이 '<agent-schema>.cr.' 로 시작) -> 연결(표시 이름 일치) -> 커넥터(표시 이름 일치, 사용자 지정).
토큰: az (resource = Dataverse URL / https://service.powerapps.com/).
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


def call(method: str, url: str, tok: str) -> tuple[int, dict]:
    req = urllib.request.Request(url, method=method, headers={
        "Authorization": f"Bearer {tok}", "Accept": "application/json", "OData-Version": "4.0"})
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            raw = r.read().decode()
            return r.status, (json.loads(raw) if raw else {})
    except urllib.error.HTTPError as e:
        raw = e.read().decode()
        try:
            return e.code, json.loads(raw)
        except json.JSONDecodeError:
            return e.code, {"raw": raw[:300]}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataverse-url", required=True)
    ap.add_argument("--env-id", required=True)
    ap.add_argument("--agent-schema", required=True)
    ap.add_argument("--connector-title", required=True)
    ap.add_argument("--connection-name", required=True)
    ap.add_argument("--only", choices=["connectionreference", "connection", "connector"], action="append",
                    help="지정한 종류만 삭제 (여러 번 지정 가능, 기본: 전부). 음성 테스트(연결만 삭제)용")
    a = ap.parse_args()
    want = set(a.only or ["connectionreference", "connection", "connector"])
    q = urllib.parse.quote
    dv = a.dataverse_url.rstrip("/") + "/api/data/v9.2"
    dtok = token(a.dataverse_url.rstrip("/"))
    ptok = token("https://service.powerapps.com/")
    rc = 0

    # 커넥터 internal id (연결 API 경로에 필요)
    code, body = call("GET", f"{dv}/connectors?$select=connectorid,connectorinternalid&$filter="
                      + q(f"displayname eq '{a.connector_title}' and connectortype eq 1"), dtok)
    connectors = body.get("value", []) if code == 200 else []

    # 1) 연결 참조
    if "connectionreference" in want:
        code, body = call("GET", f"{dv}/connectionreferences?$select=connectionreferenceid,connectionreferencelogicalname&$filter="
                          + q(f"startswith(connectionreferencelogicalname,'{a.agent_schema}.cr.')"), dtok)
        refs = body.get("value", []) if code == 200 else []
        for r in refs:
            c, b = call("DELETE", f"{dv}/connectionreferences({r['connectionreferenceid']})", dtok)
            print(f"[connectionreference] DELETE {r['connectionreferencelogicalname'][:60]}… -> HTTP {c}" + ("" if c in (200, 204) else f" {json.dumps(b)[:300]}"))
            rc |= c not in (200, 204)
        if not refs:
            print("[connectionreference] 없음 (건너뜀)")

    # 2) 연결
    if "connection" in want:
        found = False
        flt = q(f"environment eq '{a.env_id}'")
        for cn in connectors:
            base = f"https://api.powerapps.com/providers/Microsoft.PowerApps/apis/{cn['connectorinternalid']}/connections"
            c, lst = call("GET", f"{base}?api-version=2016-11-01&$filter={flt}", ptok)
            for conn in lst.get("value", []) if c == 200 else []:
                if conn.get("properties", {}).get("displayName") == a.connection_name:
                    found = True
                    c2, b2 = call("DELETE", f"{base}/{conn['name']}?api-version=2016-11-01&$filter={flt}", ptok)
                    print(f"[connection] DELETE {conn['name']} -> HTTP {c2}" + ("" if c2 in (200, 204) else f" {json.dumps(b2)[:300]}"))
                    rc |= c2 not in (200, 204)
        if not found:
            print("[connection] 없음 (건너뜀)")

    # 3) 커스텀 커넥터
    if "connector" in want:
        for cn in connectors:
            c, b = call("DELETE", f"{dv}/connectors({cn['connectorid']})", dtok)
            print(f"[connector] DELETE {cn['connectorinternalid']} -> HTTP {c}" + ("" if c in (200, 204) else f" {json.dumps(b)[:300]}"))
            rc |= c not in (200, 204)
        if not connectors:
            print("[connector] 없음 (건너뜀)")
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
