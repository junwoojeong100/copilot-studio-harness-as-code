#!/usr/bin/env python3
"""schemaName 으로 에이전트에 바로 말을 건다 (targets.yaml 에 없는 임시 에이전트용).

  ../../../.venv/bin/python scripts/chat_schema.py --schema hlab_IssueTriageMCP "메시지"
출력 형식은 harness/chat.py 와 같다 ([step] / [thought] / 봇 응답). 하네스 패키지(harness/csharness)를 그대로 쓴다.
"""
import argparse
import asyncio
import pathlib
import sys

LAB = pathlib.Path(__file__).resolve().parents[4]          # .../CopilotStudio_Harness_CodeLab
sys.path.insert(0, str(LAB / "harness"))

from csharness.client import Session  # noqa: E402


async def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--schema", required=True)
    ap.add_argument("--runtime", default="agentic3p")
    ap.add_argument("messages", nargs="+")
    a = ap.parse_args()
    s = Session(a.schema, a.runtime)
    for g in await s.start():
        print("봇(시작) >", g)
    for m in a.messages:
        print("나       >", m)
        t = await s.say(m)
        for st in t.steps:
            print("  [step]  ", st)
        for th in t.thoughts:
            print("  [thought]", th[:200])
        for r in t.messages:
            print("봇       >", r)


asyncio.run(main())
