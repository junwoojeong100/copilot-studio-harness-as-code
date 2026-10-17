#!/usr/bin/env bash
# Standard harness - generative orchestration (instructions 만으로 분류)
set -euo pipefail
source "$(dirname "$0")/env.sh"
SCHEMA=hlab_IssueTriageStdGen; DIR=issue-triage-stdgen

log "1) 에이전트 생성"
ws_init "Issue Triage StdGen" "$DIR" classic "You triage GitHub issues."

log "2) agent.mcs.yml 에 공통 지침(shared/triage-instructions.md) 주입"
"$PY" - "$LAB_ROOT" "$WS/$DIR/agent.mcs.yml" <<'PYEOF'
import sys
lab, out = sys.argv[1], sys.argv[2]
instr = open(f"{lab}/shared/triage-instructions.md").read().rstrip()
body = "\n".join(("  " + l if l else "") for l in instr.splitlines())
open(out, "w").write(f"""mcs.metadata:
  componentName: Issue Triage StdGen
  description: Classifies GitHub issues with generative orchestration (instructions only, no tools).
kind: GptComponentMetadata
instructions: |-
{body}
gptCapabilities:
  webBrowsing: false

aISettings:
  model:
    modelNameHint: GPT5Chat
""")
PYEOF

log "3) pull → push → publish → pull"
ws_sync "$DIR"
ws_publish "$SCHEMA" "$DIR"

log "4) 검증"
cd "$LAB_ROOT/harness" && "$PY" run_cases.py --target standard-generative --out "../evidence/standard-generative.json"
