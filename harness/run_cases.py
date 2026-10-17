#!/usr/bin/env python3
"""공통 5개 케이스를 선택한 하네스 에이전트에 보내 계약(JSON)을 검증한다.

예) python run_cases.py --target standard-classic
    python run_cases.py --target github --out ../evidence/github.json
"""
import argparse
import asyncio
import json
import sys
import time

from csharness.cases import evaluate
from csharness.config import load_cases, load_targets
from csharness.drivers import DRIVERS


async def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--target", required=True, help="targets.yaml 의 키")
    ap.add_argument("--cases", help="쉼표로 구분한 case id (기본: 전체)")
    ap.add_argument("--out", help="결과 JSON 저장 경로")
    a = ap.parse_args()

    tgt = load_targets()[a.target]
    cases = load_cases()
    if a.cases:
        want = set(a.cases.split(","))
        cases = [c for c in cases if c["id"] in want]

    rows = []
    for c in cases:
        t0 = time.time()
        try:
            reply = await DRIVERS[tgt["driver"]](tgt["schema"], tgt["runtime"], c)
            ev = evaluate(c, reply)
        except Exception as e:  # 네트워크/인증 오류도 케이스 실패로 기록
            reply, ev = "", {"passed": False, "problems": [f"예외: {e!r}"], "parsed": {}}
        sec = round(time.time() - t0, 1)
        rows.append({"id": c["id"], "passed": ev["passed"], "problems": ev["problems"],
                     "parsed": ev["parsed"], "seconds": sec, "reply": reply[:1500], "blocked": ev.get("blocked")})
        mark = ("PASS*" if ev.get("blocked") else "PASS") if ev["passed"] else "FAIL"
        print(f"{mark:4} {c['id']:26} {sec:6.1f}s  {json.dumps(ev['parsed'], ensure_ascii=False)}", flush=True)
        for p in ev["problems"]:
            print(f"       - {p}")

    passed = sum(r["passed"] for r in rows)
    print(f"\n[{a.target}] {passed}/{len(rows)} passed" + ("  (* = 플랫폼 보호가 차단)" if any(x.get("blocked") for x in rows) else ""))
    if a.out:
        with open(a.out, "w") as f:
            json.dump({"target": a.target, "schema": tgt["schema"], "passed": passed,
                       "total": len(rows), "results": rows}, f, ensure_ascii=False, indent=2)
    return 0 if passed == len(rows) else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
