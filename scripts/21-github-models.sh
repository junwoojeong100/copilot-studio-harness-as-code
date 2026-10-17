#!/usr/bin/env bash
# GitHub Copilot harness 모델 선택 옵션 비교 (settings.mcs.yml: configuration.agentSettings.model.series)
set -euo pipefail
source "$(dirname "$0")/env.sh"
SCHEMA=hlab_IssueTriageGitHub; DIR=issue-triage-github; AGENT="$WS/$DIR"
MODELS=("$@")
[ $# -eq 0 ] && MODELS=(Opus47 GPT55Chat GPT5Chat Sonnet46)   # 마지막에 기본 모델(Sonnet46)로 복원

for M in "${MODELS[@]}"; do
  log "모델 $M"
  sed -i.bak "s/series: .*/series: $M/" "$AGENT/settings.mcs.yml" && rm -f "$AGENT/settings.mcs.yml.bak"
  ws_sync "$DIR"
  ws_publish "$SCHEMA" "$DIR"
  (cd "$LAB_ROOT/harness" && "$PY" run_cases.py --target github --out "../evidence/github-model-$M.json") || true
done
