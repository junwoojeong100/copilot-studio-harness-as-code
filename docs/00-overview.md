# Copilot Studio 하네스 코드 실습 — Standard · GitHub Copilot · Copilot chat

> **한 줄 요약** — Copilot Studio 의 세 가지 하네스(harness)로 *같은* GitHub 이슈 분류 에이전트를 **포털 클릭 없이 코드만으로** 만들고, 같은 5개 테스트 케이스로 실제 테넌트(Caldova)에서 검증합니다.

| 항목 | 값 |
| --- | --- |
| 검증 일시 | 2026-10-17 (KST), 모든 명령은 아래 테넌트에서 **실제로 실행**해 확인 |
| 테넌트 / 계정 | `caldova10993123.onmicrosoft.com` / `admin@caldova10993123.onmicrosoft.com` (Global Administrator) |
| Copilot Studio 환경 | **Caldova (default)** — `Default-8109d700-b6b0-4088-ba33-dc39ef13d7ea`, Canada East |
| Azure 구독 | `e56daab3-ddd7-41f4-838b-6c938acd874c` (MCP 서버 호스팅, PAYG 과금 정책 API) |
| 대상 독자 | Copilot Studio 를 "코드로" 다루려는 개발자·SE (Azure/Power Platform CLI 경험자) |
| 소요 시간 | 직접 따라 하면 3~4시간, 스크립트(`scripts/`)로 재현하면 약 30분 |
| 이전 실습과의 관계 | 포털로 만든 [copilot-studio-harness-labs](https://github.com/junwoojeong100/copilot-studio-harness-labs)(Standard·GitHub 비교)의 **코드 기반·세 하네스 확장판** (같은 시나리오·같은 출력 계약) |

## 1. "하네스"란 무엇인가

Copilot Studio 에서 만드는 모든 것은 **하네스(runtime)** 위에서 실행됩니다. 하네스는 *언제 모델을 호출하고, 무엇을 모델에 보내고, 응답을 어떻게 해석하고, 어떤 도구를 호출할지*를 결정하는 런타임입니다. 모델 선택보다 먼저 오는 **아키텍처 결정**입니다. (근거: [Harnesses in Copilot Studio](https://learn.microsoft.com/microsoft-copilot-studio/harnesses-overview), 2026-09 갱신)

| 하네스 | 한마디 | 코드로 만드는 것 | 이 실습의 에이전트 |
| --- | --- | --- | --- |
| **Standard** | 규칙 기반·예측 가능. classic(토픽만) / generative(모델이 선택) 두 오케스트레이션 | 토픽 YAML + Power Fx, `agent.mcs.yml` 지침 | `Issue Triage Standard`, `Issue Triage StdGen` |
| **GitHub Copilot** | 목표를 스스로 단계로 분해하는 agentic loop. skills·memory·샌드박스(Bash) | `settings.mcs.yml`, skills(SKILL.md+스크립트), knowledge 파일, tools(MCP 등) | `Issue Triage GitHub` (+ `Issue Triage MCP`) |
| **Copilot chat** | Microsoft 365 Copilot Chat 을 조직 지식으로 확장하는 **선언형 에이전트** | `manifest.json` + `declarativeAgent.json` (앱 패키지) | `Issue Triage Copilot` |

> GitHub Copilot harness 는 "Copilot Studio 의 저작·오케스트레이션 프레임워크"이며 **GitHub Copilot 서비스가 아닙니다**. 고객 데이터는 GitHub Copilot 서비스로 전송되지 않습니다.

## 2. 코드로 쓰는 "여러 하네스 옵션" 한눈에 보기

이 실습은 하네스 **3종**과 각 하네스 안의 **옵션**을 모두 코드로 건드립니다. (✅ = 이번 실행에서 검증, 📄 = 문서·소스 기준으로만 설명)

| 영역 | 옵션 | 코드 경로 | 상태 |
| --- | --- | --- | --- |
| Standard | classic orchestration (토픽+Power Fx, 결정론적) | `pac copilot init` → YAML → `pack` + `solution import` | ✅ |
| Standard | generative orchestration (지침 기반) | `agent.mcs.yml` + `pac copilot push` | ✅ |
| GitHub Copilot | 지침 / 모델(`Sonnet46`·`Opus47`·`GPT55Chat`·`GPT5Chat`) 선택 | `settings.mcs.yml` + `push` | ✅ |
| GitHub Copilot | knowledge (업로드 파일) | `capabilities/knowledge/files/` | ✅ |
| GitHub Copilot | skill + 스크립트(샌드박스 Bash 실행) | `add-skill.js import` | ✅ |
| GitHub Copilot | tool — **MCP 서버(Azure Container Apps)** | 커스텀 커넥터 + 연결 + `McpTool` YAML | ✅ (Lab 4) |
| GitHub Copilot | 작성 도구: GitHub Copilot CLI + `mcs-assistant` 플러그인 (VS Code 확장은 📄) | 플러그인 설치 ✅ / 대화형 작성·확장 📄 | ✅📄 |
| Copilot chat | 선언형 에이전트(지침·대화 시작 문구) → M365 Copilot | 앱 패키지 + Graph 앱 카탈로그 | ✅ |
| Copilot chat | `wiqd`(Work IQ Dev Tools) / M365 Agents Toolkit(`atk`) | CLI | 📄 |
| 호출 방식 | Microsoft 365 Agents SDK `CopilotClient` (Python) | Direct-to-engine / agenticruntime 3p | ✅ |
| 수명주기 | solution export/import, clone, pack, delete | `pac solution`, `pac copilot` | ✅ |
| Azure | PAYG 과금 정책 생성·삭제(Power Platform API + ARM) | REST | ✅ (환경 링크는 과금 영향으로 미실행) |

## 3. 전체 구조

```text
            ┌──────────────── 이 저장소의 코드 ────────────────┐
            │  shared/  : label-policy · test-cases · classifier │
            │  harness/ : Agents SDK 테스트 하네스(Python)        │
            │  labs/    : 하네스별 오버레이·패키지·MCP 서버        │
            │  scripts/ : 단계별 재현 스크립트                     │
            └───────┬───────────┬─────────────┬─────────────────┘
        pac copilot │           │ pac copilot │ Microsoft Graph
        (classic)   │           │ (cli-copilot)│ (appCatalogs)
                    ▼           ▼             ▼
        ┌─────────────┐  ┌────────────────┐  ┌─────────────────────┐
        │ Standard    │  │ GitHub Copilot │  │ Copilot chat        │
        │ harness     │  │ harness        │  │ harness (선언형)     │
        └──────┬──────┘  └───────┬────────┘  └──────────┬──────────┘
   published   │   agenticruntime│ 3p                   │ M365 Copilot
   endpoint    ▼                 ▼                      ▼
        Agents SDK(CopilotClient) ──── harness/run_cases.py        (UI 확인)
                                      └─ 같은 5개 케이스 · 같은 JSON 계약 ─┘
                                 GitHub harness 의 tool ──► Azure Container Apps (MCP 서버)
```

## 4. 이 문서를 읽는 방법

* 각 Lab 은 **① 만들기 → ② 푸시/배포 → ③ 호출 → ④ 검증** 순서이며, 모든 명령은 `scripts/` 에 같은 내용이 들어 있습니다.
* `✅ 검증` 표시는 위 테넌트에서 2026-10-17 에 실제로 실행해 통과한 것입니다. 실제 출력은 `evidence/` 와 [VERIFICATION_REPORT.md](VERIFICATION_REPORT.md) 에 있습니다.
* "🐞 실제로 만난 문제" 상자는 검증 중 겪은 오류와 해결입니다(재현하면 같은 오류를 만날 수 있습니다).
* **비용**: GitHub Copilot harness 는 만들기·테스트·평가에도 Copilot Credits 가 소모됩니다. 이 실습의 호출량(에이전트당 수십 회)은 소량입니다. Azure ACR+Container Apps(최소 1 replica)는 합계 하루 약 US$0.3~0.4(소매가 기준 추정)입니다. 끝나면 [10장 정리](#10-정리)로 모두 삭제하세요.
