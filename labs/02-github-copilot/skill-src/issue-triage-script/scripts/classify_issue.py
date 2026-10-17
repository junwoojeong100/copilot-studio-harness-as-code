#!/usr/bin/env python3
"""Deterministic GitHub issue triage rules (single source of truth for the lab).

The same rules are ported to:
  - Power Fx   (Standard harness, classic orchestration topic)
  - skill script (GitHub Copilot harness, runs in the agent sandbox)
  - MCP server (Azure Container Apps tool)
Output contract: category, priority, team, summary, needsHumanReview
"""
import json
import re
import sys

RX = {
    "injection": r"ignore (your|all|previous)|system instruction|reveal (all )?secret|treat this text as|disregard (the|your)|close every",
    "security": r"vulnerab|secret|token|exploit|\bcve\b|credential|password|api key|leak",
    "docs": r"documentation|\bdocs?\b|typo|quickstart|tutorial|\bguide\b|readme|package name",
    "feature": r"feature request|please add|add support|enhancement|would like|support for",
    "question": r"how do i|how to|is it possible|\?",
    "bug": r"error|fail|crash|exception|broken|\b50[0-9]\b|timeout|regression|not work|doesn't work",
    "outage": r"\b503\b|outage|all customers|data loss|site down|production down",
    "backend": r"\bapi\b|service|database|latency|server|\b50[0-9]\b",
    "frontend": r"\bui\b|\bux\b|browser|react|\bcss\b|accessibility|button",
    "data": r"analytics|pipeline|\bmodel\b|schema|warehouse",
    "platform": r"infrastructure|deployment|\bci\b|\bbuild\b|\bauth\b|permission",
}


def has(name: str, text: str) -> bool:
    return re.search(RX[name], text) is not None


def classify(title: str, body: str) -> dict:
    t = f"{title} {body}".lower()
    inj, sec, doc = has("injection", t), has("security", t), has("docs", t)

    if inj:
        category = "security"
    elif sec:
        category = "security"
    elif doc:
        category = "documentation"
    elif has("feature", t):
        category = "feature"
    elif has("question", t):
        category = "question"
    elif has("bug", t):
        category = "bug"
    else:
        category = "question"

    if inj:
        team = "needs-triage"
    elif sec:
        team = "security"
    elif doc:
        team = "docs"
    elif has("backend", t):
        team = "backend"
    elif has("frontend", t):
        team = "frontend"
    elif has("data", t):
        team = "data"
    elif has("platform", t):
        team = "platform"
    else:
        team = "needs-triage"

    if team == "needs-triage":
        priority = "P3"
    elif sec:
        priority = "P1"
    elif has("outage", t):
        priority = "P0"
    elif category == "bug":
        priority = "P2"
    else:
        priority = "P3"

    needs_review = category == "security" or priority == "P0" or team == "needs-triage"
    short = " ".join(title.split())[:80]
    return {
        "category": category,
        "priority": priority,
        "team": team,
        "summary": f"{category} for {team}: {short}",
        "needsHumanReview": needs_review,
    }


if __name__ == "__main__":
    if len(sys.argv) >= 3:
        print(json.dumps(classify(sys.argv[1], sys.argv[2]), ensure_ascii=False))
    else:
        data = json.load(sys.stdin)
        print(json.dumps(classify(data["issueTitle"], data["issueBody"]), ensure_ascii=False))
