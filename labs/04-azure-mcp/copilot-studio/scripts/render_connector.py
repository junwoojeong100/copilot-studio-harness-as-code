#!/usr/bin/env python3
"""lab 04 의 커넥터 정의(../connector)를 pac connector create 가 받아들이는 형태로 복사한다.

  python3 scripts/render_connector.py [--out DIR]     # 제목은 환경 변수 CONNECTOR_TITLE (기본 "Issue Triage MCP")

- swagger 의 host 를 .env.local 의 MCP_ENDPOINT 와 맞춘다.
- pac 는 OpenAPI info.title 이 30자 이하여야 한다(초과하면 `must have a Title property with a maximum of 30 characters`).
  lab 04 원본 제목은 길어서 TITLE 로 줄인다. 원본 파일은 수정하지 않는다.
- API 키(.env.local 의 API_KEY)는 읽지도 쓰지도 않는다.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from urllib.parse import urlparse

HERE = Path(__file__).resolve().parent.parent          # .../copilot-studio
LAB04 = HERE.parent                                     # .../04-azure-mcp
SRC = LAB04 / "connector"
DST = HERE / "connector"
ENV_FILE = LAB04 / ".env.local"
TITLE = os.environ.get("CONNECTOR_TITLE", "Issue Triage MCP")   # <= 30 chars


def endpoint() -> str:
    value = os.environ.get("MCP_ENDPOINT", "")
    if not value and ENV_FILE.exists():
        for line in ENV_FILE.read_text().splitlines():
            if line.startswith("MCP_ENDPOINT="):
                value = line.split("=", 1)[1].strip()
    if not value:
        sys.exit("MCP_ENDPOINT 가 없습니다 (labs/04-azure-mcp/.env.local 확인).")
    return value


def main() -> int:
    if len(TITLE) > 30:
        sys.exit(f"CONNECTOR_TITLE 은 30자 이하여야 합니다 (pac 제한): {TITLE!r} = {len(TITLE)}자")
    dst = DST
    if "--out" in sys.argv:
        dst = Path(sys.argv[sys.argv.index("--out") + 1])
    host = urlparse(endpoint()).netloc
    swagger = json.loads((SRC / "apiDefinition.swagger.json").read_text())
    props = json.loads((SRC / "apiProperties.json").read_text())
    swagger["host"] = host
    swagger["info"]["title"] = TITLE
    dst.mkdir(parents=True, exist_ok=True)
    (dst / "apiDefinition.swagger.json").write_text(json.dumps(swagger, indent=2) + "\n")
    (dst / "apiProperties.json").write_text(json.dumps(props, indent=2) + "\n")
    print(f"rendered {dst}/ (host={host}, title={TITLE!r})", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
