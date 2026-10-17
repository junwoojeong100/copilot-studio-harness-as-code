# 1. 사전 준비

## 1.1 도구

| 도구 | 용도 | 확인한 버전 | 설치 |
| --- | --- | --- | --- |
| Power Platform CLI (`pac`) | 에이전트 생성·동기화·게시·solution | **2.13.1** (⚠ 2.10.1 은 `pull` 이 예외로 종료) | `dotnet tool install --global Microsoft.PowerApps.CLI.Tool` / 갱신: `dotnet tool update -g Microsoft.PowerApps.CLI.Tool` |
| .NET SDK | `pac` 실행 | 10.0.301 | `brew install dotnet` (macOS) |
| Azure CLI (`az`) | Entra 앱 등록, Azure 리소스, REST 토큰 | 2.86.0 | `brew install azure-cli` |
| Python | 테스트 하네스(Agents SDK) | 3.14 (3.10+) | `brew install python` |
| Node.js | 스킬 가져오기 스크립트(`add-skill.js`) | 22 (18+) | `nvm install --lts` |
| git | 플러그인 저장소 clone | 2.54 | 기본 |

> **macOS + Homebrew dotnet**: `pac` 가 ".NET 을 찾을 수 없다"고 하면 `export DOTNET_ROOT="$(brew --prefix dotnet)/libexec"` 를 설정합니다(`scripts/env.sh` 가 자동 처리).

## 1.2 계정·권한·라이선스 (Caldova 에서 실제 확인한 값)

| 항목 | 값 | 확인 방법 |
| --- | --- | --- |
| Entra 역할 | Global Administrator | `GET /me/transitiveMemberOf/microsoft.graph.directoryRole` |
| Dataverse 역할 (Caldova default) | `Environment Maker`, `Basic User` — **에이전트 생성·게시에 충분** (System Administrator 불필요) | Dataverse `systemusers(...)/systemuserroles_association` |
| Copilot Studio 라이선스 | `VIRTUAL_AGENT_USL`, `COPILOT_STUDIO_IN_COPILOT_FOR_M365` (Microsoft 365 E7 포함) | Graph `me/licenseDetails` |
| Microsoft 365 Copilot | `M365_COPILOT_BUSINESS_CHAT` 등 (Copilot chat harness 용) | 동일 |
| Copilot Credits | 테넌트 선불 용량(Dynamics 365 Premium 포함분)에서 사용. **PAYG 과금 정책 0개**였지만 GitHub harness 가 동작 | Power Platform API `licensing/billingPolicies` |
| DLP 정책 | 0개 (차단 없음) | BAP `PowerPlatform.Governance/v2/policies` |

> 사전 점검은 `scripts/00-preflight.sh` 한 번이면 위 항목을 읽기 전용으로 확인합니다([1.5](#15-사전-점검-스크립트)).

> **필요 권한 정리** — Entra: 앱 등록·관리자 동의(1.4)에 `Application Administrator`/`Global Administrator` 급. Azure 구독: **Owner**(또는 Contributor + User Access Administrator) — Lab 4 의 Bicep 이 ACR 에 `AcrPull` 역할을 할당하고 리소스 공급자를 등록합니다. Power Platform: 대상 환경의 `Environment Maker`(에이전트·연결·커넥터 생성).

## 1.3 로그인 (디바이스 코드)

개인 `az` 로그인과 섞이지 않도록 **전용 구성 디렉터리**를 씁니다(선택). 두 CLI 모두 *디바이스 코드* 방식이라 터미널에는 코드만 출력되고, 브라우저에서 한 번 승인합니다. `export` 는 **그 터미널에서만** 유효하므로, 새 터미널에서도 같은 로그인을 쓰려면 아래 1.4 의 `lab.env` 에 `CSLAB_AZURE_CONFIG_DIR` 을 적어 두세요(스크립트는 이 값만 읽습니다).
```bash
# (선택) 실습 전용 Azure CLI 구성 — 개인 로그인과 분리
export AZURE_CONFIG_DIR=$HOME/.caldova-lab/azure

az login --tenant 8109d700-b6b0-4088-ba33-dc39ef13d7ea --use-device-code --allow-no-subscriptions
# → "To sign in, use a web browser to open the page https://login.microsoft.com/device and enter the code XXXXXXXXX"

pac auth create --name caldova --deviceCode
# → 같은 방식. 성공하면 "Connected to... Caldova (default)" 와 함께 프로필이 활성화된다.
pac env who        # Environment ID: Default-8109d700-…, Org URL: https://orgd5bc94ea.crm3.dynamics.com/
az account show    # e56daab3-… 구독 확인
```

* 브라우저에서 `https://login.microsoft.com/device` 를 열고 코드를 입력한 뒤 **`admin@caldova10993123.onmicrosoft.com`** 을 선택합니다. 회사 계정이 이미 로그인돼 있으면 "Use another account" 를 눌러야 합니다.
* Caldova 관리자 계정은 **패스키(FIDO)** 로그인입니다. 계정 선택 후 패스키 프롬프트가 뜨면 승인하세요.
* 코드는 약 15분 후 만료됩니다. 터미널이 코드를 출력한 직후에 입력하세요.

> 🐞 **실제로 만난 문제 — "성공 화면을 봤는데 CLI 가 안 끝난다"**: 서로 다른 브라우저 프로필에서 입력했을 때 한 번 재현됐습니다. 새 코드를 발급받아(CLI 재실행) 계정 선택 → *Continue* → "You have signed in to … application" 화면까지 확인하면 CLI 가 몇 초 안에 끝납니다.

## 1.4 실습 설정과 Python 환경

```bash
cd CopilotStudio_Harness_CodeLab
cp lab.env.example lab.env          # 값 채우기 (테넌트·환경·구독, CSLAB_CLIENT_ID 는 다음 단계에서 기록)
python3 -m venv .venv
.venv/bin/pip install -r harness/requirements.txt
```

`lab.env` 의 키와 값을 얻는 곳:

| 키 | 값 얻는 방법 |
| --- | --- |
| `CSLAB_TENANT_ID` | `az account show --query tenantId -o tsv` |
| `CSLAB_ENV_ID` | `pac env who` 의 *Environment ID* (기본 환경은 `Default-<tenantId>`) |
| `CSLAB_DATAVERSE_URL` | `pac env who` 의 *Org URL* |
| `CSLAB_SUBSCRIPTION_ID` | `az account show --query id -o tsv` |
| `CSLAB_CLIENT_ID` | 다음 단계(`scripts/01-entra-app.sh`)가 기록 |
| (선택) `CSLAB_AZURE_CONFIG_DIR`, `CSLAB_MSAL_CACHE` | 1.3 의 전용 az 구성 경로 / SDK 토큰 캐시 경로 |

> **실행 규칙**: 이 문서의 모든 명령은 **저장소 루트(`CopilotStudio_Harness_CodeLab/`)에서** 실행합니다. 새 터미널을 열 때마다 `source scripts/env.sh` 를 먼저 실행하면 `lab.env` 값(`$CSLAB_DATAVERSE_URL` 등)·`DOTNET_ROOT`·`PATH` 가 설정됩니다. 하위 폴더에서 실행해야 하는 명령은 `(cd harness && …)` 처럼 서브셸로 감쌌습니다.

### Entra 공용 클라이언트 앱 등록 (코드)

Agents SDK 로 에이전트와 대화하려면 **Power Platform API 의 `CopilotStudio.Copilots.Invoke`** 위임 권한을 가진 Entra 공용 클라이언트 앱이 필요합니다. Copilot chat harness 배포(Lab 3)에는 Graph 의 `AppCatalog.ReadWrite.All` 등을 추가합니다.

```bash
./scripts/01-entra-app.sh     # 앱 생성 → 권한 추가 → 관리자 동의 → lab.env 에 CSLAB_CLIENT_ID 기록
```

핵심 명령(스크립트 내용):

```bash
PPAPI=8578e004-a5c6-46e7-913e-12f58912df43   # "Power Platform API" 서비스 주체
SCOPE_ID=$(az ad sp show --id $PPAPI --query "oauth2PermissionScopes[?value=='CopilotStudio.Copilots.Invoke'].id|[0]" -o tsv)
az ad app create --display-name csharness-lab-sdk-client --sign-in-audience AzureADMyOrg \
   --is-fallback-public-client true --public-client-redirect-uris http://localhost \
   --required-resource-accesses '[{"resourceAppId":"'$PPAPI'","resourceAccess":[{"id":"'$SCOPE_ID'","type":"Scope"}]}]'
az ad sp create --id <appId>
az ad app permission admin-consent --id <appId>
```

(`az ad sp show --id $PPAPI` 가 실패하면 먼저 `az ad sp create --id $PPAPI` 로 Power Platform API 서비스 주체를 만듭니다 — 스크립트가 자동 처리.)

> `az account get-access-token --resource https://api.powerplatform.com` 가 바로 동작하는 것은 Azure CLI 앱에 *관리용* 권한이 사전 동의돼 있기 때문입니다. **에이전트와 대화하는** `Copilots.Invoke` 는 별도 앱 등록이 필요합니다.

## 1.5 사전 점검 스크립트

```bash
./scripts/00-preflight.sh
```

실제 출력(요약, 2026-10-17):

```text
▶ 1) 도구 버전   pac 2.13.1 · az 2.86.0 · node 22 · python 3.14 · dotnet 10.0.301      ✔ pac ≥ 2.13
▶ 2) 로그인      az: admin@caldova10993123.onmicrosoft.com / pac: caldova (Caldova (default))
▶ 3) 환경        Caldova (default) · Default-8109d700-… · canadaeast · Default · Ready
▶ 4) 라이선스    AGENT_365 · M365_COPILOT_BUSINESS_CHAT · COPILOT_STUDIO_IN_COPILOT_FOR_M365 · VIRTUAL_AGENT_USL
▶ 5) Credits     billingPolicies: 0   (선불 용량으로 동작)
▶ 6) 기타        환경에 이미 있는 에이전트는 건드리지 않음
```

> 🐞 **`pac` 2.10.1 의 `copilot pull` 이 `System.FormatException: '1033>>>>>>> '` 로 종료** — 3-way 병합 충돌 마커를 파싱하다 죽는 버그입니다. `dotnet tool update -g Microsoft.PowerApps.CLI.Tool` 로 2.13 이상으로 올리면 정상 동작(충돌은 "Unresolved merge conflict" 메시지로 안내)합니다.
