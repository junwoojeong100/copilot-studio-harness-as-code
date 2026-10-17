# 검증 요약 (2026-10-17 14:33 KST)

| target | 하네스 | 통과 | 평균 응답(s) |
| --- | --- | --- | --- |
| standard-classic | Standard / classic | 5/5 | 4.3 |
| standard-generative | Standard / generative | 5/5* | 4.3 |
| github | GitHub Copilot | 5/5 | 10.1 |
| github-mcp | GitHub Copilot + MCP 도구 | 5/5 | 9.6 |

`*` = 프롬프트 주입 케이스를 모델/플랫폼이 안전하게 거절·차단 (합격으로 계산)
Copilot chat harness 는 SDK 대화가 없어 UI 로 확인: evidence/copilot-chat-ui-run1.json
