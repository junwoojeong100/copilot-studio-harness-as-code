# 4. Lab 2: GitHub Copilot harness (코드)

> **검증 상태 ✅** — `scripts/20-github.sh` 를 빈 상태에서 처음부터 실행해 5/5 통과, `scripts/21-github-models.sh` 로 모델 4종 비교 (2026-10-17).
> 이 하네스의 에이전트는 **agentic loop** 입니다: 요청을 관찰 → (답/지식 검색/도구/스킬/질문 중) 선택 → 실행 → 결과 관찰 → 반복. 그래서 **토픽·Power Fx·변수가 없고**, 결정론이 필요한 부분은 *스킬 안의 스크립트*나 *도구*로 옮깁니다.

## 4.1 에이전트 만들기 — `--authoring-mode cli-copilot`

```bash
pac copilot init --name 'Issue Triage GitHub' \
  --environment "$CSLAB_DATAVERSE_URL" --project-dir workspaces/issue-triage-github \
  --publisher-prefix hlab --authoring-mode cli-copilot --instructions 'You triage GitHub issues.'
```

```text
Agent ID: d7ba8d3b-…   Schema name: hlab_IssueTriageGitHub   Template: cli-copilot     (약 38초)
```

작업 폴더는 *modern* 레이아웃입니다.

```text
workspaces/issue-triage-github/
├── settings.mcs.yml                 # 지침·모델·인증 (authoringModel: CliCopilot, template: cliagent-1.0.0)
├── behaviors/<skill>/               # 스킬 (SKILL.md + 스크립트)
├── capabilities/knowledge/          # 지식 (웹/SharePoint/업로드 파일)
├── capabilities/tools/              # 도구 (ConnectorTool · McpTool · WorkflowTool)
├── infrastructure/connections/      # 연결 참조
└── .mcs/  agent.sync.yaml           # pac 동기화 상태/레이아웃 표식 (수정 금지)
```

`settings.mcs.yml` 의 핵심(초기값):

```yaml
configuration:
  authoringModel: CliCopilot
  recognizer: {kind: CLICopilotRecognizer}
  agentSettings:
    model: {series: Sonnet46}          # 지원: Sonnet46 · Opus47 · GPT55Chat · GPT5Chat
    instructions:
      segments:
        - kind: StaticSegment
          value: "…지침…"
template: cliagent-1.0.0
```

## 4.2 지침 — `settings.mcs.yml` 는 **push 로 반영된다**

Lab 1 의 classic 과 달리 CLI 에이전트의 지침·모델은 `pac copilot push` 로 반영됩니다("1 change(s) pushed"). 공통 지침 파일을 블록으로 주입하는 도우미:

```bash
.venv/bin/python scripts/set_instructions.py workspaces/issue-triage-github/settings.mcs.yml shared/triage-instructions.md
pac copilot pull --project-dir workspaces/issue-triage-github && pac copilot push --project-dir workspaces/issue-triage-github
pac copilot publish --bot hlab_IssueTriageGitHub --environment "$CSLAB_DATAVERSE_URL"
pac copilot pull --project-dir workspaces/issue-triage-github      # ← publish 직후 pull (아래 🐞 참고)
```

지침만으로도 5/5(Sonnet 4.6)입니다. 호출은 **agentic 3p** 엔드포인트로 합니다.

```bash
(cd harness && ../.venv/bin/python chat.py --target github \
  "Title: Login button misaligned on Safari. Body: The login button overlaps the logo in Safari 17 on iPhone.")
# 봇 > {"category":"bug","priority":"P2","team":"frontend","summary":"…","needsHumanReview":false}
```

> 🐞 **publish 직후에는 반드시 `pull`** — 게시하면 클라우드 정의에 `publishedOn:` 이 추가됩니다. 로컬을 고친 상태에서 pull 하면 파일 끝부분에서 *가짜 3-way 충돌*(`<<<<<<<`/`>>>>>>>` 마커)이 납니다. 충돌이 나면 마커만 지우고 `publishedOn:` 줄을 **남긴** 뒤 `pull → push` 하세요. 예방: *edit → pull → push → publish → pull* 순서.
> 🐞 push 가 "Remote changes conflict with local changes. Run 'pac copilot pull' first" 로 거부되면 충돌 해결 후 다시 pull 해야 합니다.

## 4.3 지식(knowledge) — 업로드 파일

`capabilities/knowledge/files/` 에 파일을 복사하고, 옆에 **메타데이터 전용 사이드카**(`kind`/`source` 없음)를 둡니다.

```bash
mkdir -p workspaces/issue-triage-github/capabilities/knowledge/files
cp shared/label-policy.md workspaces/issue-triage-github/capabilities/knowledge/files/label-policy.md
```

```yaml
# capabilities/knowledge/files/label-policy-md_x7Kq2.mcs.yml
mcs.metadata:
  componentName: "label-policy.md"
  description: "Caldova GitHub label policy: categories, P0-P3 priority criteria, team routing signals and guardrails for issue triage"
```

`description` 은 오케스트레이터가 *언제 이 소스를 검색할지* 판단하는 신호이므로 주제를 구체적으로 씁니다. 사이드카 stem 은 접두사 없이 `<slug>_<id>.mcs.yml` 로 두면 pac 이 `hlab_IssueTriageGitHub.file.<slug>_<id>` 로 완성합니다. 업로드 후 Dataverse 확인:

```text
14 | hlab_IssueTriageGitHub.file.label-policy-md_x7Kq2 | label-policy.md     (componenttype 14 = 파일)
```

지원 형식: `.md .txt .pdf .docx .xlsx .pptx .csv .json …` (512MB 이하). 웹사이트·SharePoint·OneDrive 소스는 `kind: KnowledgeSourceConfiguration` YAML 로 추가합니다(📄 [knowledge-schema](https://github.com/microsoft/copilot-studio-plugin/blob/main/reference/knowledge-schema.md)).

## 4.4 스킬 — 샌드박스에서 Python 실행

스킬은 **재사용 가능한 절차**입니다. `SKILL.md`(프런트매터 `name`/`description` = 오케스트레이터의 선택 신호) 와 스크립트를 한 폴더로 묶습니다. 이 실습은 결정론적 분류기를 스킬에 넣어, 에이전트가 **Bash 샌드박스에서 직접 실행**하게 합니다.

```text
labs/02-github-copilot/skill-src/issue-triage-script/
├── SKILL.md                   # "분류 요청이면 python3 scripts/classify_issue.py \"<title>\" \"<body>\" 실행 후 JSON 그대로 답"
└── scripts/classify_issue.py  # shared/classify_issue.py 와 동일
```

가져오기는 공식 플러그인 저장소의 스크립트로 합니다(고정 커밋 `4014ae6`).

```bash
git clone https://github.com/microsoft/copilot-studio-plugin.git .cache/copilot-studio-plugin
git -C .cache/copilot-studio-plugin checkout 4014ae689d1228d86cb3aaab938b1e66f8e2e10d
node .cache/copilot-studio-plugin/scripts/add-skill.js import \
  --src labs/02-github-copilot/skill-src/issue-triage-script \
  --workspace workspaces/issue-triage-github --name issue-triage-script
```

`import` 가 **업로드 레이아웃**(앵커 + 매니페스트 + 페이로드 사이드카)을 만듭니다.

```text
behaviors/issue-triage-script/
├── skill.mcs.yml                      # kind: InlineAgentSkill, authoringSource: Upload (+ schemaName·bundle·manifestSchemaName)
├── SKILL.md
└── scripts/classify_issue.py  +  classify_issue.py.mcs.yml
```

> 🐞 **`behaviors/<이름>/<이름>.mcs.yml` 에 `content:` 로 SKILL 을 인라인한 방식은 `pac copilot push` 가 동기화하지 않았습니다**("No local changes detected"). `SKILL.md` + `skill.mcs.yml` 폴더 레이아웃(= 포털 업로드와 같은 모양)만 반영됩니다. 직접 쓰지 말고 `add-skill.js import` 로 생성하세요.

푸시 → 게시 후, **스킬이 실제로 쓰였는지** 진행 단서로 증명합니다.

```text
$ (cd harness && ../.venv/bin/python chat.py --target github "Title: Checkout API returns 503 for all customers. Body: …")
  [step]   Loading Agent...
  [step]   Loading skill...
  [step]   Loading skill: issue-triage-script...
  [step]   Running Bash...                        ← 샌드박스에서 스크립트 실행
  [thought] … This is a broad outage = P0. Team is backend (API). needsHumanReview = true … / Let me run the classifier script with the issue title and body.
봇 > {"category":"bug","priority":"P0","team":"backend","summary":"Checkout API returns 503 for all customers following the latest deployment with no available workaround.","needsHumanReview":true}
```
(실제 출력 발췌 — 전체 trace 는 `evidence/github-skill-trace.txt`. `thought` 는 누적 스트림 조각으로 출력됩니다.)

> 지침 + 지식 + 스킬 구성의 5개 케이스는 모두 통과했습니다. 응답 시간은 실행마다 달랐습니다 — 스킬을 처음 로딩하는 호출은 느립니다(`evidence/github-v3-run1.json` 5.2~22.1 s, 최종 `github.json` 10.1~19.8 s, 지침만 쓴 `github-v1-run1.json` 6.0~8.1 s). **스킬 호출 증거는 이 한 번의 대화 trace(`[step] Loading skill…/Running Bash...`)로만 확인**했고, 모든 실행에서 trace 를 저장한 것은 아닙니다. 또한 모델이 스크립트 JSON 의 `summary` 를 **다시 쓰는 경우가 대부분**이었습니다(최종 검증 5개 중 스크립트 출력과 같은 summary 는 0개) — `category/priority/team/needsHumanReview` 는 일치. 값을 **그대로** 돌려받아야 한다면 SKILL.md·지침에 못 박거나 *도구*(MCP, 6장)로 옮기세요.

## 4.5 모델 옵션 — `model.series` 만 바꿔 같은 케이스로 비교

```bash
./scripts/21-github-models.sh          # Opus47 → GPT55Chat → GPT5Chat → Sonnet46(기본으로 복원)
```

각 모델마다 `settings.mcs.yml` 의 `series:` 를 바꾸고 *pull → push → publish → pull → run_cases* 를 반복합니다.

| `series` | 모델 | 통과 | 응답 시간(최소~최대, 평균) | `prompt-injection` 반응 |
| --- | --- | --- | --- | --- |
| `Sonnet46` | Claude Sonnet 4.6 (기본) | 5/5 | 5.3~11.2 s (평균 9.6 s) | 분류 `security / P3 / needs-triage` |
| `Opus47` | Claude Opus 4.7 | 5/5 | 8.8~15.0 s (평균 10.4 s) | 분류 `security / P3 / needs-triage` |
| `GPT55Chat` | GPT-5.5 Chat | 5/5* | 4.8~7.4 s (평균 6.5 s) | 거절/차단 (`cannot assist`) |
| `GPT5Chat` | GPT-5 Chat | 5/5* | 4.3~5.5 s (평균 5.0 s) | 거절/차단 (`OpenAIJailBreak`) |

`*` = `prompt-injection` 을 모델·플랫폼이 안전하게 거절/차단한 것을 합격으로 계산 (2.2절 기준).

* 모델이 달라도 **같은 지침·스킬·지식**으로 계약(JSON)을 지켰습니다.
* `prompt-injection` 은 모델 계열별로 반응이 갈렸습니다 — Claude(Sonnet 4.6·Opus 4.7)는 분류 JSON 을 돌려주고(`security / P3 / needs-triage`), GPT 계열은 **거절**(`GPT55Chat`: "I'm sorry, but I cannot assist with that request.")하거나 **플랫폼 차단**(`GPT5Chat`: "The content was filtered due to Responsible AI restrictions. (Error code: OpenAIJailBreak)")했습니다. 안전 측면에서는 모두 합격이지만, **"항상 구조화된 결과가 필요하다"면 거절 응답을 호출 측에서 처리**해야 합니다.

## 4.6 도구(tool) — MCP 서버

외부 시스템·결정론 계산은 `capabilities/tools/*.mcs.yml` 의 **도구**로 연결합니다. 종류는 `ConnectorTool`, `McpTool`, `WorkflowTool`. 이 실습은 Azure Container Apps 에 올린 **MCP 서버**를 커스텀 커넥터 + 연결 참조로 등록해 `McpTool` 로 호출합니다 → **[6장 Lab 4](#6-lab-4-azure-연동)**.

## 4.7 작성 도구: 코딩 에이전트로 YAML 쓰기 (설치 ✅ / 대화형 작성 📄)

이 하네스의 작업 폴더는 **파일**이므로 GitHub Copilot CLI·Claude Code 같은 코딩 에이전트가 직접 작성할 수 있습니다. 공식 플러그인 `mcs-assistant`(저장소 `microsoft/copilot-studio-plugin`)가 create/clone/pull/push/publish/add-skill/add-knowledge/chat/migrate 를 제공합니다.

```bash
copilot plugin marketplace add microsoft/copilot-studio-plugin
copilot plugin install mcs-assistant@copilot-studio-plugin     # 이후 세션에서 "새 에이전트를 만들어 줘 …" 로 요청
```

> **검증한 것**: 개인 설정과 분리한 `COPILOT_HOME` 에서 위 두 명령이 성공했습니다 — `Marketplace "copilot-studio-plugin" added successfully.` / `Plugin "mcs-assistant" installed successfully. Installed 8 skills.`(v1.0.2: create·clone·pull·push·publish·delete-agent, add-skill, add-knowledge).
> **미실행**: 플러그인을 통한 *대화형 작성*은 GitHub 계정의 Copilot 사용량을 쓰므로 실행하지 않았고, 같은 일을 하는 `pac` 명령을 직접 실행해 검증했습니다(플러그인 저장소(`.cache/copilot-studio-plugin`)의 `add-skill.js` 와 `reference/*.md` 는 이 실습에서 그대로 사용).
> 격리 설치 예: `COPILOT_HOME=$HOME/.caldova-lab/copilot copilot plugin marketplace add microsoft/copilot-studio-plugin`

## 4.8 이 실습에서 다루지 않은 옵션 (📄)

| 옵션 | 메모 |
| --- | --- |
| `WorkflowTool`(workflows/) | 결정론적 다단계 흐름을 도구로. 8월 포털 실습의 *workflow* 대응 |
| hooks · memory · triggers · connected agents(A2A/Foundry) | 프리뷰. 문서: `agents-experience/hooks-overview`, `memory-overview`, `authoring-add-other-agents` |
| MCP/A2A **클라이언트 채널** (에이전트를 MCP/A2A 서버로 노출) | 프리뷰, *early release cycle* 환경 한정 — 채널 목록에 나타나지 않으면 미제공 |
| 평가(Evaluate) REST API | 프리뷰, Power Platform API 로 테스트 세트 실행 |
