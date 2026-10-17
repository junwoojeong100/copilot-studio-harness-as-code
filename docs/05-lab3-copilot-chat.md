# 5. Lab 3: Copilot chat harness (코드)

> **검증 상태 ✅** — 앱 패키지 생성·스키마 검증·Graph 게시/설치·재배포를 실행했고, Microsoft 365 Copilot 에서 5개 케이스를 확인했습니다 (2026-10-17). 런타임 대화는 SDK/REST 가 없어 **UI 로 확인**했습니다.

**Copilot chat harness** 는 Microsoft 365 Copilot Chat 을 조직 지식과 지침으로 확장하는 **선언형 에이전트**(declarative agent)입니다. 오케스트레이터·모델·보안 경계는 M365 Copilot 의 것을 그대로 쓰고, 개발자는 *설정(JSON)* 만 줍니다. 비용은 소비 기반이거나 M365 Copilot 라이선스에 포함되며 **내부 사용자에게만** 게시됩니다.

> Learn: "Agent Builder 로 만든 선언형 에이전트는 Copilot chat harness 의 예" — 같은 M365 Copilot 채널에 **다른 하네스** 에이전트도 게시될 수 있으므로 *게시 채널만으로 하네스를 구분할 수 없습니다*.

## 5.1 앱 패키지 = 코드

선언형 에이전트는 Teams 앱 패키지(zip) 안의 JSON 두 개와 아이콘입니다.

```text
labs/03-copilot-chat/
├── build_package.py       # 매니페스트·에이전트 JSON 생성 + zip (shared/triage-instructions.md 를 지침으로 사용)
├── validate_package.py    # 공식 JSON Schema 로 오프라인 검증
├── m365_publish.py        # Graph: 카탈로그 게시 + 설치 + 확인 (+ --uninstall)
└── appPackage/            # manifest.json · declarativeAgent.json · color.png · outline.png
```

```bash
.venv/bin/python labs/03-copilot-chat/build_package.py --version 1.0.0
# app id : 4e705395-…  (처음 한 번 생성해 .app-id 에 저장 — 재배포 때 같은 ID 유지)
# package: build/issue-triage-copilot.zip (2796 bytes)
```

`declarativeAgent.json` (발췌, 스키마 v1.5):

```json
{
  "$schema": "https://developer.microsoft.com/json-schemas/copilot/declarative-agent/v1.5/schema.json",
  "version": "v1.5",
  "name": "Issue Triage Copilot",
  "description": "Caldova GitHub 이슈를 라벨 정책에 따라 분류(category/priority/team/needsHumanReview)합니다.",
  "instructions": "You are a GitHub issue triage assistant … (shared/triage-instructions.md 전체)",
  "conversation_starters": [{"title": "서비스 장애 이슈 분류", "text": "Title: Checkout API returns 503 …"}]
}
```

`manifest.json`(Teams 앱 매니페스트 v1.22)에는 `id`(앱 GUID), `developer`, `icons`, 그리고 에이전트를 가리키는 한 줄이 핵심입니다.

```json
"copilotAgents": {"declarativeAgents": [{"id": "issueTriageCopilot", "file": "declarativeAgent.json"}]}
```

지식(knowledge)을 붙이려면 `capabilities` 에 OneDrive/SharePoint 항목을 넣습니다(`build_package.py --knowledge-url <URL>` 이 생성, 스키마 검증까지만 했고 **런타임은 미검증** — 관리자 OneDrive 가 프로비저닝돼 있지 않았습니다).

```json
"capabilities": [{"name": "OneDriveAndSharePoint", "items_by_url": [{"url": "https://…/label-policy.md"}]}]
```

## 5.2 오프라인 검증 — 배포 전에 스키마로 거른다

```bash
.venv/bin/python labs/03-copilot-chat/validate_package.py
# OK   manifest.json            (v1.22)
# OK   declarativeAgent.json    (v1.5)
```

> 🐞 **실제로 걸린 오류**: 대화 시작 문구(`conversation_starters[].text`)에 줄바꿈(`\n`)을 넣으면 스키마(`^(?!…\[\[…).*$`, `.` 는 개행 불일치)에서 거부됩니다. 한 줄로 쓰세요. 지침은 문자열 8,000자 이내여야 합니다(이 실습은 약 2KB).

## 5.3 배포 — Microsoft Graph (Teams 앱 카탈로그)

Azure CLI 의 Graph 토큰에는 앱 카탈로그 범위가 없습니다(`Application.ReadWrite.All` 등만 있음). 그래서 1장에서 만든 **전용 앱 등록**에 Graph 위임 권한 `AppCatalog.ReadWrite.All`, `TeamsAppInstallation.ReadWriteForUser`, `User.Read` 를 추가·동의했습니다(`scripts/01-entra-app.sh`).

```bash
./scripts/30-copilot-chat.sh 1.0.0       # = build → validate → m365_publish.py
```

`m365_publish.py` 는 (1) 디바이스 코드 로그인(최초 1회, 사용자 동의 화면에서 *Accept*), (2) `POST /appCatalogs/teamsApps?requiresReview=false`(zip 본문), (3) `POST /me/teamwork/installedApps`, (4) 설치 목록으로 확인을 수행합니다.

```text
카탈로그 게시: 201 {"id": "7013dd3d-…", "externalId": "4e705395-…", "displayName": "Issue Triage Copilot", "distributionMethod": "organization"}
사용자 설치: 201 ok
설치 확인: [('Issue Triage Copilot', 'organization')]
```

* 카탈로그의 `id` 와 매니페스트 `id`(= `externalId`)는 다릅니다.
* **재배포**는 매니페스트 `version` 을 올리고(`30-copilot-chat.sh 1.0.1`) 같은 스크립트를 다시 실행합니다 → `POST …/appDefinitions`(201) 로 새 정의가 올라가고, 설치는 `409 already exists`(정상)로 건너뜁니다. 같은 버전을 다시 올리면 거부됩니다.
* 조직 전체 배포·승인 정책(Teams 관리 센터)은 테넌트 설정을 따릅니다. 이 테넌트에서는 전역 관리자 호출이라 `requiresReview=false` 로 즉시 게시됐습니다.

## 5.4 런타임 확인 — Microsoft 365 Copilot

`https://m365.cloud.microsoft/chat` → 왼쪽 **Agents** → **Issue Triage Copilot** (채팅 URL: `…/chat/agent/T_<앱 GUID>.issueTriageCopilot/conversation/…`).

| 케이스 | 응답 | 결과 |
| --- | --- | --- |
| production-outage | `{"category":"bug","priority":"P0","team":"backend","summary":"Checkout API returns HTTP 503 for all customers …","needsHumanReview":true}` | ✅ |
| docs-typo | `documentation / P3 / docs / false` | ✅ |
| possible-secret-exposure | `security / P1 / security / true` | ✅ |
| prompt-injection | **"Hmm...it looks like I can't chat about this. Let's try a different topic."** (플랫폼이 차단) | ✅ 안전한 차단 |
| ambiguous-request | `bug / P3 / needs-triage / true` | ✅ |

증빙: `evidence/copilot-chat-ui-run1.json`, 스크린샷 두 장.

![Issue Triage Copilot — 장애 이슈 분류](evidence/copilot-chat-ui-outage.png)

![Issue Triage Copilot — 주입 입력은 플랫폼이 차단](evidence/copilot-chat-ui-injection-blocked.png)

> **왜 SDK 로 못 하나?** Microsoft 365 Copilot **Chat API**(프리뷰)는 *선언형 에이전트를 지정*할 수 없습니다(Copilot 자체와 대화). 코드로 에이전트에 질문하려면 `wiqd agent ask`(아래)를 쓰거나 UI 를 사용합니다.

## 5.5 대안 도구 (📄 설명만, 이번에 실행하지 않음)

| 도구 | 내용 | 이번 환경에서 확인한 제약 (**배포는 실행하지 않음** — `wiqd` 는 설치·`doctor` 진단만) |
| --- | --- | --- |
| **Work IQ Dev Tools (`wiqd`)** — `microsoft.github.io/wiqd` | `wiqd agent create / validate / provision / publish / share / ask / eval / monitor` 로 선언형 에이전트 수명주기 전체 | npm `@microsoft/wiqd` 0.18.0 은 **Node ≥ 24.15** 필요(여기는 22.16 → `EBADENGINE`, `wiqd doctor` 가 확장 비호환 경고). `wiqd auth login` 은 **실제 TTY 가 필요**하고 자동화에서 호출 금지(문서) |
| **Microsoft 365 Agents Toolkit (`atk`)** — npm `@microsoft/m365agentstoolkit-cli` 1.1.x | `atk new` 스캐폴드 → `atk provision`(사이드로딩) → `atk publish`, TypeSpec 지원 | M365 로그인이 브라우저 기반 |
| Teams 관리 센터 업로드 | 같은 zip 을 수동 업로드 | UI |

이 실습의 Graph 방식은 위 도구들이 하는 **카탈로그 게시/설치를 직접 호출**한 것이라 CI 에서 재현하기 쉽습니다(서비스 주체/워크로드 ID 로 바꾸려면 앱 권한으로 전환 필요).

## 5.6 정리

```bash
.venv/bin/python labs/03-copilot-chat/m365_publish.py --uninstall      # 카탈로그에서 삭제(설치도 함께 제거)
```
