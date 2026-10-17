#!/usr/bin/env python3
"""End-to-end test of the issue-triage MCP server (local or deployed) with a real MCP client.

  python scripts/test_mcp.py                                  # MCP_ENDPOINT + API_KEY from .env.local
  python scripts/test_mcp.py --url http://127.0.0.1:8000/mcp  # e.g. a locally running server

MCP_ENDPOINT / API_KEY environment variables override .env.local. The key is never printed.
Exit code 0 only if every check passes.
"""
import argparse
import asyncio
import json
import os
import sys
from contextlib import asynccontextmanager
from datetime import timedelta
from pathlib import Path
from urllib.parse import urlsplit

import httpx
import yaml
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client

LAB_DIR = Path(__file__).resolve().parents[1]
SHARED_DIR = LAB_DIR.parents[1] / "shared"
JSONRPC_HEADERS = {"Content-Type": "application/json", "Accept": "application/json, text/event-stream"}
INIT_REQUEST = {
    "jsonrpc": "2.0",
    "id": 1,
    "method": "initialize",
    "params": {"protocolVersion": "2025-03-26", "capabilities": {}, "clientInfo": {"name": "raw-http-check", "version": "1"}},
}


class Report:
    def __init__(self) -> None:
        self.rows: list[tuple[str, bool]] = []

    def check(self, name: str, ok: bool, detail: str = "") -> bool:
        self.rows.append((name, ok))
        print(f"[{'PASS' if ok else 'FAIL'}] {name}" + (f"  ({detail})" if detail else ""), flush=True)
        return ok

    @property
    def failed(self) -> int:
        return sum(1 for _, ok in self.rows if not ok)


def read_env_file(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if path.is_file():
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, _, value = line.partition("=")
                values[key.strip()] = value.strip().strip("\"'")
    return values


def tool_text(result) -> str:
    return "".join(part.text for part in result.content if getattr(part, "type", "") == "text")


def evaluate_case(case: dict, contract: dict, got: dict, raw_text: str) -> list[str]:
    """Returns a list of problems (empty list == pass)."""
    problems: list[str] = []
    expected = case["expected"]

    if set(got) != set(contract):
        problems.append(f"keys {sorted(got)} != contract {sorted(contract)}")
    for field in ("category", "priority", "team"):
        if got.get(field) not in contract[field]:
            problems.append(f"{field}={got.get(field)!r} not in contract {contract[field]}")
    if not isinstance(got.get("summary"), str) or not got.get("summary"):
        problems.append("summary must be a non-empty string")
    if not isinstance(got.get("needsHumanReview"), bool):
        problems.append("needsHumanReview must be a boolean")

    for field in ("category", "priority", "team", "needsHumanReview"):
        if field in expected and got.get(field) != expected[field]:
            problems.append(f"{field}: expected {expected[field]!r}, got {got.get(field)!r}")
    if "priorityAnyOf" in expected and got.get("priority") not in expected["priorityAnyOf"]:
        problems.append(f"priority {got.get('priority')!r} not in {expected['priorityAnyOf']}")
    for phrase in expected.get("forbiddenPhrases", []):
        if phrase.lower() in raw_text.lower():
            problems.append(f"forbidden phrase present: {phrase!r}")
    return problems


@asynccontextmanager
async def mcp_session(url: str, api_key: str):
    async with httpx.AsyncClient(headers={"x-api-key": api_key}, timeout=httpx.Timeout(30.0, read=60.0)) as http_client:
        async with streamable_http_client(url, http_client=http_client) as (read, write, _get_session_id):
            async with ClientSession(read, write, read_timeout_seconds=timedelta(seconds=60)) as session:
                yield session


async def run(url: str, api_key: str) -> int:
    report = Report()
    parts = urlsplit(url)
    origin = f"{parts.scheme}://{parts.netloc}"
    spec = yaml.safe_load((SHARED_DIR / "test-cases.yaml").read_text(encoding="utf-8"))
    contract, cases = spec["contract"], spec["cases"]
    policy_reference = yaml.safe_load((SHARED_DIR / "label-policy.yaml").read_text(encoding="utf-8"))

    try:
        sys.path.insert(0, str(SHARED_DIR))
        from classify_issue import classify as reference_classify
    except ImportError:
        reference_classify = None

    print(f"endpoint: {url}")

    # --- plain HTTP checks (no MCP client): health + authentication -------------------------------------------
    async with httpx.AsyncClient(timeout=30.0) as http:
        r = await http.get(f"{origin}/healthz")
        report.check("GET /healthz without key -> 200 'ok'", r.status_code == 200 and r.text.strip() == "ok", f"HTTP {r.status_code}")

        r = await http.post(url, json=INIT_REQUEST, headers=JSONRPC_HEADERS)
        body = r.json() if r.headers.get("content-type", "").startswith("application/json") else {}
        report.check("POST /mcp WITHOUT x-api-key -> 401 JSON", r.status_code == 401 and "error" in body, f"HTTP {r.status_code}")

        r = await http.post(url, json=INIT_REQUEST, headers={**JSONRPC_HEADERS, "x-api-key": "wrong-" + "x" * 24})
        report.check("POST /mcp with WRONG x-api-key -> 401", r.status_code == 401, f"HTTP {r.status_code}")

        r = await http.post(url, json=INIT_REQUEST, headers={**JSONRPC_HEADERS, "x-api-key": api_key})
        report.check(
            "raw JSON-RPC initialize with key -> 200 application/json, stateless (no mcp-session-id)",
            r.status_code == 200
            and r.headers.get("content-type", "").startswith("application/json")
            and "mcp-session-id" not in r.headers,
            f"HTTP {r.status_code}",
        )

        r = await http.get(url, headers={"x-api-key": api_key, "Accept": "text/event-stream"})
        report.check("GET /mcp with key -> 405 (no standalone SSE stream)", r.status_code == 405, f"HTTP {r.status_code}")

    # --- real MCP client: initialize / list_tools / call_tool -------------------------------------------------
    async with mcp_session(url, api_key) as session:
        init = await session.initialize()
        report.check(
            "MCP initialize",
            bool(init.serverInfo.name),
            f"server={init.serverInfo.name} {init.serverInfo.version}, protocol={init.protocolVersion}",
        )

        tools = (await session.list_tools()).tools
        names = sorted(tool.name for tool in tools)
        report.check("list_tools -> classify_issue + get_label_policy", names == ["classify_issue", "get_label_policy"], str(names))
        report.check(
            "every tool has a description and an input schema",
            all(tool.description and tool.inputSchema.get("type") == "object" for tool in tools),
        )
        classify_tool = next(tool for tool in tools if tool.name == "classify_issue")
        report.check(
            "classify_issue requires issue_title + issue_body",
            sorted(classify_tool.inputSchema.get("required", [])) == ["issue_body", "issue_title"],
        )

        for case in cases:
            args = {"issue_title": case["input"]["issueTitle"], "issue_body": case["input"]["issueBody"]}
            result = await session.call_tool("classify_issue", args)
            raw = tool_text(result)
            if result.isError:
                report.check(f"case {case['id']}", False, f"tool error: {raw[:120]}")
                continue
            try:
                got = json.loads(raw)
            except json.JSONDecodeError:
                report.check(f"case {case['id']}", False, f"response is not JSON: {raw[:120]}")
                continue
            problems = evaluate_case(case, contract, got, raw)
            if reference_classify is not None and got != reference_classify(args["issue_title"], args["issue_body"]):
                problems.append("differs from shared/classify_issue.py (reference)")
            detail = f"{got.get('category')}/{got.get('priority')}/{got.get('team')}/review={got.get('needsHumanReview')}"
            report.check(f"case {case['id']}", not problems, detail if not problems else "; ".join(problems))

        result = await session.call_tool("get_label_policy", {})
        try:
            policy = json.loads(tool_text(result))
        except json.JSONDecodeError:
            policy = None
        report.check(
            "get_label_policy == shared/label-policy.yaml",
            not result.isError and policy == policy_reference,
            f"version={policy.get('version') if isinstance(policy, dict) else '?'}, keys={sorted(policy) if isinstance(policy, dict) else '?'}",
        )

        result = await session.call_tool("classify_issue", {})
        report.check("classify_issue without arguments -> tool error (not a crash)", result.isError is True)

    total = len(report.rows)
    print(f"\n{total - report.failed}/{total} checks passed")
    return 0 if report.failed == 0 else 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--url", help="MCP endpoint (default: MCP_ENDPOINT from the environment or .env.local)")
    parser.add_argument("--env-file", default=str(LAB_DIR / ".env.local"), help="path of the .env file (default: %(default)s)")
    args = parser.parse_args()

    env_file = read_env_file(Path(args.env_file))
    url = args.url or os.environ.get("MCP_ENDPOINT") or env_file.get("MCP_ENDPOINT")
    api_key = os.environ.get("API_KEY") or env_file.get("API_KEY")
    if not url:
        print("No endpoint: pass --url or set MCP_ENDPOINT (deploy.sh writes it to .env.local).", file=sys.stderr)
        return 2
    if not api_key:
        print("No API key: set API_KEY or add it to .env.local.", file=sys.stderr)
        return 2
    try:
        return asyncio.run(asyncio.wait_for(run(url, api_key), timeout=180))
    except Exception as exc:  # noqa: BLE001 - report and fail instead of a stack trace wall
        print(f"[FAIL] unexpected error: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
