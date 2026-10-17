# 7. Lab 5: 수명주기(ALM): solution · clone · pack

> **검증 상태 ✅** — `scripts/50-alm.sh` 로 *export → 에이전트 삭제 → import → 게시 → 5/5 재통과 → clone* 을 실행했습니다 (2026-10-17).

에이전트는 Dataverse 의 `bot`/`botcomponent` 레코드이므로 **solution** 으로 옮깁니다. 코드 관점에서 세 가지 입출구가 있습니다.

| 목적 | 명령 | 비고 |
| --- | --- | --- |
| 작업 폴더 → solution zip | `pac copilot pack --publisher-prefix hlab --project-dir <ws> --solution-name <이름> --output-path <dir>` | 봇 수준 설정까지 포함 → Lab 1 의 classic 설정 반영에 사용 |
| 환경 간 이동 | `pac solution export --name <이름> --path x.zip --managed true`(또는 `false`) → `pac solution import --path x.zip --publish-changes` | 운영 환경은 managed 권장 |
| 클라우드 → 작업 폴더 | `pac copilot clone --bot <schema 또는 id> --output-dir <dir>` | 폴더명은 에이전트 표시 이름 |

복원 시나리오(스크립트 요약):

```bash
pac solution export --name HarnessLabStandard --path build/HarnessLabStandard_unmanaged.zip --managed false --environment "$CSLAB_DATAVERSE_URL" --overwrite
pac solution export --name HarnessLabStandard --path build/HarnessLabStandard_managed.zip   --managed true  --environment "$CSLAB_DATAVERSE_URL" --overwrite
pac copilot delete --bot hlab_IssueTriageStandard --environment "$CSLAB_DATAVERSE_URL" --confirm   # 장애 가정
pac solution import --path build/HarnessLabStandard_unmanaged.zip --environment "$CSLAB_DATAVERSE_URL" --force-overwrite --publish-changes
pac copilot publish --bot hlab_IssueTriageStandard --environment "$CSLAB_DATAVERSE_URL"            # 필요 시 재시도
(cd harness && ../.venv/bin/python run_cases.py --target standard-classic)                           # 5/5
rm -rf workspaces/issue-triage-standard && mkdir -p workspaces/_clone                                  # 옛 작업 폴더는 폐기
pac copilot clone --bot hlab_IssueTriageStandard --environment "$CSLAB_DATAVERSE_URL" --output-dir workspaces/_clone
mv "workspaces/_clone/Issue Triage Standard" workspaces/issue-triage-standard && rmdir workspaces/_clone
```

```text
Deleted copilot 'Issue Triage Standard' [b917c1a4-…]
… Solution Imported successfully.
[standard-classic] 5/5 passed          ← 복원된 에이전트가 같은 결과
Clone complete. Agent cloned to 'Issue Triage Standard'.   ← 새 Copilot ID: 1828d76f-…
```

> 🐞 **import 직후 `publish` 가 409**: `ExternalServiceException … statuscode 409 Conflict` — 프로비저닝이 끝나기 전입니다. 20초 뒤 재시도하면 성공합니다(스크립트가 최대 6회 재시도).
> 🐞 **import 하면 Copilot ID 가 바뀝니다**(삭제된 레코드 ID 재사용 불가: `b917c1a4-…` → `1828d76f-…`). 옛 작업 폴더의 `.mcs/` 연결은 더 이상 유효하지 않으며, **그 폴더에서 `pull` 하면 "15 change(s) applied" 와 함께 로컬 토픽 파일이 모두 지워졌습니다**(실제로 확인). 폐기하고 `clone` 으로 새로 받으세요(스크립트가 같은 경로로 교체). 호출은 ID 가 아니라 **schemaName** 으로 하므로 하네스 설정은 그대로 동작합니다.
> 🐞 `pac copilot status --bot-id …` 는 2.13.1 에서 `'bot' entity doesn't contain attribute … componentstate_Property` 로 실패합니다 — 상태 확인은 `pac copilot list`(Component State) 또는 Dataverse `bots?$select=publishedon` 을 쓰세요.

## 7.1 Dataverse 로 직접 확인하기 (읽기 전용)

```bash
DV=$CSLAB_DATAVERSE_URL; T=$(az account get-access-token --resource "$DV" --query accessToken -o tsv)
curl -s -H "Authorization: Bearer $T" "${DV%/}/api/data/v9.2/bots?\$select=name,schemaname,publishedon&\$filter=startswith(schemaname,'hlab_')" | python3 -m json.tool
# botcomponents: componenttype 9=토픽/스킬(대화 컴포넌트), 14=파일(지식·SKILL.md·스크립트)
curl -s -G -H "Authorization: Bearer $T" --data-urlencode '$select=name,schemaname,componenttype' \
  --data-urlencode "\$filter=_parentbotid_value eq <botid>" "${DV%/}/api/data/v9.2/botcomponents"
```
