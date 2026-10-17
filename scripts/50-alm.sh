#!/usr/bin/env bash
# ALM(수명주기) : solution export → 에이전트 삭제 → solution import 로 복원 → 동일 테스트 재통과
set -euo pipefail
source "$(dirname "$0")/env.sh"
SOL=HarnessLabStandard; SCHEMA=hlab_IssueTriageStandard

log "1) solution export (unmanaged / managed)"
pac solution export --name "$SOL" --path "$BUILD/${SOL}_unmanaged.zip" --managed false --environment "$ENV_URL" --overwrite
pac solution export --name "$SOL" --path "$BUILD/${SOL}_managed.zip"   --managed true  --environment "$ENV_URL" --overwrite
ls -la "$BUILD"/${SOL}_*.zip

log "2) 에이전트 삭제 (장애/환경 이전 상황을 가정)"
pac copilot delete --bot "$SCHEMA" --environment "$ENV_URL" --confirm
pac copilot list --environment "$ENV_URL" | grep -c "$SCHEMA" || echo "삭제 확인: 목록에 없음"

log "3) unmanaged solution import → 게시"
pac solution import --path "$BUILD/${SOL}_unmanaged.zip" --environment "$ENV_URL" --force-overwrite --publish-changes
# import 직후에는 프로비저닝이 끝나기 전이라 publish 가 409(Conflict)로 실패할 수 있어 재시도한다
for i in 1 2 3 4 5 6; do
  pac copilot publish --bot "$SCHEMA" --environment "$ENV_URL" && break
  echo "게시 재시도 $i/6 (20초 대기)"; sleep 20
done

log "4) 복원된 에이전트 재검증"
(cd "$LAB_ROOT/harness" && "$PY" run_cases.py --target standard-classic --out ../evidence/alm-roundtrip.json)

log "5) 옛 작업 폴더는 폐기하고 복원된 에이전트를 clone 으로 다시 받는다"
# import 로 Copilot ID 와 컴포넌트 ID 가 모두 바뀐다. 옛 폴더에서 pull 하면 로컬 토픽 파일이 지워진 채 동기화되므로 쓰지 않는다.
rm -rf "$WS/_clone" "$WS/issue-triage-standard"; mkdir -p "$WS/_clone"
pac copilot clone --bot "$SCHEMA" --environment "$ENV_URL" --output-dir "$WS/_clone"
mv "$WS/_clone/Issue Triage Standard" "$WS/issue-triage-standard" && rmdir "$WS/_clone"
find "$WS/issue-triage-standard" -maxdepth 2 -name "*.mcs.yml" | head -20
