# Copilot Studio 하네스 코드 실습 (Caldova)

Copilot Studio 의 **세 가지 하네스(Standard · GitHub Copilot · Copilot chat)** 로 같은 GitHub 이슈 분류 에이전트를 **포털 클릭 없이 코드만으로** 만들고, Microsoft 365 Agents SDK 테스트 하네스로 같은 5개 케이스를 검증하는 실습입니다. 모든 단계는 `caldova10993123.onmicrosoft.com` / **Caldova (default)** 환경 / Azure 구독 `e56daab3-…` 에서 2026-10-17 에 실제로 실행했습니다.

* **본문**: [`GUIDE.ko.md`](GUIDE.ko.md) (또는 단일 파일 [`GUIDE.ko.html`](GUIDE.ko.html))
* **검증 기록**: [`VERIFICATION_REPORT.md`](VERIFICATION_REPORT.md), `evidence/`

## 결과 한눈에

| 하네스 · 옵션 | 코드 | 호출/확인 | 결과 |
| --- | --- | --- | --- |
| Standard · classic (토픽+Power Fx) | `pac copilot init/push/pack` + `solution import` | Agents SDK | **5/5** (모든 필드 값이 참조 구현과 동일) |
| Standard · generative (지침) | `agent.mcs.yml` + `push` | Agents SDK | 5/5* |
| GitHub Copilot · 지침+지식+스킬(샌드박스 Python) | `init --authoring-mode cli-copilot` + `add-skill.js` | Agents SDK(agentic 3p) | **5/5** · 모델 4종 비교 |
| GitHub Copilot · **MCP 도구**(Azure Container Apps) | 커넥터+연결+`McpTool` YAML, Bicep | Agents SDK | **5/5** (서버 로그로 호출 확인) |
| Copilot chat · 선언형 에이전트 | 앱 패키지(JSON) + Graph 앱 카탈로그 | M365 Copilot UI | 5/5* |
| ALM | `solution export/import`, `clone`, `pack` | 삭제→복원→재검증 | ✅ |
| Azure 과금 | PAYG 정책 API (생성→조회→삭제) | REST | ✅ (환경 링크는 과금 영향으로 미실행) |

`*` = 프롬프트 주입 케이스를 모델/플랫폼이 안전하게 거절·차단한 것을 합격으로 계산.

## 빠른 시작

```bash
cp lab.env.example lab.env && python3 -m venv .venv && .venv/bin/pip install -r harness/requirements.txt
az login --tenant <tenantId> --use-device-code --allow-no-subscriptions && pac auth create --name caldova --deviceCode
./scripts/00-preflight.sh          # 도구·로그인·환경·라이선스 점검 (읽기 전용)
./scripts/01-entra-app.sh          # SDK/Graph 용 Entra 공용 클라이언트 앱 (CSLAB_CLIENT_ID 기록)
./scripts/10-standard-classic.sh   # Lab 1  Standard classic
./scripts/11-standard-generative.sh
./scripts/20-github.sh             # Lab 2  GitHub Copilot harness (+ 21-github-models.sh 모델 비교)
./scripts/30-copilot-chat.sh       # Lab 3  Copilot chat harness (선언형 에이전트)
(cd labs/04-azure-mcp && ./scripts/deploy.sh && cd copilot-studio && ./scripts/setup_all.sh)   # Lab 4  Azure + MCP
./scripts/50-alm.sh                # Lab 5  수명주기
./scripts/90-verify-all.sh         # 전체 검증 → evidence/summary.md
./scripts/99-cleanup.sh --all --yes
```

## 주의

* 이 환경(Caldova default)에는 **다른 데모 에이전트(`cra4a_*`, managed)** 가 있습니다. 실습 스크립트는 `hlab_` 접두사 객체만 만들고 지웁니다.
* GitHub Copilot harness 는 만들기·테스트에도 **Copilot Credits** 를 소모합니다. Azure ACR+Container Apps 는 합계 하루 약 US$0.3~0.4(추정)입니다. 끝나면 `99-cleanup.sh` 로 정리하세요.
* `lab.env`, `labs/04-azure-mcp/.env.local`(API 키), `.venv`, `workspaces/`, `.cache/` 는 `.gitignore` 대상이며 커밋하지 마세요.
