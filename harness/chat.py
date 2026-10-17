#!/usr/bin/env python3
"""한 줄 대화 도구. 예) python chat.py --target github "이슈를 분류해 줘: ..." """
import argparse
import asyncio

from csharness.client import Session
from csharness.config import load_targets


async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--target", required=True)
    ap.add_argument("messages", nargs="+")
    a = ap.parse_args()
    tgt = load_targets()[a.target]
    s = Session(tgt["schema"], tgt["runtime"])
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
