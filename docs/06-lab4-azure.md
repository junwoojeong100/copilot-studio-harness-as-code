# 6. Lab 4: Azure 연동

> **검증 상태 ✅** — MCP 서버 배포·테스트(16/16), Copilot Studio 등록·호출(5/5), PAYG 과금 정책 API(생성→조회→삭제)를 실제 구독·환경에서 실행했습니다 (2026-10-17).
> 상세 절차·로그: [`labs/04-azure-mcp/README.md`](labs/04-azure-mcp/README.md), [`…/copilot-studio/README.md`](labs/04-azure-mcp/copilot-studio/README.md), 각 `EVIDENCE.md`.

Azure 구독은 이 실습에서 두 곳에 쓰입니다.

| 용도 | 무엇을 | 상태 |
| --- | --- | --- |
| **도구 호스팅** | GitHub harness 에이전트의 *tool* 이 되는 **MCP 서버**를 Azure Container Apps 에 배포 | ✅ 실행 |
| **과금** | Copilot Credits **PAYG 과금 정책**(Azure 구독에 연결) 생성·삭제 | ✅ 정책 API 실행 / ⚠ 환경 링크는 의도적으로 미실행 |

## 6.1 MCP 서버를 Azure Container Apps 에 (코드)

`classify_issue(issue_title, issue_body)`·`get_label_policy()` 두 도구를 가진 **MCP 서버**(Python, 공식 `mcp` SDK, *stateless streamable-HTTP*, `/mcp`)입니다. 분류 로직은 `shared/classify_issue.py` 를 그대로 복사해 씁니다(스킬 스크립트·Power Fx 와 같은 규칙).

```text
labs/04-azure-mcp/
├── server/   server.py · Dockerfile · requirements.txt (mcp==1.30.0)
├── infra/    main.bicep — ACR(Basic) · Container Apps 환경 · 앱(외부 ingress, 시크릿 api-key, AcrPull 시스템 ID)
├── scripts/  deploy.sh(멱등) · test_mcp.py · cleanup.sh
└── connector/ apiDefinition.swagger.json · apiProperties.json   ← Copilot Studio 커스텀 커넥터용
```

```bash
source scripts/env.sh                         # 저장소 루트에서 — $LAB_ROOT, $CSLAB_* 설정
cd "$LAB_ROOT/labs/04-azure-mcp"
# 터미널 1: 서버 실행 (venv 생성 + 포그라운드 실행 — 끝나면 Ctrl+C). python3.12 가 없으면 PYTHON=python3
PYTHON=python3.12 ./scripts/run_local.sh
# 터미널 2: 같은 폴더에서 실제 MCP 클라이언트로 테스트 → 로컬 16/16
.venv/bin/python scripts/test_mcp.py --url http://127.0.0.1:8000/mcp
az account set -s "$CSLAB_SUBSCRIPTION_ID"      # deploy.sh 는 현재 az 기본 구독을 사용하므로 먼저 맞춘다 (source scripts/env.sh 후)
az bicep build --file infra/main.bicep --stdout >/dev/null && ./scripts/deploy.sh --what-if          # 4개 리소스 생성 예정
./scripts/deploy.sh          # RG → ACR/환경 → az acr build(원격 빌드, 로컬 Docker 불필요) → 앱 배포. API 키는 .env.local 에만 저장
.venv/bin/python scripts/test_mcp.py                                                                   # 공개 엔드포인트 16/16 (401 검증 포함)
```

| 항목 | 값 |
| --- | --- |
| 리전 / RG | `koreacentral` / `rg-csharness-lab` (태그 `purpose=copilot-studio-harness-lab`, `deleteAfter=2026-10-24`) |
| 앱 | `ca-csharness-mcp` — 0.25 vCPU / 0.5 GiB, min 1 / max 2, 이미지는 ACR 원격 빌드 35초 |
| 엔드포인트 | `https://ca-csharness-mcp.<고유 접미사>.koreacentral.azurecontainerapps.io/mcp` (`/healthz` 는 키 불필요) |
| 인증 | 헤더 `x-api-key` (ACA 시크릿 `api-key`) — 없으면 **401** |
| 비용 | ACR+ACA 합계 약 US$0.3~0.4/일(소매가 기준 추정, min replica 1) |

`curl` 만으로도 확인됩니다(Accept 헤더 필수, 없으면 406).

```bash
curl -sS "$MCP_ENDPOINT" -H "x-api-key: $API_KEY" -H 'Content-Type: application/json' -H 'Accept: application/json, text/event-stream' \
  -d '{"jsonrpc":"2.0","id":2,"method":"tools/list"}'
```

> 🐞 `pip install mcp` 가 2.x 를 받으면 `mcp.server.fastmcp` 가 없습니다 → `mcp==1.30.0` 고정. 컨테이너에서는 `GET /mcp` 를 405 로 막아야 유휴 SSE 가 매달리지 않습니다. Container Apps 에서 비밀(secret)만 바꾸면 **새 리비전**이 있어야 반영되므로 서버가 키 지문 환경변수를 함께 둡니다.

## 6.2 Copilot Studio 에이전트의 도구로 등록 (포털 없이)

MCP 서버는 **커스텀 커넥터 → 연결 → 연결 참조 → `McpTool` YAML** 사슬로 에이전트에 붙습니다.

```text
에이전트(hlab_IssueTriageMCP) ─ capabilities/tools/*.mcs.yml (kind: McpTool)
        └─ connectionReference ─► 연결(API 키, Power Apps 연결 REST) ─► 커스텀 커넥터(x-ms-agentic-protocol: mcp-streamable-1.0) ─► POST /mcp ─► ACA
```

```bash
cd "$LAB_ROOT/labs/04-azure-mcp/copilot-studio" && ./scripts/setup_all.sh      # 01 커넥터 → 02 연결 → 03 에이전트 → 04 테스트 (멱등, 약 3분)
```

| 단계 | 코드 | 비고 |
| --- | --- | --- |
| 커넥터 | `pac connector create --api-definition-file connector/apiDefinition.swagger.json --api-properties-file connector/apiProperties.json` (스크립트 `01_connector.sh` 는 `render_connector.py` 가 host·title(≤30자)을 채운 **사본**을 사용) | swagger `title` ≤ 30자. 핵심은 `POST /mcp`(`operationId: InvokeServer`) 의 `x-ms-agentic-protocol: mcp-streamable-1.0`. 도구 목록은 YAML 에 쓰지 않고 시작 시 MCP `tools/list` 로 가져옴 |
| 연결 | `PUT https://api.powerapps.com/providers/Microsoft.PowerApps/apis/<커넥터 API 이름>/connections/<GUID>?api-version=2016-11-01` | 키는 `.env.local` 에서 읽음. `pac connection create` 는 서비스 주체 전용이라 API 키 연결 불가 |
| 연결 참조 | Dataverse `connectionreferences` 행 생성 + 연결 바인딩 | **push 전에** 만들어야 함 |
| 에이전트 | `pac copilot init --authoring-mode cli-copilot --schema-name hlab_IssueTriageMCP …` → 도구 YAML → `pull → push → publish → pull` | |

도구 YAML:

```yaml
kind: McpTool
authMode: Maker                 # 연결을 만든 maker 자격으로 호출 (Invoker = 사용자별 연결)
connectionReference: hlab_IssueTriageMCP.cr.<커넥터 API 이름>.<연결 ID>
connectorId: /providers/Microsoft.PowerApps/apis/<커넥터 API 이름>
operationId: InvokeServer       # swagger 의 operationId 와 일치해야 함
```

**도구가 실제로 호출됐다는 증거**

```text
$ chat.py --target github-mcp "Classify this GitHub issue …"
  [step]   Calling Classify GitHub issue...
  [step]   Classify GitHub issue completed
봇 > {"category":"bug","priority":"P0","team":"backend","summary":"bug for backend: Checkout API returns 503 for all customers","needsHumanReview":true}
```

* `summary` 가 **서버의 템플릿 문장**("bug for backend: …")입니다 — 모델이 다시 쓴 문장이 아닙니다.
* 서버 로그(처음 한 번 `az extension add -n containerapp -y` 후 `az containerapp logs show -n ca-csharness-mcp -g rg-csharness-lab --type console --tail 100 --format text`, `--tail` 최대 300)에 호출당 `Processing request of type CallToolRequest` 가 한 번씩 남고, 요청 IP 는 이 PC 가 아니라 Power Platform 대역입니다.

<!-- AUTO:mcp-times -->
<!-- /AUTO -->

**실패 시 동작(음성 테스트)** — 모두 에이전트가 값을 지어내지 않고 "도구를 쓸 수 없다"고 답했습니다.

| 상황 | 결과 |
| --- | --- |
| 연결에 **틀린 API 키** | 연결은 `Connected`, publish 도 성공. 대화 시점에 서버가 401 → 도구 누락 |
| 연결 삭제 | 같은 동작 |
| 도구 YAML 이 **없는 연결 참조**를 가리킴 | `pac copilot push` 가 `IsvAborted` 로 실패 |

> 🐞 연결 참조는 push **전에** Dataverse 에 만들어야 합니다(없으면 `A record with the specified key values does not exist in connectionreference entity`). 반대로 `infrastructure/connections/*.sync.yaml` 을 **미리** 만들어 두면 push 가 `ExportKeyInvalidCreate` 로 실패합니다 — 이 파일은 첫 push 후 **pull 이 서버에서 받아 씁니다**.
> 🐞 `pac connector` 에는 delete 가 없어 정리는 Dataverse `DELETE /connectors(<id>)` 로 합니다(`cleanup.sh`). `pac copilot delete` 는 에이전트 이름의 unmanaged solution 을 남기므로 함께 지웁니다.

## 6.3 PAYG 과금 정책 (Azure 구독과 Power Platform 연결)

Copilot Credits 의 **종량제(PAYG)** 는 *Power Platform 의 과금 정책(billing policy) ↔ Azure 구독/리소스 그룹* 연결입니다. 이 테넌트는 **정책 0개**였고, GitHub harness 가 **테넌트 선불 용량**으로 동작했습니다(그래서 PAYG 가 필수는 아님). 코드로 하는 순서와 이번 실행 결과:

```bash
SUB="$CSLAB_SUBSCRIPTION_ID"      # = e56daab3-ddd7-41f4-838b-6c938acd874c (lab.env)
az provider register -n Microsoft.PowerPlatform --wait                  # 구독의 리소스 공급자 등록 (NotRegistered → Registered)
PPT=$(az account get-access-token --resource https://api.powerplatform.com --query accessToken -o tsv)
# 정책 생성 — name 은 영문·숫자 10~64자, location 은 환경 지역(canada)
curl -s -X POST -H "Authorization: Bearer $PPT" -H 'Content-Type: application/json' \
  "https://api.powerplatform.com/licensing/billingPolicies?api-version=2024-10-01" \
  -d '{"name":"CsharnessLabPayg01","location":"canada","status":"Enabled",
       "billingInstrument":{"id":"/subscriptions/'$SUB'/resourceGroups/rg-csharness-lab","resourceGroup":"rg-csharness-lab","subscriptionId":"'$SUB'"}}'
# → 201 {"id":"ecb9f2ec-…","name":"CsharnessLabPayg01","status":"Enabled","location":"canada", …}
# ARM 에 Microsoft.PowerPlatform/accounts/CsharnessLabPayg01 리소스가 생성됨 (provisioningStatus: Succeeded)
```

| 단계 | API | 결과 |
| --- | --- | --- |
| 조회 | `GET /licensing/billingPolicies?api-version=2024-10-01` | `{"value":[]}` → 생성 후 1개 |
| **환경 링크** | `POST /licensing/billingPolicies/{id}/environments/add` · body `{"environmentIds":["<env id>"]}` | **실행하지 않음** — 링크하면 해당 환경의 Copilot 사용량이 Azure 구독으로 청구됩니다. 엔드포인트 형태는 더미 ID 로 확인(`400 "Environment does not exist or does not belongs to Tenant"`) |
| 삭제 | `DELETE /licensing/billingPolicies/{id}` | `204`, 목록·ARM 리소스 모두 사라짐 |

> 실제 PAYG 를 켜려면 위 *링크* 호출을 실행하고 Power Platform 관리 센터의 **Licensing → Copilot Studio → Capacity overages** 에서 해당 환경이 "Bill to my pay-as-you-go billing plan" 을 쓰는지 확인합니다. 환경별·에이전트별 월 한도는 같은 화면(Manage Agents)에서 설정합니다. 사용량 확인은 Azure Cost Management.

## 6.4 정리

```bash
cd "$LAB_ROOT/labs/04-azure-mcp/copilot-studio" && ./scripts/cleanup.sh --yes      # 커넥터·연결·연결 참조·에이전트
cd "$LAB_ROOT/labs/04-azure-mcp" && ./scripts/cleanup.sh --yes                                    # az group delete -n rg-csharness-lab (ACA·ACR·환경)
```
