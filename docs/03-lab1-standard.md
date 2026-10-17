# 3. Lab 1: Standard harness (코드)

> **검증 상태 ✅** — `scripts/10-standard-classic.sh`, `scripts/11-standard-generative.sh` 를 **빈 상태에서 처음부터** 실행해 각각 5/5 통과 (2026-10-17).
> 작업 폴더 구조는 VS Code **Copilot Studio 확장**이 쓰는 *에이전트 정의*(YAML)와 같습니다. 확장 대신 `pac copilot` 이 같은 일을 CLI 로 합니다.

Standard harness 는 두 가지 **오케스트레이션**을 가집니다.

| | classic orchestration | generative orchestration |
| --- | --- | --- |
| 동작 | 사용자가 정의한 **토픽·경로**를 따름 (트리거 문구 → 노드) | 모델이 topic/tool/knowledge 를 선택 |
| 결과 | 같은 입력 → 항상 같은 출력 (결정론적) | 모델 판단에 따라 변동 가능 |
| 코드 | 토픽 YAML + **Power Fx** | `agent.mcs.yml` 의 지침 |
| 이 실습 | `Issue Triage Standard` (`hlab_IssueTriageStandard`) | `Issue Triage StdGen` (`hlab_IssueTriageStdGen`) |

## 3.1 classic orchestration — 토픽 + Power Fx

### ① 에이전트 만들기

```bash
source scripts/env.sh
pac copilot init --name 'Issue Triage Standard' \
  --environment "$CSLAB_DATAVERSE_URL" --project-dir workspaces/issue-triage-standard \
  --publisher-prefix hlab --template minimal --instructions 'You triage GitHub issues.'
```

`init` 은 **클라우드에 에이전트를 즉시 만들고**(solution 을 import) 로컬에 작업 폴더를 만듭니다(약 40초).

```text
Agent discovered: 6cf80317-5b3e-429a-a796-7f06d6bdb7aa
Schema name: hlab_IssueTriageStandard      Template: minimal
workspaces/issue-triage-standard/
├── agent.mcs.yml        # kind: GptComponentMetadata — 지침·모델 힌트
├── settings.mcs.yml     # 에이전트 설정 (orchestration, AI 설정, recognizer)
├── topics/*.mcs.yml     # 시스템 토픽 13개 (Greeting, Fallback, Escalate, …)
└── .mcs/                # pac 의 동기화 상태 — 직접 수정·커밋하지 않음
```

### ② 토픽 작성 — 결정론적 분류 규칙을 Power Fx 로

```bash
cp labs/01-standard/overlay/classic/topics/ClassifyIssue.mcs.yml workspaces/issue-triage-standard/topics/   # 아래 YAML 전체가 들어 있는 파일
```

`labs/01-standard/overlay/classic/topics/ClassifyIssue.mcs.yml` (발췌):

```yaml
kind: AdaptiveDialog
beginDialog:
  kind: OnRecognizedIntent
  id: main
  intent:
    displayName: Classify Issue
    triggerQueries: [classify an issue, triage an issue, issue triage]
  actions:
    - kind: Question                       # 제목 → 본문을 차례로 묻는다
      id: question_title
      variable: init:Topic.IssueTitle
      prompt: What is the GitHub issue title?
      entity: StringPrebuiltEntity
    - kind: Question
      id: question_body
      variable: init:Topic.IssueBody
      prompt: What is the GitHub issue body?
      entity: StringPrebuiltEntity
    - kind: SetVariable
      id: set_text
      variable: init:Topic.Text
      value: =Lower(Topic.IssueTitle & " " & Topic.IssueBody)
    - kind: SetVariable
      id: set_team
      variable: init:Topic.Team
      value: |-
        =If(Topic.IsInjection, "needs-triage",
           Topic.IsSecurity, "security",
           Topic.IsDocs, "docs",
           IsMatch(Topic.Text, "\bapi\b|service|database|latency|server|\b50[0-9]\b", MatchOptions.Contains), "backend",
           …, "needs-triage")
    # category, priority, needsHumanReview, summary 도 같은 방식 …
    - kind: SetVariable
      id: set_json
      variable: init:Topic.ResultJson
      value: =JSON({category: Topic.Category, priority: Topic.Priority, team: Topic.Team, summary: Topic.Summary, needsHumanReview: Topic.NeedsHumanReview})
    - kind: SendActivity
      id: send_result
      activity: "{Topic.ResultJson}"
```

> 🐞 **정규식 백슬래시는 한 번만** — YAML 평문·`|-` 블록에서는 이스케이프가 없고 Power Fx 문자열도 마찬가지입니다. `"\\b50[0-9]\\b"` 처럼 두 번 쓰면 "리터럴 `\` + `b50…`" 패턴이 되어 **절대 매치되지 않습니다**. 특히 `"\\?"` 는 *"`\` 가 0~1개"* 가 되어 **항상 참**이라 모든 이슈가 `question` 으로 분류됐습니다(첫 실행 4/5).

### ③ 동기화 — `push` 는 설정을 반영하지 않는다 ⚠

```bash
pac copilot push --project-dir workspaces/issue-triage-standard     # → "Push complete. 1 change(s) pushed." (토픽 등록 — 이 단계는 pack 전에 반드시 필요)
```

`settings.mcs.yml` 의 `GenerativeActionsEnabled: false` 로 바꿔도 `pac copilot push` 는 **"No local changes detected"** 이며, 다음 `pull` 이 값을 `true` 로 되돌립니다(클라우드 구성 `configuration.settings.GenerativeActionsEnabled` 로 직접 확인). **봇 수준 설정(오케스트레이션·AI 설정)은 `pack` → `solution import` 경로로 반영**됩니다.

```bash
# settings.mcs.yml 에서 아래 4개 키를 true → false 로 변경한 뒤 (스크립트가 일괄 치환):
#   GenerativeActionsEnabled · useModelKnowledge · isFileAnalysisEnabled · isSemanticSearchEnabled
pac copilot pack --publisher-prefix hlab --project-dir workspaces/issue-triage-standard \
                 --solution-name HarnessLabStandard --output-path build
pac solution import --path build/HarnessLabStandard.zip --environment "$CSLAB_DATAVERSE_URL" \
                    --force-overwrite --publish-changes
```

Dataverse 로 확인(`GET bots(<id>)?$select=configuration`):

```text
GenerativeActionsEnabled = False | useModelKnowledge = False
```

> 🐞 **`pack` 전에 반드시 `push` 한 번**: 새로 만든 토픽을 `push` 없이 `pack`/`import` 하면 이후 `pull` 이 `Component is missing Id: hlab_IssueTriageStandard.topic.ClassifyIssue` 로 종료됩니다. 스크립트는 `push → settings 수정 → pack → import` 순서를 씁니다.
> 🐞 **클라우드가 바뀐 뒤 `push`** 는 "The agent was changed in the cloud while you were editing it. Get the latest changes before pushing again." — 항상 `pull → push` 순서로 합니다.

### ④ 게시 → 대화 검증

```bash
pac copilot publish --bot hlab_IssueTriageStandard --environment "$CSLAB_DATAVERSE_URL"   # ~20초
pac copilot pull --project-dir workspaces/issue-triage-standard                            # publishedOn 동기화
(cd harness && ../.venv/bin/python run_cases.py --target standard-classic)
```

classic 에이전트는 **다중 턴**으로 동작합니다: `classify an issue` → (제목 질문) → 제목 → (본문 질문) → 본문 → JSON.

<!-- AUTO:cases:standard-classic -->
<!-- /AUTO -->

모든 필드 값이 `shared/classify_issue.py` 의 출력과 **같습니다**(결정론적 — 키 순서만 Power Fx `JSON()` 이 알파벳순으로 내보냅니다).

## 3.2 generative orchestration — 지침만으로

`pac copilot init` 의 *minimal* 템플릿은 기본이 generative 입니다. 공통 지침(`shared/triage-instructions.md`)을 `agent.mcs.yml` 에 넣고 일반 동기화로 반영합니다 (`scripts/11-standard-generative.sh`).

```yaml
kind: GptComponentMetadata
instructions: |-
  You are a GitHub issue triage assistant for the Caldova engineering organization.
  TASK … (라벨 정책 · 출력 계약 · 가드레일)
gptCapabilities: {webBrowsing: false}
aISettings: {model: {modelNameHint: GPT5Chat}}
```

```bash
pac copilot init --name 'Issue Triage StdGen' --environment "$CSLAB_DATAVERSE_URL" --project-dir workspaces/issue-triage-stdgen \
  --publisher-prefix hlab --template minimal --instructions 'You triage GitHub issues.'
# agent.mcs.yml 을 위 YAML 로 교체 (스크립트가 shared/triage-instructions.md 를 들여써서 주입)
pac copilot pull --project-dir workspaces/issue-triage-stdgen && pac copilot push --project-dir workspaces/issue-triage-stdgen
pac copilot publish --bot hlab_IssueTriageStdGen --environment "$CSLAB_DATAVERSE_URL"
pac copilot pull --project-dir workspaces/issue-triage-stdgen            # publishedOn 동기화
(cd harness && ../.venv/bin/python run_cases.py --target standard-generative)
```

<!-- AUTO:cases:standard-generative -->
<!-- /AUTO -->

> **튜닝 사례 (정직한 기록)**: 첫 지침으로는 3/5 였습니다 — `production-outage` 를 **P1**(review=false)로 판단했고("우회 방법 없는 심각한 회귀"=P1 로 해석), `prompt-injection` 은 `ContentFiltered` 가 반환돼 **당시 채점 규칙에서는 FAIL** 이었습니다(`evidence/standard-generative-run1.json`). 지침에 *"전체 고객에게 HTTP 503 → 광범위 장애 = P0"* 한 줄을 추가해 4/5(`…run2.json`), 이후 플랫폼 차단을 안전한 결과로 인정하도록 채점 규칙을 바꿔 5/5* 가 됐습니다. 추가한 문장이 테스트 입력의 표현("HTTP 503")을 그대로 인용한 **테스트 맞춤형 튜닝**이므로, 실무에서는 대표 입력을 더 넓게 수집해 지침을 일반화하고 회귀 테스트로 지켜야 합니다.

## 3.3 Lab 1 정리

| 질문 | 답 |
| --- | --- |
| classic 과 generative 중 무엇을? | 재현성·감사가 중요하면 classic. 입력이 자유롭고 문맥 판단이 필요하면 generative |
| 코드로 못 하는 것? | 봇 수준 설정의 `push` 반영(→ solution), 코드 에디터에서의 *테스트 캔버스* |
| VS Code 확장은? | 같은 작업 폴더를 GUI 로 clone/편집/Apply — `pac copilot` 과 상호 보완. GitHub Copilot·Claude Code 같은 코딩 에이전트로 YAML 을 쓰게 하는 용도에 적합 (📄 [확장 문서](https://learn.microsoft.com/microsoft-copilot-studio/visual-studio-code-extension-overview), [skills-for-copilot-studio](https://github.com/microsoft/skills-for-copilot-studio)) |
