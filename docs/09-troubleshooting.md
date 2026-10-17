# 9. 트러블슈팅 — 검증 중 실제로 만난 문제

| # | 증상 / 메시지 | 원인 | 해결 |
| --- | --- | --- | --- |
| 1 | `pac copilot pull` → `System.FormatException: The input string '1033>>>>>>> '…` | pac **2.10.1** 이 3-way 병합 충돌 마커를 파싱하다 종료 | `dotnet tool update -g Microsoft.PowerApps.CLI.Tool` (2.13.1 확인) |
| 2 | `pac` 실행 시 "You must install .NET to run this application" | Homebrew dotnet 의 `DOTNET_ROOT` 미설정 | `export DOTNET_ROOT="$(brew --prefix dotnet)/libexec"` |
| 3 | 디바이스 코드를 입력했는데 CLI 가 끝나지 않음 | 서로 다른 브라우저 세션/계정으로 입력, 또는 코드 만료(15분) | 새 코드 발급 후 *계정 선택 → Continue → "You have signed in…"* 까지 확인 |
| 4 | classic 에이전트가 모든 입력을 `question` 으로 분류, 정규식이 안 맞음 | YAML/Power Fx 문자열에서 `\\b`, `\\?` 처럼 백슬래시를 **두 번** 씀 | `\b`, `\?` 로 한 번만 |
| 5 | `settings.mcs.yml` 의 `GenerativeActionsEnabled: false` 가 반영 안 됨, pull 하면 `true` 로 복귀 | classic 의 봇 수준 설정은 `push` 대상이 아님 | `pac copilot pack` + `pac solution import`, 확인은 Dataverse `bots?$select=configuration` |
| 6 | `pull` → `InvalidOperationException: Component is missing Id: …topic.ClassifyIssue` | 새 토픽을 **push 하지 않고** pack/import | push 로 먼저 등록, 이후 pack/import |
| 7 | `push` → "The agent was changed in the cloud while you were editing it" | import/게시 등으로 클라우드가 바뀜 | `pull` 후 `push` |
| 8 | `pull` 후 `settings.mcs.yml` 끝에 `<<<<<<<` … `publishedOn:` 충돌 마커, "Unresolved merge conflict" | publish 가 `publishedOn:` 을 추가했는데 로컬을 수정한 채 pull | 마커만 제거(`publishedOn` 줄 유지) → `pull` → `push`. 예방: publish 직후 pull |
| 9 | `push` → "Remote changes conflict with local changes. Run 'pac copilot pull' first" | 8번 충돌 미해결 상태 | 충돌 해소 후 pull |
| 10 | 인라인 SKILL(`behaviors/x/x.mcs.yml`)이 **No local changes detected** | CLI 에이전트는 `SKILL.md` + `skill.mcs.yml` 업로드 레이아웃만 동기화 | `add-skill.js import` 로 생성 |
| 11 | import 직후 `publish` → `409 Conflict … ExternalServiceException` | 에이전트 프로비저닝 미완료 | 20초 후 재시도(최대 6회) |
| 12 | `pac copilot status` → `componentstate_Property` 오류 | 2.13.1 의 알려진 문제 | `pac copilot list`, Dataverse `bots` 조회 |
| 13 | Graph `POST /appCatalogs/teamsApps` → 403 (Azure CLI 토큰) | az 토큰 범위에 `AppCatalog.*` 없음 | 전용 앱 등록 + `AppCatalog.ReadWrite.All` 동의 후 디바이스 코드 |
| 14 | `urllib.error` / `InvalidURL: URL can't contain control characters` | OData `$filter` 의 공백 미인코딩 | `urllib.parse.quote(...)` |
| 15 | `declarativeAgent.json` 스키마 오류: `conversation_starters/0/text` | 시작 문구에 줄바꿈 | 한 줄로 |
| 16 | 선언형 에이전트 재배포 `409` | 같은 `version` | 매니페스트 `version` 올리기, 설치 409 는 정상 |
| 17 | 주입 케이스에서 JSON 이 안 옴 (`ContentFiltered`/`OpenAIJailBreak`/"cannot assist") | 플랫폼·모델의 안전장치 | 정상 동작. 테스트는 "안전한 거절"을 합격으로 정의 |
| 18 | PAYG 정책 생성 `BillingDocumentNameInvalid` | 이름은 **영문·숫자 10~64자** | `CsharnessLabPayg01` |
| 19 | `npm`/NuGet 직접 접근 불가(사내망) | 내부 패키지 피드 프록시 | 설정된 피드로 설치(`npm view`/`dotnet tool update` 가 프록시 경유) |

> 모든 `pac` 오류 상세는 `…/microsoft.powerapps.cli.tool/<버전>/tools/net10.0/any/logs/pac-log.txt` 에 스택과 함께 남습니다.
