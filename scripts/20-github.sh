#!/usr/bin/env bash
# GitHub Copilot harness (CliCopilot): 지침 + 지식 파일 + 스킬(Python 스크립트, 샌드박스 실행)
set -euo pipefail
source "$(dirname "$0")/env.sh"
SCHEMA=hlab_IssueTriageGitHub; DIR=issue-triage-github; AGENT="$WS/$DIR"

log "1) 에이전트 생성 (pac copilot init --authoring-mode cli-copilot)"
ws_init "Issue Triage GitHub" "$DIR" cli-copilot "You triage GitHub issues."

log "2) 지침 적용 (settings.mcs.yml)"
"$PY" "$LAB_ROOT/scripts/set_instructions.py" "$AGENT/settings.mcs.yml" "$LAB_ROOT/shared/triage-instructions.md"

log "3) 지식 파일 추가 (capabilities/knowledge/files)"
mkdir -p "$AGENT/capabilities/knowledge/files"
cp "$LAB_ROOT/shared/label-policy.md" "$AGENT/capabilities/knowledge/files/label-policy.md"
cat > "$AGENT/capabilities/knowledge/files/label-policy-md_x7Kq2.mcs.yml" <<'YML'
mcs.metadata:
  componentName: "label-policy.md"
  description: "Caldova GitHub label policy: categories, P0-P3 priority criteria, team routing signals and guardrails for issue triage"
YML

log "4) 스킬 추가 (microsoft/copilot-studio-plugin 의 add-skill.js import)"
if [ ! -d "$PLUGIN_DIR/.git" ]; then
  git clone -q https://github.com/microsoft/copilot-studio-plugin.git "$PLUGIN_DIR"
  git -C "$PLUGIN_DIR" checkout -q "$PLUGIN_SHA"
fi
SRC="$LAB_ROOT/labs/02-github-copilot/skill-src/issue-triage-script"
cp "$LAB_ROOT/shared/classify_issue.py" "$SRC/scripts/classify_issue.py"
if [ ! -d "$AGENT/behaviors/issue-triage-script" ]; then
  node "$PLUGIN_DIR/scripts/add-skill.js" import --src "$SRC" --workspace "$AGENT" --name issue-triage-script
else
  echo "스킬이 이미 있음 (건너뜀)"
fi

log "5) pull → push → publish → pull"
ws_sync "$DIR"
ws_publish "$SCHEMA" "$DIR"

log "6) 5개 공통 케이스 검증 (agentic3p 엔드포인트)"
cd "$LAB_ROOT/harness" && "$PY" run_cases.py --target github --out "../evidence/github.json"
