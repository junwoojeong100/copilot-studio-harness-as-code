# 8. 비교 결과

같은 5개 케이스·같은 JSON 계약으로 각 하네스를 호출한 결과입니다 (2026-10-17, Caldova default. Copilot chat 행만 UI 수동 확인이고 나머지는 스크립트로 재현).

| 대상 | 하네스 / 옵션 | 통과 | 평균 응답 | 결정론 | `prompt-injection` |
| --- | --- | --- | --- | --- | --- |
| `standard-classic` | Standard · classic (Power Fx) | **5/5** | 4.3 s | ✅ 항상 같은 출력 | 규칙으로 분류(`needs-triage`) |
| `standard-generative` | Standard · generative (GPT5Chat) | 5/5* | 4.3 s | ❌ 지침 의존(튜닝 필요) | `ContentFiltered` 차단 |
| `github` (Sonnet 4.6) | GitHub Copilot · 지침+지식+스킬 | **5/5** | 10.1 s | △ 스킬 스크립트로 값 고정 가능 | 분류(`needs-triage`) |
| `github` (Opus 4.7) | 〃 | 5/5 | 10.4 s | △ | 분류 |
| `github` (GPT-5.5 / GPT-5 Chat) | 〃 | 5/5* | 6.5 s / 5.0 s | △ | 거절 / `OpenAIJailBreak` |
| `github-mcp` | GitHub Copilot · **MCP 도구**(Azure) | **5/5** | 9.6 s | ✅ 도구가 계산 | 서버가 분류(`needs-triage`) |
| Copilot chat (UI) | 선언형 에이전트(M365 Copilot) | 5/5* | — (UI 수동, 미측정) | △ | "can't chat about this" 차단 |

`*` = 주입 케이스를 안전하게 거절/차단한 것을 합격으로 계산. 응답 시간은 최종 `90-verify-all.sh`(`evidence/summary.md`) 기준이며 실행마다 ±수 초(GitHub 는 최대 ±10초) 변동합니다 — 모델 4종 비교(4.5절)는 별도 실행입니다.

## 8.1 무엇을 언제 고르나 (이번 결과 기준)

| 요구 | 선택 | 근거 |
| --- | --- | --- |
| 같은 입력 → **같은 출력**, 감사·재현성, 저지연·저비용 | Standard classic | 5/5, 모든 필드 값이 참조 구현과 일치, 호출당 모델 비용 없음 |
| 자유 문장 입력, 문맥 판단, 빠른 구현 | Standard generative 또는 GitHub harness | 지침만으로 4~5/5 |
| 스크립트 실행·파일 생성·다단계 도구 호출·장기 작업 | **GitHub Copilot harness** | 샌드박스 Bash, skills, 도구, 모델 선택. 단순 분류에는 과한 지연(6~20 s) |
| 결정론 + 에이전트 문맥 이해 | GitHub harness + **MCP/스킬 스크립트**로 계산 위임 | 분류는 도구가 확정, 대화는 모델이 담당 |
| M365 Copilot 사용자에게 *지식 기반* 도우미 제공 | Copilot chat harness | 설정(JSON)만으로 배포, 플랫폼 보호(주입 차단) 기본 제공 |

## 8.2 관찰한 차이

* **안전장치가 계층마다 다르다**: Standard generative(GPT5Chat)는 플랫폼이 `ContentFiltered` 로 **입력 단계에서** 차단, GPT 계열 GitHub 에이전트는 `OpenAIJailBreak`/거절, Claude 계열은 분류해서 답, M365 Copilot 은 "can't chat about this". **하네스·모델에 따라 "구조화된 응답이 오지 않을 수 있다"는 전제로 클라이언트를 짜야 합니다.**
* **응답 시간**: classic ≈ generative ≈ 4~5 s < MCP 도구 ≈ 9~10 s ≈ GitHub(스킬+Bash) 6~20 s (첫 호출은 스킬 로딩으로 더 느림). agentic loop 는 스킬 로딩·샌드박스 실행이 더해집니다.
* **저작 방식**: classic 은 *흐름을 직접 작성*, generative/GitHub 는 *지침·지식·도구를 작성하고 테스트로 검증*. 후자는 **테스트 하네스가 사실상 소스 코드의 일부**입니다.
* **동기화**: classic 의 봇 설정은 solution 경로, CLI(GitHub) 에이전트는 push 로 설정까지 반영.
