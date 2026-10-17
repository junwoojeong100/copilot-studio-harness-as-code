#!/usr/bin/env python3
"""Sync connector/apiDefinition.swagger.json with the deployed endpoint and sanity-check both connector files.

  python scripts/render_connector.py          # set "host" from MCP_ENDPOINT in .env.local, then validate
  python scripts/render_connector.py --check  # validate only (exit 1 if the host does not match MCP_ENDPOINT)

Only the standard library is used. The API key is never read or printed.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from urllib.parse import urlparse

LAB = Path(__file__).resolve().parent.parent
SWAGGER = LAB / "connector" / "apiDefinition.swagger.json"
PROPS = LAB / "connector" / "apiProperties.json"
ENV_FILE = LAB / ".env.local"


def endpoint() -> str:
    value = os.environ.get("MCP_ENDPOINT", "")
    if not value and ENV_FILE.exists():
        for line in ENV_FILE.read_text().splitlines():
            if line.startswith("MCP_ENDPOINT="):
                value = line.split("=", 1)[1].strip()
    if not value:
        sys.exit("MCP_ENDPOINT is not set (run scripts/deploy.sh first).")
    return value


def main() -> int:
    check_only = "--check" in sys.argv[1:]
    host = urlparse(endpoint()).netloc
    swagger = json.loads(SWAGGER.read_text())
    props = json.loads(PROPS.read_text())

    if swagger.get("host") != host:
        if check_only:
            print(f"FAIL: swagger host {swagger.get('host')!r} != deployed host {host!r}")
            return 1
        swagger["host"] = host
        SWAGGER.write_text(json.dumps(swagger, indent=2) + "\n")
        print(f"updated host -> {host}")

    op = swagger["paths"]["/mcp"]["post"]
    sec = swagger["securityDefinitions"]["api_key"]
    param = props["properties"]["connectionParameters"]["api_key"]
    checks = {
        "swagger 2.0": swagger["swagger"] == "2.0",
        "https only": swagger["schemes"] == ["https"],
        "basePath /": swagger["basePath"] == "/",
        "host matches deployment": swagger["host"] == host,
        "POST /mcp has x-ms-agentic-protocol mcp-streamable-1.0": op.get("x-ms-agentic-protocol") == "mcp-streamable-1.0",
        "operationId present": bool(op.get("operationId")),
        "apiKey in header x-api-key": sec == {"type": "apiKey", "in": "header", "name": "x-api-key"},
        "operation secured by api_key": {"api_key": []} in swagger["security"],
        "connection parameter api_key is a securestring": param["type"] == "securestring",
        "iconBrandColor is #RRGGBB": len(props["properties"]["iconBrandColor"]) == 7,
    }
    for name, ok in checks.items():
        print(f"[{'PASS' if ok else 'FAIL'}] {name}")
    return 0 if all(checks.values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
