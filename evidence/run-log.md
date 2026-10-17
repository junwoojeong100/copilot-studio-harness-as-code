# 실행 기록 (수기 발췌)

2026-10-17 KST. 다른 `evidence/` 파일로 남지 않은 명령 결과를 사람이 옮겨 적은 기록입니다(원본은 실행 당시 터미널 출력). 숫자·상태 코드는 실제 출력 그대로입니다.

## 1. 로그인
* `az login --tenant 8109d700-… --use-device-code --allow-no-subscriptions` (디바이스 코드, 브라우저 승인) → `admin@caldova10993123.onmicrosoft.com`, 구독 `e56daab3-…` "ME-Caldova10993123-junwoojeong-1" `Enabled`
* `pac auth create --name caldova --deviceCode` → `Connected to... Caldova (default)`, Org URL `https://orgd5bc94ea.crm3.dynamics.com/`
* `pac` 전역 도구 `2.10.1 → 2.13.1` (`dotnet tool update -g Microsoft.PowerApps.CLI.Tool`). 2.10.1 은 `copilot pull` 에서 `System.FormatException: '1033>>>>>>> '`

## 2. `scripts/00-preflight.sh` 출력 (실행 시각 기준)
```text
▶ 1) 도구 버전
  pac     : Version: 2.13.1+g251dee1 (.NET 10.0.9)
  az      : 2.86.0
  node    : v22.16.0
  python  : Python 3.14.6
  dotnet  : 10.0.301
  ✔ pac 버전 조건 충족 (≥ 2.13)

▶ 2) 로그인 상태
  az  : admin@caldova10993123.onmicrosoft.com 8109d700-b6b0-4088-ba33-dc39ef13d7ea e56daab3-ddd7-41f4-838b-6c938acd874c
  pac : [3]   *      UNIVERSAL caldova            admin@caldova10993123.onmicrosoft.com Public User          Caldova (default)              https://orgd5bc94ea.crm3.dynamics.com/ 

▶ 3) 환경 (Copilot Studio / Dataverse)
    Friendly Name:              Caldova (default)
    Org URL:                    https://orgd5bc94ea.crm3.dynamics.com/
    User Email:                 admin@caldova10993123.onmicrosoft.com
    Environment ID:             Default-8109d700-b6b0-4088-ba33-dc39ef13d7ea
  region·sku·dataverse: canadaeast	Default	Ready

▶ 4) 라이선스 (Microsoft Graph)
  
  AGENT_365	M365_COPILOT_BUSINESS_CHAT	COPILOT_STUDIO_IN_COPILOT_FOR_M365
  VIRTUAL_AGENT_USL

▶ 5) Copilot Credits 과금 정책 (Power Platform API) — 비어 있어도 선불 용량으로 동작할 수 있음
  billingPolicies: 0

▶ 6) 환경에 이미 있는 다른 에이전트 수 (실습은 이 에이전트들을 건드리지 않음)
  15 개
```

## 3. 스크립트 소요 시간 (`time` 출력)
| 스크립트 | 소요 | 비고 |
| --- | --- | --- |
| `10-standard-classic.sh` | 2분 27초 | 첫 시도(1분 53초)는 5단계 `pull` 에서 `Component is missing Id` 로 실패 → push 단계를 추가한 뒤 재실행 |
| `11-standard-generative.sh` | 2분 26초 | |
| `20-github.sh` | 2분 04초 | `Push complete. 5 change(s) pushed.` (지식 파일·사이드카·스킬 앵커·SKILL.md·스크립트) |
| `21-github-models.sh` | 약 8분 | 모델 4종 순차 (게시 4회 포함) |
| `50-alm.sh` | 1분 24초 | 첫 실행에서 import 직후 `publish` 409 → 수동 재시도 성공 → 스크립트에 재시도 루프·clone 단계 추가 |
| `90-verify-all.sh` | 2분 35초 | 4개 대상 |

## 4. Microsoft Graph 게시 (`labs/03-copilot-chat/m365_publish.py`)
* 카탈로그 게시 `201` — `id 7013dd3d-a1e5-4f10-a695-9dc5504098ac`, `externalId 4e705395-d1c8-47ea-9d7c-d38b2caf6a2f`, `distributionMethod: organization`
* 사용자 설치 `201` → 설치 확인 `[('Issue Triage Copilot', 'organization')]`
* 재배포(`--version 1.0.1`): 앱 정의 업데이트 `201`, 사용자 설치 `409 already exists`(정상)
* 첫 실행은 `$filter` 공백 미인코딩으로 `InvalidURL` 예외 → `urllib.parse.quote` 로 수정

## 5. PAYG 과금 정책 (Power Platform API `api-version=2024-10-01` + ARM)
* `az provider register -n Microsoft.PowerPlatform --wait` → `Registered` (이전: `NotRegistered`)
* `POST /licensing/billingPolicies` `name=csharness-lab-payg` → `400 BillingDocumentNameInvalid` ("Min length is 10. Max length is 64. Allowed characters are A-Z and 0-9.")
* 같은 요청 `name=CsharnessLabPayg01`, `location=canada`, `status=Enabled` → `201`, `id ecb9f2ec-a03c-42e6-b5fa-e0453c76b8fe`. ARM 에 `Microsoft.PowerPlatform/accounts/CsharnessLabPayg01` 생성(`provisioningStatus: Succeeded`)
* `POST …/environments/add` 더미 환경 ID → `400 "Environment does not exist or does not belongs to Tenant"` (엔드포인트 형태 확인용, **실제 환경은 링크하지 않음**)
* `DELETE /licensing/billingPolicies/{id}` → `204`, 이후 목록 `{"value":[]}`, ARM 리소스 없음

## 6. 기타
* `COPILOT_HOME` 을 격리해 `copilot plugin marketplace add microsoft/copilot-studio-plugin` → `Marketplace "copilot-studio-plugin" added successfully.`, `copilot plugin install mcs-assistant@copilot-studio-plugin` → `Plugin "mcs-assistant" installed successfully. Installed 8 skills.` (v1.0.2)
* `npm install @microsoft/wiqd`(로컬) → v0.18.0, `engines: node >=24.15.0` 인데 실행 환경은 Node 22.16.0 → `EBADENGINE` 경고, `wiqd doctor` 가 확장 비호환 경고. **배포·로그인은 실행하지 않음**
* Dataverse 조회(읽기 전용): `bots`·`botcomponents`·`solutions`·`publishers`·`systemusers/…/systemuserroles_association`(역할: `Environment Maker`, `Basic User`)
* 기존 데모 에이전트 `cra4a_*`(managed) 13개는 조회만 했음
