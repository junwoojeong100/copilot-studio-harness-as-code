#!/usr/bin/env bash
# 이미 만들어진 에이전트들에 5개 공통 케이스를 실행하고 evidence/summary.md 를 만든다 (읽기 전용 호출만 수행).
# 사용: 90-verify-all.sh [target ...]   (생략하면 harness/targets.yaml 의 전부 — github-mcp 는 Lab 4 가 끝난 뒤에만 포함)
# 주의: evidence/<target>.json 을 덮어씁니다.
set -uo pipefail
source "$(dirname "$0")/env.sh"
OUT="$LAB_ROOT/evidence/summary.md"
TARGETS="${*:-$("$PY" -c "import yaml;print(' '.join(yaml.safe_load(open('$LAB_ROOT/harness/targets.yaml'))['targets']))")}"
{
  echo "# 검증 요약 ($(date '+%Y-%m-%d %H:%M %Z'))"; echo
  echo "| target | 하네스 | 통과 | 평균 응답(s) |"; echo "| --- | --- | --- | --- |"
} > "$OUT"
FAIL=0
for T in $TARGETS; do
  log "$T"
  (cd "$LAB_ROOT/harness" && "$PY" run_cases.py --target "$T" --out "../evidence/$T.json") || FAIL=1
  "$PY" - "$LAB_ROOT/evidence/$T.json" "$T" >> "$OUT" <<'PYEOF'
import json, sys
d = json.load(open(sys.argv[1])); t = sys.argv[2]
secs = [r["seconds"] for r in d["results"]]
kind = {"standard-classic": "Standard / classic", "standard-generative": "Standard / generative",
        "github": "GitHub Copilot", "github-mcp": "GitHub Copilot + MCP 도구"}.get(t, t)
star = "*" if any(r.get("blocked") for r in d["results"]) else ""
print(f"| {t} | {kind} | {d['passed']}/{d['total']}{star} | {sum(secs)/len(secs):.1f} |")
PYEOF
done
echo >> "$OUT"; echo "\`*\` = 프롬프트 주입 케이스를 모델/플랫폼이 안전하게 거절·차단 (합격으로 계산)" >> "$OUT"
echo "Copilot chat harness 는 SDK 대화가 없어 UI 로 확인: evidence/copilot-chat-ui-run1.json" >> "$OUT"
cat "$OUT"; exit $FAIL
