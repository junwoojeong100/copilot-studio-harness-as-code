#!/usr/bin/env bash
# Standard harness - classic orchestration (topic + Power Fx, 결정론적)
set -euo pipefail
source "$(dirname "$0")/env.sh"
SCHEMA=hlab_IssueTriageStandard; DIR=issue-triage-standard

log "1) 에이전트 생성 (pac copilot init, classic 템플릿)"
ws_init "Issue Triage Standard" "$DIR" classic "You triage GitHub issues."

log "2) 토픽(YAML+Power Fx) 오버레이 복사"
cp "$LAB_ROOT/labs/01-standard/overlay/classic/topics/ClassifyIssue.mcs.yml" "$WS/$DIR/topics/ClassifyIssue.mcs.yml"

log "3) push 로 토픽을 클라우드에 등록 (이 단계가 없으면 이후 pull 이 'Component is missing Id' 로 실패)"
pac copilot push --project-dir "$WS/$DIR"

log "4) settings.mcs.yml: classic orchestration 으로 전환 (생성형 기능 끄기)"
"$PY" - "$WS/$DIR/settings.mcs.yml" <<'PYEOF'
import sys
p = sys.argv[1]; s = open(p).read()
for k in ("GenerativeActionsEnabled", "useModelKnowledge", "isFileAnalysisEnabled", "isSemanticSearchEnabled"):
    s = s.replace(f"{k}: true", f"{k}: false")
open(p, "w").write(s)
PYEOF

log "5) pack → solution import  (push 는 settings 를 반영하지 않으므로 solution 경로를 사용)"
pac copilot pack --publisher-prefix hlab --project-dir "$WS/$DIR" --solution-name HarnessLabStandard --output-path "$BUILD"
pac solution import --path "$BUILD/HarnessLabStandard.zip" --environment "$ENV_URL" --force-overwrite --publish-changes

log "6) 게시 + 동기화"
ws_publish "$SCHEMA" "$DIR"

log "7) 5개 공통 케이스 검증"
cd "$LAB_ROOT/harness" && "$PY" run_cases.py --target standard-classic --out "../evidence/standard-classic.json"
