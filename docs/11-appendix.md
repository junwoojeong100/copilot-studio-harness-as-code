# 부록

## A. 저장소 구조

```text
CopilotStudio_Harness_CodeLab/
├── README.md · GUIDE.ko.md · GUIDE.ko.html · VERIFICATION_REPORT.md
├── lab.env.example            # lab.env 로 복사 (lab.env 는 git 제외)
├── shared/                    # 모든 하네스가 공유: label-policy(.yaml/.md) · test-cases.yaml · classify_issue.py · triage-instructions.md
├── harness/                   # Agents SDK 테스트 하네스 (run_cases.py · chat.py · csharness/)
├── labs/
│   ├── 01-standard/overlay/classic/topics/ClassifyIssue.mcs.yml
│   ├── 02-github-copilot/skill-src/issue-triage-script/{SKILL.md, scripts/}
│   ├── 03-copilot-chat/{build_package.py, validate_package.py, m365_publish.py, appPackage/}
│   └── 04-azure-mcp/{server, infra, scripts, connector, copilot-studio/}
├── scripts/                   # 00-preflight · 01-entra-app · 10/11 standard · 20/21 github · 30 copilot-chat · 50-alm · 90-verify-all · 99-cleanup
├── docs/                      # 가이드 원문(장별) — GUIDE.ko.md 는 scripts/build_guide.py 가 병합
└── evidence/                  # 실제 실행 결과(JSON·PNG·summary.md)
```

## B. 명령 치트시트

| 하고 싶은 것 | 명령 |
| --- | --- |
| 에이전트 생성 (Standard) | `pac copilot init --name … --environment <url> --project-dir <dir> --publisher-prefix hlab --template minimal` |
| 에이전트 생성 (GitHub harness) | 위에 `--authoring-mode cli-copilot` (템플릿 옵션 대신) |
| 안전한 동기화 | `pac copilot pull` → `pac copilot push` → `pac copilot publish --bot <schema> --environment <url>` → `pac copilot pull` |
| 봇 수준 설정 반영 (classic) | `pac copilot pack …` → `pac solution import … --force-overwrite --publish-changes` |
| 목록·삭제·복제 | `pac copilot list` / `delete --bot … --confirm` / `clone --bot … --output-dir …` |
| solution 이동 | `pac solution export --name … --managed true`(또는 `false`) / `pac solution import --path …` |
| 스킬 추가 | `node copilot-studio-plugin/scripts/add-skill.js import --src <dir> --workspace <agentDir> --name <folder>` |
| 대화 테스트 | `harness/run_cases.py --target <대상>` (대상: standard-classic · standard-generative · github · github-mcp) |
| 선언형 에이전트 | `build_package.py` → `validate_package.py` → `m365_publish.py [--uninstall]` |
| 상태 조회 (읽기 전용) | Dataverse `bots`, `botcomponents`; BAP `…/scopes/admin/environments/<id>`; Power Platform API `licensing/billingPolicies` |
| 로그인 확인 | `pac auth list` · `pac env who` · `az account show` |

## C. 참고 문서

* [Harnesses in Copilot Studio](https://learn.microsoft.com/microsoft-copilot-studio/harnesses-overview) · [Compare harnesses](https://learn.microsoft.com/microsoft-copilot-studio/guidance/choose-harness) · [Agents overview](https://learn.microsoft.com/microsoft-copilot-studio/agents-overview)
* GitHub Copilot harness: [overview](https://learn.microsoft.com/microsoft-copilot-studio/agents-experience/overview) · [skills](https://learn.microsoft.com/microsoft-copilot-studio/agents-experience/skills-overview) · [MCP 서버 추가](https://learn.microsoft.com/microsoft-copilot-studio/agents-experience/tools-add-mcp-server) · [MCP·A2A 채널(프리뷰)](https://learn.microsoft.com/microsoft-copilot-studio/agents-experience/publication-channels-mcp-agent-to-agent) · [Copilot Credits 과금](https://learn.microsoft.com/microsoft-copilot-studio/agents-experience/billing-credit-overview)
* Standard harness: [VS Code 확장](https://learn.microsoft.com/microsoft-copilot-studio/visual-studio-code-extension-overview) · [Agents SDK 연동](https://learn.microsoft.com/microsoft-copilot-studio/publication-integrate-web-or-native-app-m365-agents-sdk)
* Copilot chat harness: [Extend Microsoft Copilot](https://learn.microsoft.com/microsoft-copilot-studio/microsoft-365-copilot-extend-with-agents) · [선언형 에이전트](https://learn.microsoft.com/microsoft-365/copilot/extensibility/overview-declarative-agent) · [Work IQ Dev Tools](https://microsoft.github.io/wiqd/)
* 과금 API: [Create billing policy](https://learn.microsoft.com/rest/api/power-platform/licensing/billing-policy/create-billing-policy) · [Add environment](https://learn.microsoft.com/rest/api/power-platform/licensing/billing-policy-environment/add-billing-policy-environment) · [PAYG 설정](https://learn.microsoft.com/power-platform/admin/pay-as-you-go-set-up)
* 저장소: [microsoft/vscode-copilotstudio](https://github.com/microsoft/vscode-copilotstudio) · [microsoft/copilot-studio-plugin](https://github.com/microsoft/copilot-studio-plugin)(커밋 `4014ae6`) · [microsoft/skills-for-copilot-studio](https://github.com/microsoft/skills-for-copilot-studio)(Standard 용) · [microsoft/wiqd](https://github.com/microsoft/wiqd)

## D. 범위와 한계 (정직한 메모)

* **한 테넌트·한 환경(Caldova default, Canada East)** 에서 2026-10-17 에 검증했습니다. 다른 테넌트의 DLP·조건부 액세스·라이선스에 따라 결과가 다를 수 있습니다(8월 포털 실습에서는 조직 DLP 가 `PvaSkills` 커넥터를 막아 Standard 게시가 막혔고 `pac` 로그인도 준수 디바이스가 필요했습니다. Caldova 는 DLP 0개).
* GitHub Copilot harness 는 **프리뷰/신규 런타임**입니다 — `pac copilot` 의 YAML 스키마·`agenticruntime/3p` 엔드포인트·플러그인(WIP)이 예고 없이 바뀔 수 있습니다.
* LLM 기반 대상은 비결정적입니다. 이 문서의 5/5 는 *해당 실행의 결과*이며 재실행하면 달라질 수 있습니다(지침 튜닝 사례 참고).
* **미실행**: `wiqd`/`atk` 경유 배포, GitHub Copilot CLI 플러그인을 통한 *대화형* 작성(설치만 검증), MCP/A2A 클라이언트 채널, 평가(Evaluate) REST API, `WorkflowTool`·hooks·memory·connected agents, PAYG 환경 링크, 선언형 에이전트의 지식(capabilities) 런타임, `authMode: Invoker` MCP 도구.
* 선언형 에이전트 런타임 대화는 API 가 없어 **UI(Playwright)** 로 확인했습니다.
