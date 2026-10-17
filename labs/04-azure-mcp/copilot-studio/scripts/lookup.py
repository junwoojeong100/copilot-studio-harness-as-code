#!/usr/bin/env python3
"""Dataverse 조회 도우미 (읽기 전용, 비밀값 없음). 결과가 없으면 아무것도 출력하지 않는다.

  python3 scripts/lookup.py connector --dataverse-url URL --title "Issue Triage MCP"
      -> <connectorid>\t<name>\t<connectorinternalid>          (pac connector list 는 internal id 를 보여 주지 않는다)
  python3 scripts/lookup.py agent --dataverse-url URL --schema hlab_IssueTriageMCP
      -> <botid>\t<schemaname>\t<name>
  python3 scripts/lookup.py connref --dataverse-url URL --logical-name <connectionreferencelogicalname>
      -> <connectionreferenceid>\t<connectionid>\t<connectorid>

토큰: `az account get-access-token --resource <dataverse-url>` (AZURE_CONFIG_DIR 은 호출자가 설정).
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


def get(url: str, tok: str) -> dict:
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {tok}", "Accept": "application/json",
                                               "OData-Version": "4.0"})
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            return json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        sys.exit(f"HTTP {e.code}: {e.read().decode()[:400]}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("kind", choices=["connector", "agent", "connref"])
    ap.add_argument("--dataverse-url", required=True)
    ap.add_argument("--title")
    ap.add_argument("--schema")
    ap.add_argument("--logical-name")
    a = ap.parse_args()
    base = a.dataverse_url.rstrip("/") + "/api/data/v9.2"
    tok = token(a.dataverse_url.rstrip("/"))
    q = urllib.parse.quote

    if a.kind == "connector":
        flt = q(f"displayname eq '{a.title}' and connectortype eq 1")
        rows = get(f"{base}/connectors?$select=connectorid,name,connectorinternalid&$filter={flt}", tok)["value"]
        for r in rows:
            print(f"{r['connectorid']}\t{r['name']}\t{r['connectorinternalid']}")
    elif a.kind == "agent":
        rows = get(f"{base}/bots?$select=botid,schemaname,name&$filter={q(f'schemaname eq {chr(39)}{a.schema}{chr(39)}')}", tok)["value"]
        for r in rows:
            print(f"{r['botid']}\t{r['schemaname']}\t{r['name']}")
    else:
        flt = q(f"connectionreferencelogicalname eq '{a.logical_name}'")
        rows = get(f"{base}/connectionreferences?$select=connectionreferenceid,connectionid,connectorid&$filter={flt}", tok)["value"]
        for r in rows:
            print(f"{r['connectionreferenceid']}\t{r.get('connectionid')}\t{r.get('connectorid')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
