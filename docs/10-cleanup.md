# 10. 정리

실습 리소스는 모두 이름/태그로 식별되며 한 번에 삭제됩니다. **Caldova 의 기존 에이전트(`cra4a_*`, managed)는 건드리지 않습니다.**

```bash
./scripts/99-cleanup.sh --mcp    --yes    # Lab 4: 커스텀 커넥터·연결·연결 참조·MCP 에이전트 (--agents 보다 먼저)
./scripts/99-cleanup.sh --agents --yes    # Copilot Studio 에이전트 hlab_IssueTriage* + solution + 로컬 workspaces
./scripts/99-cleanup.sh --m365   --yes    # Teams 카탈로그의 선언형 에이전트
./scripts/99-cleanup.sh --azure  --yes    # 리소스 그룹 rg-csharness-lab (ACA·ACR·환경, 비동기)
./scripts/99-cleanup.sh --entra  --yes    # Entra 앱 등록 csharness-lab-sdk-client
# 한 번에: ./scripts/99-cleanup.sh --all --yes
```

추가로 확인할 것:

* Lab 4 의 로컬 작업 폴더: `rm -rf ~/.cs-harness-lab/hlab_IssueTriageMCP` (스크립트가 `--mcp` 에서 함께 삭제)
* 토큰 캐시: `rm -f ~/.cache/csharness-lab/msal_cache.json` (또는 `CSLAB_MSAL_CACHE` 경로)
* `pac auth delete --name caldova`, `az logout` (실습 전용 `AZURE_CONFIG_DIR` 이라면 디렉터리 삭제)
* Azure 비용: ACR+Container Apps(최소 1 replica)는 합계 하루 약 US$0.3~0.4(추정). 리소스에는 `purpose=copilot-studio-harness-lab`, `deleteAfter=2026-10-24` 태그가 붙어 있습니다.
