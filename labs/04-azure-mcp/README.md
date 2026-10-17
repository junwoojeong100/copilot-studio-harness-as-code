# Lab 04 — Azure Container Apps에 MCP 서버 배포하기 (GitHub 이슈 triage)

> **소요 시간** 약 30분 (배포 대기 약 5분 포함) · **비용** 켜 둔 상태로 하루 약 US$0.3 (추정, [비용 안내](#10-비용-안내) 참고) · **끝나면 반드시** [정리](#9-정리-cleanup)

## 0. 이 랩에서 하는 일

시나리오는 **GitHub 이슈 triage** 입니다. 이미 있는 결정론적 분류기(`shared/classify_issue.py`)를 **MCP 서버**로 감싸서 Azure Container Apps(ACA)에 올리고, **진짜 MCP 클라이언트**(`mcp` Python SDK)와 `curl` 로 검증합니다. 다음 랩에서 Copilot Studio 에이전트가 이 서버를 *커스텀 커넥터(MCP)* 로 호출합니다.

```text
Copilot Studio 에이전트 ──HTTPS + x-api-key──▶  Azure Container Apps  (ca-csharness-mcp, 외부 ingress :443 → 컨테이너 :8000)
 (커스텀 커넥터, MCP)                              └─ server.py  (FastMCP · stateless · JSON 응답 · POST /mcp · GET /healthz)
                                                       └─ classify_issue.py (= ../../shared 의 파일을 빌드 때 복사)
Azure Container Registry (Basic) ──AcrPull(시스템 할당 관리 ID)──▶ Container App   (레지스트리 암호 없음)
```

| 도구(tool) | 하는 일 |
| --- | --- |
| `classify_issue(issue_title, issue_body)` | 이슈 1건을 `{category, priority, team, summary, needsHumanReview}` 로 분류 (읽기 전용) |
| `get_label_policy()` | `label-policy.yaml` 내용(라벨 매핑, 승인이 필요한 결과, 가드레일) 반환 (읽기 전용) |

> 검증 환경(2026-10-17): Azure CLI 2.86.0, Bicep 0.48.1, Python 3.12.15(venv), `mcp==1.30.0`, 컨테이너 `python:3.12-slim`, 리전 `koreacentral`.

## 1. 사전 준비

| 항목 | 설명 |
| --- | --- |
| Azure 구독 | 리소스 그룹 생성 + **역할 할당(AcrPull)** 권한 필요 → 구독/리소스 그룹에 `Owner` (또는 `Contributor` + `User Access Administrator`) |
| Azure CLI | `az login` 후 `az account set -s <구독 ID>` |
| Python | 3.10 이상 필요(mcp 1.x 요구사항). 이 랩은 **3.12**로 검증 |
| 기타 | `bash`, `curl`, `openssl` (macOS / Linux / WSL / Git Bash) |
| Docker | **필요 없음** — 이미지는 `az acr build` 로 Azure에서 원격 빌드 |

```bash
az login
az account set -s "<구독 ID>"
az account show --query "{name:name, id:id, tenant:tenantId}" -o table   # 맞는 구독인지 꼭 확인
```

> 이 문서의 모든 `az` 명령은 위 로그인 상태를 그대로 사용합니다. (검증 때는 별도 `AZURE_CONFIG_DIR` 로 격리된 로그인을 썼을 뿐 명령은 동일합니다.)

## 2. 폴더 구조

```text
labs/04-azure-mcp/
├─ server/            server.py · requirements.txt · Dockerfile  (classify_issue.py / label-policy.yaml 은 빌드 때 ../../shared 에서 복사 — git 제외)
├─ infra/             main.bicep · main.bicepparam
├─ scripts/           run_local.sh · deploy.sh · test_mcp.py · render_connector.py · cleanup.sh (+ _common.sh · sync_shared.sh)
├─ connector/         apiDefinition.swagger.json · apiProperties.json · README.md   (다음 랩용)
├─ .env.local         API_KEY / MCP_ENDPOINT  (자동 생성, chmod 600, git 제외 — 절대 공유 금지)
└─ README.md · EVIDENCE.md
```

## 3. 로컬에서 먼저 실행하고 테스트하기 (Azure 불필요)

**터미널 1** — 서버 실행. 첫 실행 때 `.venv` 생성, 의존성 설치, `.env.local` 에 API 키 생성(`openssl rand -hex 24`, 화면에 출력되지 않음)까지 해 줍니다.

```bash
cd CopilotStudio_Harness_CodeLab/labs/04-azure-mcp
PYTHON=python3.12 ./scripts/run_local.sh       # python3.12 가 없으면 PYTHON=python3
```

```text
[sync] shared/classify_issue.py + shared/label-policy.yaml -> server/
[key] generated a new API key in .env.local (chmod 600, not printed)
[run] serving http://127.0.0.1:8000/mcp  (health: /healthz, Ctrl+C to stop)
```

**터미널 2** — 실제 MCP 클라이언트로 테스트 (`initialize` → `list_tools` → 5개 케이스 → `get_label_policy` → 인증 검사).

```bash
cd CopilotStudio_Harness_CodeLab/labs/04-azure-mcp
.venv/bin/python scripts/test_mcp.py --url http://127.0.0.1:8000/mcp
```

```text
endpoint: http://127.0.0.1:8000/mcp
[PASS] GET /healthz without key -> 200 'ok'  (HTTP 200)
[PASS] POST /mcp WITHOUT x-api-key -> 401 JSON  (HTTP 401)
[PASS] POST /mcp with WRONG x-api-key -> 401  (HTTP 401)
[PASS] raw JSON-RPC initialize with key -> 200 application/json, stateless (no mcp-session-id)  (HTTP 200)
[PASS] GET /mcp with key -> 405 (no standalone SSE stream)  (HTTP 405)
[PASS] MCP initialize  (server=issue-triage 1.30.0, protocol=2025-11-25)
[PASS] list_tools -> classify_issue + get_label_policy  (['classify_issue', 'get_label_policy'])
...
[PASS] case production-outage  (bug/P0/backend/review=True)
[PASS] case docs-typo  (documentation/P3/docs/review=False)
[PASS] case possible-secret-exposure  (security/P1/security/review=True)
[PASS] case prompt-injection  (security/P3/needs-triage/review=True)
[PASS] case ambiguous-request  (bug/P3/needs-triage/review=True)
[PASS] get_label_policy == shared/label-policy.yaml  (version=1, keys=['guardrails', 'priorities', 'teams', 'types', 'version'])
[PASS] classify_issue without arguments -> tool error (not a crash)

16/16 checks passed
```

테스트가 끝났으면 터미널 1에서 `Ctrl+C` 로 서버를 끕니다. (포트 8000이 사용 중이면 `PORT=8001 ./scripts/run_local.sh` 후 `--url http://127.0.0.1:8001/mcp`.)

## 4. Azure에 배포하기

### 4-1. (선택) Bicep 검증과 what-if

```bash
az bicep build --file infra/main.bicep --stdout > /dev/null && echo "bicep OK"   # 컴파일/린트 (출력 없으면 경고 없음)
./scripts/deploy.sh --what-if                                                   # 리소스 그룹만 만들고 변경 사항 미리보기
```

```text
Resource changes: 4 to create.        # ACR, 컨테이너 앱 환경, 컨테이너 앱, AcrPull 역할 할당
```

### 4-2. 배포

```bash
./scripts/deploy.sh
```

스크립트는 **여러 번 실행해도 안전(멱등)** 합니다. 진행 로그는 stderr, **마지막 줄(stdout)에 엔드포인트만** 출력합니다. API 키는 출력하지 않습니다.

```text
[az] subscription: <구독 이름> (<구독 ID>)
[key] generated a new API key in .env.local (chmod 600, not printed)
[rg] creating rg-csharness-lab in koreacentral
[bicep] phase 1/2: ACR + environment + app (placeholder image) ...
[bicep] registry: acrcsharnessppvfngmzdhct2 / app: ca-csharness-mcp
[acr] az acr build -> acrcsharnessppvfngmzdhct2/csharness-mcp:d3f8a6bfcb69 (remote build, no local Docker)
...                                                  (원격 빌드 로그 생략)
Run ID: de1 was successful after 35s
[bicep] phase 2/2: app -> csharness-mcp:d3f8a6bfcb69
[wait] provisioning=Succeeded latest=ca-csharness-mcp--0000001 ready=ca-csharness-mcp--ii8txnf healthz=<none>
[wait] provisioning=Succeeded latest=ca-csharness-mcp--0000001 ready=ca-csharness-mcp--0000001 healthz=ok
[done] revision ca-csharness-mcp--0000001 is healthy. Endpoint saved to .env.local (MCP_ENDPOINT); API key stays in .env.local.
https://<앱>.<환경ID>.koreacentral.azurecontainerapps.io/mcp
```

약 5분 걸렸습니다(1단계 약 3분 40초, 원격 빌드 35초, 2단계 + 헬스 대기 약 1분). 만들어지는 리소스:

```bash
az resource list -g rg-csharness-lab -o table
```

```text
Name                       ResourceGroup     Location      Type                                    Status
-------------------------  ----------------  ------------  --------------------------------------  ---------
acrcsharnessppvfngmzdhct2  rg-csharness-lab  koreacentral  Microsoft.ContainerRegistry/registries  Succeeded
cae-csharness              rg-csharness-lab  koreacentral  Microsoft.App/managedEnvironments       Succeeded
ca-csharness-mcp           rg-csharness-lab  koreacentral  Microsoft.App/containerApps             Succeeded
```

> **왜 2단계(phase)로 배포하나요?** 관리 ID(시스템 할당)는 앱이 만들어진 *뒤에* 생기므로 AcrPull 역할도 그 뒤에야 줄 수 있고, 앱은 그 역할이 있어야 ACR에서 이미지를 받을 수 있습니다(닭과 달걀). 그래서 ① 공개 placeholder 이미지로 앱+ID+AcrPull을 먼저 만들고 → ② `az acr build` → ③ 같은 Bicep을 이미지 태그와 함께 다시 적용해 앱을 실제 이미지로 전환합니다. 레지스트리 관리자 계정/암호는 쓰지 않습니다.
> 이미지 태그는 소스 해시(`d3f8a6bfcb69`)라서 소스가 같으면 빌드를 건너뜁니다.

## 5. 공개 엔드포인트 검증

### 5-1. 실제 MCP 클라이언트 (Python)

```bash
.venv/bin/python scripts/test_mcp.py          # .env.local 의 MCP_ENDPOINT / API_KEY 사용
```

로컬과 같은 `16/16 checks passed` (종료 코드 0)가 나와야 합니다. 5개 케이스는 `shared/test-cases.yaml` 의 `expected` 와 비교하며(`priorityAnyOf` 포함), 금지 문구(`forbiddenPhrases`)와 기준 분류기 결과와의 일치도 확인합니다.

### 5-2. Python 없이 `curl` 만으로

```bash
cd CopilotStudio_Harness_CodeLab/labs/04-azure-mcp
set -a; source .env.local; set +a                       # API_KEY, MCP_ENDPOINT 를 셸에 로드 (echo 하지 마세요)
HDR=(-H "Content-Type: application/json" -H "Accept: application/json, text/event-stream")

# 0) 헬스 체크 — 키 불필요
curl -sS "${MCP_ENDPOINT%/mcp}/healthz"; echo                                     # ok

# 1) 키 없이 호출 → 401
curl -sS -i -X POST "$MCP_ENDPOINT" "${HDR[@]}" -d '{"jsonrpc":"2.0","id":1,"method":"tools/list"}' | sed -n '1p;$p'; echo
#   HTTP/2 401
#   {"error":"unauthorized","message":"Missing or invalid x-api-key header."}

# 2) initialize
curl -sS "$MCP_ENDPOINT" -H "x-api-key: $API_KEY" "${HDR[@]}" \
  -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-03-26","capabilities":{},"clientInfo":{"name":"curl","version":"0"}}}' | python3 -m json.tool

# 3) initialized 알림 → 202 (본문 없음)
curl -sS -o /dev/null -w "HTTP %{http_code}\n" "$MCP_ENDPOINT" -H "x-api-key: $API_KEY" "${HDR[@]}" \
  -d '{"jsonrpc":"2.0","method":"notifications/initialized"}'

# 4) tools/list
curl -sS "$MCP_ENDPOINT" -H "x-api-key: $API_KEY" "${HDR[@]}" \
  -d '{"jsonrpc":"2.0","id":2,"method":"tools/list"}' | python3 -m json.tool

# 5) tools/call — classify_issue
curl -sS "$MCP_ENDPOINT" -H "x-api-key: $API_KEY" "${HDR[@]}" \
  -d '{"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"classify_issue","arguments":{"issue_title":"Production outage: API returns 500 for all requests","issue_body":"Since 09:00 UTC every request to the backend API fails with HTTP 500. Customers cannot check out."}}}' \
  | python3 -c 'import sys,json; print(json.load(sys.stdin)["result"]["content"][0]["text"])'

# 6) tools/call — get_label_policy
curl -sS "$MCP_ENDPOINT" -H "x-api-key: $API_KEY" "${HDR[@]}" \
  -d '{"jsonrpc":"2.0","id":4,"method":"tools/call","params":{"name":"get_label_policy","arguments":{}}}' | python3 -m json.tool | head -n 20
```

5)번 기대 출력:

```json
{
  "category": "bug",
  "priority": "P0",
  "team": "backend",
  "summary": "bug for backend: Production outage: API returns 500 for all requests",
  "needsHumanReview": true
}
```

> 서버가 **stateless** 라서 세션(`mcp-session-id`)이 없고, `initialize` 없이 `tools/list` 만 보내도 동작합니다. 응답은 SSE 스트림이 아닌 일반 `application/json` 입니다.

## 6. Copilot Studio 연결 준비 (다음 랩)

```bash
python3 scripts/render_connector.py            # swagger 의 host 를 MCP_ENDPOINT 와 맞추고 필드 검증 (10개 PASS)
```

`connector/` 에는 `pac connector create --api-definition-file ... --api-properties-file ...` 에 바로 쓸 수 있는 `apiDefinition.swagger.json`(POST `/mcp`, `x-ms-agentic-protocol: mcp-streamable-1.0`, 헤더 `x-api-key`)과 `apiProperties.json` 이 있습니다. 근거 문서와 사용법은 [`connector/README.md`](connector/README.md) 참고. **이 랩에서는 `pac` 를 실행하지 않습니다.**

다음 랩에서 필요한 값: ① MCP URL = `.env.local` 의 `MCP_ENDPOINT` ② API 키 = `.env.local` 의 `API_KEY` (채팅/문서/커밋에 붙여 넣지 마세요).

## 7. 설계 포인트

| 포인트 | 이유 |
| --- | --- |
| `FastMCP(stateless_http=True, json_response=True)`, 경로 `/mcp`, `0.0.0.0:8000` | 세션이 없어서 **레플리카가 2개여도 sticky session 불필요**. 응답이 단순 JSON이라 프록시/커넥터에서 다루기 쉬움 |
| `ApiKeyMiddleware` (순수 ASGI) | `/healthz` 외 **모두 기본 거부**. `hmac.compare_digest` 로 상수 시간 비교, 실패 시 401 JSON. `API_KEY` 가 없거나 16자 미만이면 서버가 **아예 시작하지 않음**(fail closed) |
| `GET /healthz` → `ok` | 인증 없는 프로브용. 컨테이너 앱의 Startup/Liveness/Readiness 프로브가 사용 |
| `GET /mcp` → 405 | 스테이트리스 서버는 서버 시작 SSE 스트림이 없음. 405로 답하지 않으면 연결이 열린 채 멈추고(로컬에서 확인), 열린 요청은 ACA 동시 요청 수에도 잡힐 수 있음 |
| 최소 1 / 최대 2 레플리카, 0.25 vCPU / 0.5 GiB | 콜드 스타트 없이 에이전트 호출에 바로 응답. HTTP 동시 요청 50개 기준 스케일 |
| 외부 ingress + `allowInsecure: false` | HTTPS만 허용 (`http://` 는 301 → `https://`). CORS는 설정하지 않음 — Copilot Studio 커넥터는 서버 측에서 호출하므로 불필요 |
| 로그 분석 작업 영역 없음 | 비용 절감. 실시간 로그는 아래 명령으로 확인 |
| API 키 → ACA **secret** `api-key` → 환경 변수 `API_KEY` (`secretRef`) | 키가 템플릿/명령줄/이미지에 들어가지 않음 (`main.bicepparam` 이 환경 변수에서 읽음) |

```bash
az extension add -n containerapp -y                                              # 처음 한 번
az containerapp logs show -n ca-csharness-mcp -g rg-csharness-lab --type console --tail 20 --format text
```

**API 키 교체**: `.env.local` 에서 `API_KEY=` 줄을 지우고 `./scripts/deploy.sh` 를 다시 실행하면 새 키를 만들어 secret을 갱신합니다. 키의 해시 앞 12자리(`API_KEY_FINGERPRINT`)가 환경 변수에 들어 있어서 **새 리비전이 자동 생성**되고, 새 레플리카가 새 키를 읽습니다(secret만 바꾸면 실행 중인 레플리카는 옛 키를 계속 씁니다). 검증: 교체 후 새 키 200, 옛 키 401.

## 8. 문제 해결

| 증상 | 원인 / 해결 |
| --- | --- |
| `ModuleNotFoundError: mcp.server.fastmcp` | `pip install mcp` 가 **2.x** 를 설치하면 `FastMCP` 모듈이 없습니다(`MCPServer` 로 이름 변경). `server/requirements.txt` 가 `mcp==1.30.0` 으로 고정하고 있으니 그대로 설치하세요 (`pip install -r server/requirements.txt`) |
| `DeprecationWarning: streamablehttp_client` | 1.30에서 클라이언트 함수가 `streamable_http_client(url, http_client=httpx.AsyncClient(headers=...))` 로 바뀌었습니다. `scripts/test_mcp.py` 는 새 함수를 사용 |
| `curl` 이 `406 Not Acceptable` | `Accept: application/json, text/event-stream` 헤더 누락(스펙상 둘 다 보내야 함). `Content-Type: application/json` 도 필요 |
| `curl` 이 `401 unauthorized` | `x-api-key` 헤더가 없거나 값이 다름. `set -a; source .env.local; set +a` 를 다시 실행했는지, 키를 교체한 뒤라면 새 키인지 확인 |
| `GET /mcp` 가 `405` | 정상입니다(스테이트리스 서버). MCP 호출은 항상 **POST** |
| `http://…/mcp` 가 `301` | ACA가 https로 리디렉션합니다. 항상 `https://` URL 사용 |
| `/mcp/` (끝에 슬래시) | 서버가 `/mcp` 로 처리하므로 200 (리디렉션 없음) |
| `deploy.sh` 가 중간에 실패/중단 | 그냥 다시 실행하세요. 이미 있는 리소스·이미지는 건너뜁니다 |
| `Not logged in to Azure` | `az login` 후 `az account set -s <구독 ID>` |
| 역할 할당 권한 오류(`AuthorizationFailed` …/roleAssignments/write) | 구독/리소스 그룹에 `Owner` 또는 `User Access Administrator` 필요 |
| ACR Tasks 차단 구독(`TasksOperationsNotAllowed`) | 일부 구독 유형에서 `az acr build` 가 막힐 수 있다고 알려져 있습니다. 이 랩의 검증 환경에서는 발생하지 않았습니다(미검증) |
| 8000 포트 사용 중 | `PORT=8001 ./scripts/run_local.sh` (검증함) |

## 9. 정리 (Cleanup)

```bash
./scripts/cleanup.sh            # 삭제될 리소스 목록만 보여 주고 종료(코드 2) — 아무것도 삭제하지 않음
./scripts/cleanup.sh --yes      # az group delete -n rg-csharness-lab --yes --no-wait
az group exists -n rg-csharness-lab                                  # false 가 되면 삭제 완료 (수 분 소요)
```

모든 리소스에는 태그 `purpose=copilot-studio-harness-lab`, `deleteAfter=2026-10-24` 가 붙어 있습니다(리소스 그룹에도). `cleanup.sh` 는 이 `purpose` 태그가 없는 리소스 그룹은 삭제를 거부합니다. 로컬 정리: `rm -rf .venv .run .env.local`.

## 10. 비용 안내

공개 [Azure Retail Prices API](https://prices.azure.com/api/retail/prices) 로 조회한 `koreacentral` 소매가(2026-10-17, 추정에 사용):

| 항목 | 단가 | 이 랩 기준 월 추정(30일, 상시 가동) |
| --- | --- | --- |
| ACR **Basic** | US$0.1666 / 일 | 약 US$5.0 (이미지 약 58 MB — Basic 포함 저장 용량 이내로 가정) |
| ACA Consumption vCPU (idle / active) | US$0.000003 / US$0.000024 per 초 | 0.25 vCPU × 2,592,000초 × idle 단가 ≈ US$1.9 (구독당 월 무료 제공량 반영 시 더 낮음) |
| ACA Consumption 메모리 | US$0.000003 per GiB·초 | 0.5 GiB × 2,592,000초 ≈ US$3.9 |
| 요청 | US$0.40 / 100만 건 | 랩 수준에서는 무시 가능 |

→ **켜 두면 하루 약 US$0.3, 한 달 약 US$10 안팎**(추정, 실제 청구는 Cost Management 에서 확인). 최소 레플리카가 1이라 쓰지 않아도 비용이 나가므로 **랩이 끝나면 `cleanup.sh --yes`** 를 실행하세요. Log Analytics 를 쓰지 않아 로그 수집 비용은 없습니다.

## 참고 문서

- [Add an existing MCP server to an agent](https://learn.microsoft.com/en-us/microsoft-copilot-studio/mcp-add-existing-server-to-agent) · [Create a new MCP server](https://learn.microsoft.com/en-us/microsoft-copilot-studio/mcp-create-new-server)
- [MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk) · [MCP Streamable HTTP 전송 스펙](https://modelcontextprotocol.io/specification/2025-03-26/basic/transports#streamable-http)
- 검증 로그와 실제 출력: [`EVIDENCE.md`](EVIDENCE.md)
