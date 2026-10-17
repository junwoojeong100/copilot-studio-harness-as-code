# 검증 보고서

**일시**: 2026-10-17 (KST) 11:30–14:40경 · **수행**: Microsoft Scout (Claude Sonnet 5.5) + 서브 에이전트 2개(Azure MCP 서버, Copilot Studio 연결)
**대상**: 테넌트 `caldova10993123.onmicrosoft.com`(`8109d700-b6b0-4088-ba33-dc39ef13d7ea`) · 환경 **Caldova (default)** (`Default-8109d700-…`, Canada East) · 구독 `e56daab3-ddd7-41f4-838b-6c938acd874c`
**계정**: `admin@caldova10993123.onmicrosoft.com` (Entra Global Administrator, Dataverse `Environment Maker`+`Basic User`)

## 1. 실행 환경

| 항목 | 버전 |
| --- | --- |
| Power Platform CLI | **2.13.1** (시작 시 2.10.1 → `dotnet tool update -g` 로 갱신. 2.10.1 은 `pull` 병합 충돌에서 예외 종료) |
| Azure CLI / Bicep | 2.86.0 / 0.48.1 · .NET 10.0.301 · Node 22.16.0 · Python 3.14.6 |
| SDK | `microsoft-agents-copilotstudio-client` 1.8.0, `msal` 1.39, `mcp==1.30.0`(서버) |
| 플러그인 | `microsoft/copilot-studio-plugin` @ `4014ae6`(add-skill.js) |
| 로그인 | `az`(격리 구성 디렉터리) · `pac` 프로필 `caldova` · MSAL 디바이스 코드(SDK 앱) — 모두 브라우저 승인 필요(관리자 계정은 패스키) |

## 2. 결과 요약

| # | 항목 | 방법 | 결과 | 증빙 |
| --- | --- | --- | --- | --- |
| 1 | 사전 점검 | `00-preflight.sh` | ✅ pac≥2.13, 환경 Ready, 라이선스·Credits 확인 | `evidence/run-log.md` §2 |
| 2 | Standard classic — 빈 상태에서 재현 | `10-standard-classic.sh` (2분 27초) | **5/5**, 모든 필드 값이 `classify_issue.py` 와 동일 | `evidence/standard-classic.json` |
| 3 | Standard generative — 재현 | `11-standard-generative.sh` (2분 26초) | 5/5* (`ContentFiltered`) · 튜닝 전 3/5 | `evidence/standard-generative*.json` |
| 4 | GitHub harness — 재현 | `20-github.sh` (2분 04초): init→지침→지식→스킬→push→publish | **5/5**, 대화 trace 1건에서 `Loading skill` → `Running Bash...` 확인 | `evidence/github*.json`, `evidence/github-skill-trace.txt` |
| 5 | 모델 옵션 4종 | `21-github-models.sh` (약 8분) | Sonnet46 5/5 · Opus47 5/5 · GPT55Chat 5/5* · GPT5Chat 5/5* | `evidence/github-model-*.json` |
| 6 | MCP 서버 (ACA, koreacentral) | 서브 에이전트 | 로컬·공개 **16/16**, 401 검증, curl 동등 확인 | `labs/04-azure-mcp/EVIDENCE.md` |
| 7 | MCP → Copilot Studio 도구 | 서브 에이전트 + `90-verify-all.sh` | **5/5**, `Calling Classify GitHub issue...`, 서버 `CallToolRequest` 로그 | `labs/04-azure-mcp/copilot-studio/EVIDENCE.md`, `evidence/github-mcp.json` |
| 8 | Copilot chat harness | 스키마 검증 + Graph 게시(201)/설치(201)/재배포(201) + M365 Copilot UI(수동) | 5/5* (주입은 "can't chat about this") | `evidence/run-log.md` §4, `evidence/copilot-chat-ui-run1.json`, `…-outage.png`, `…-injection-blocked.png` |
| 9 | ALM | `50-alm.sh`: export→delete→import→publish(재시도)→테스트→clone | ✅ 5/5 재통과, Copilot ID 변경(→clone) | `evidence/alm-roundtrip.json` |
| 10 | PAYG 과금 정책 | provider 등록 → 정책 생성(201)/조회/삭제(204) | ✅ (환경 링크: 더미 ID 400 으로 엔드포인트만 확인, **미실행**) | `evidence/run-log.md` §5 |
| 11 | 최종 전체 검증 | `90-verify-all.sh` (2분 35초) | classic 5/5 · generative 5/5* · github 5/5 · github-mcp 5/5 | `evidence/summary.md` |

`*` = 프롬프트 주입 케이스의 안전한 거절/차단을 합격으로 계산.

## 2.1 증거 파일 안내 (`evidence/`)

| 파일 | 내용 |
| --- | --- |
| `standard-classic-run1.json` → `…-run2.json` | 첫 실행 **4/5**(Power Fx 정규식 백슬래시 이중 이스케이프 버그) → 수정 후 **5/5** |
| `standard-generative-run1.json` → `…-run2.json` | 지침 튜닝 전 3/5(P1 오분류·`ContentFiltered`) → 튜닝 후 4/5 → (채점 규칙 보강 후) 5/5* |
| `github-v1-run1.json` / `github-v3-run1.json` | 지침만 5/5 / 지침+지식+스킬 5/5 |
| `github-model-<series>.json` | 모델 4종 비교(`21-github-models.sh`) |
| `standard-classic.json`·`standard-generative.json`·`github.json`·`github-mcp.json`·`summary.md` | 최종 `90-verify-all.sh` 결과(스크립트를 다시 돌리면 덮어씀) |
| `github-skill-trace.txt` | 스킬 로딩·`Running Bash...` 단서가 찍힌 대화 trace 1건 |
| `run-log.md` | 다른 파일로 남지 않은 결과(로그인·소요 시간·Graph·PAYG·사전 점검 출력)를 옮겨 적은 기록 |
| `alm-roundtrip.json` | export→삭제→import 후 재검증 |
| `copilot-chat-ui-run1.json`, `copilot-chat-ui-outage.png`, `copilot-chat-ui-injection-blocked.png` | M365 Copilot UI 에서 확인한 선언형 에이전트 5개 케이스 |

## 3. 실제로 발견한 문제 (해결은 가이드 9장)

`pac` 2.10.1 `pull` 예외 · classic 설정이 `push` 로 반영 안 됨(→ pack+import) · 새 토픽 미등록 상태의 pack → `Component is missing Id` · publish 후 `publishedOn` 으로 인한 가짜 병합 충돌 · 인라인 스킬 미동기화 · import 직후 publish 409 · `pac copilot status` 오류 · Azure CLI Graph 토큰에 Teams 카탈로그 범위 없음 · 선언형 에이전트 시작 문구 줄바꿈 스키마 오류 · PAYG 정책 이름 규칙 · Power Fx 정규식 백슬래시 이중 이스케이프 · 하네스·모델별 주입 입력 반응 차이.

## 4. 미실행·미검증 (정직한 목록)

`wiqd`(Node ≥ 24.15·TTY 로그인 필요)·`atk` 경유 배포 · GitHub Copilot CLI + `mcs-assistant` 플러그인 *대화형* 작성(격리된 `COPILOT_HOME` 에 설치만 검증: 8 skills) · MCP/A2A **클라이언트 채널**(early release 환경 한정) · 평가(Evaluate) REST API · `WorkflowTool`/hooks/memory/connected agents · PAYG **환경 링크** · 선언형 에이전트 knowledge(capabilities) 런타임 · `authMode: Invoker` MCP 도구 · 선언형 에이전트의 SDK/REST 대화(경로 없음 → UI 로 확인).

## 5. 테넌트·구독·로컬에 남긴 것 (정리: `scripts/99-cleanup.sh`)

| 위치 | 객체 |
| --- | --- |
| Copilot Studio / Dataverse (Caldova default) | 에이전트 `hlab_IssueTriageStandard` · `hlab_IssueTriageStdGen` · `hlab_IssueTriageGitHub` · `hlab_IssueTriageMCP`, 같은 이름의 unmanaged solution(+`HarnessLabStandard`), publisher `hlab`, 커스텀 커넥터 `Issue Triage MCP` + 연결 + 연결 참조 |
| Entra | 앱 등록 `csharness-lab-sdk-client`(`8508c3d0-158f-47e9-a665-2f3ccb3c55f5`, 공용 클라이언트, `CopilotStudio.Copilots.Invoke`·`AppCatalog.ReadWrite.All`·`TeamsAppInstallation.ReadWriteForUser`·`User.Read`) |
| Microsoft 365 | Teams 앱 `Issue Triage Copilot`(카탈로그 `7013dd3d-…`, 조직 배포, 관리자에게 설치) |
| Azure `e56daab3-…` | RG `rg-csharness-lab`(ACR·Container Apps 환경·앱 `ca-csharness-mcp`, 태그 `deleteAfter=2026-10-24`) · 리소스 공급자 `Microsoft.PowerPlatform` 등록 · (PAYG 정책은 생성 후 삭제) |
| 로컬 | `pac` 전역 도구 2.10.1→2.13.1 · `~/.scout/caldova/`(격리 `az` 구성·MSAL 토큰 캐시·임시 실험 작업 폴더·`@microsoft/wiqd` 로컬 설치) · Scout 브라우저 프로필에 Caldova 관리자 세션 |

> 기존 Caldova 데모 에이전트(`cra4a_*` 13개 등)는 **조회만** 했고 수정하지 않았습니다.

## 6. 독립 검토

완성한 가이드·스크립트를 **읽기 전용 서브 에이전트**가 별도로 검토했습니다(`bash -n` 23개 스크립트 통과, 27개 `.py` 컴파일 통과, 공통 분류기 5/5, 증거 JSON 대조). 지적된 사항 — 작업 디렉터리/환경 변수 함정, `run_local.sh` 포그라운드 실행, 손으로 고친 콘솔 출력, 튜닝 경위 서술, "글자 하나까지 같다"는 과장, 수동 절차와 스크립트의 차이, 권한 사전 조건 누락, 표 안의 `|` 등 — 를 가이드·스크립트에 반영했고, 이 보고서의 증빙 인용(`run-log.md`, 스크린샷 이름)도 고쳤습니다.
