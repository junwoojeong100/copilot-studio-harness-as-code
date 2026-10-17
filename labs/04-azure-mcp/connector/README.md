# connector/ — Copilot Studio용 커스텀 커넥터(MCP) 정의 파일

이 폴더의 파일은 **다음 랩에서** 배포한 MCP 서버를 Power Platform *커스텀 커넥터*로 등록할 때 사용합니다.
이 랩에서는 `pac` / Power Platform / Copilot Studio를 **실행하지 않았고**, JSON 문법과 필수 필드만 검증했습니다.

| 파일 | 역할 |
| --- | --- |
| `apiDefinition.swagger.json` | OpenAPI 2.0(swagger). `host` = 배포된 Container App FQDN, `POST /mcp` 한 개(`x-ms-agentic-protocol: mcp-streamable-1.0`), 보안 정의 = 헤더 `x-api-key` |
| `apiProperties.json` | 연결(connection) 파라미터(API 키, `securestring`), `iconBrandColor`, `capabilities` |

## 따라 한 공식 문서 (Microsoft Learn, 2026-10-17 확인)

1. [Create a new MCP server for Copilot Studio (mcp-create-new-server)](https://learn.microsoft.com/en-us/microsoft-copilot-studio/mcp-create-new-server) — MCP 서버용 OpenAPI 2.0 예시: `host`, `basePath: /`, `schemes: [https]`, `POST /mcp`, `x-ms-agentic-protocol: mcp-streamable-1.0`. 문서의 예시 operationId는 `InvokeMCP`이고, 이 랩은 `InvokeServer`를 사용합니다(operationId는 임의 이름).
2. [Add an existing MCP server to an agent (mcp-add-existing-server-to-agent)](https://learn.microsoft.com/en-us/microsoft-copilot-studio/mcp-add-existing-server-to-agent) — Copilot Studio에서 MCP 서버 추가, 인증 방식(API 키: Header/Query + 헤더 이름). Copilot Studio는 **Streamable HTTP** 전송만 지원합니다(SSE 미지원).
3. [paconn CLI — API properties file](https://learn.microsoft.com/en-us/connectors/custom-connectors/paconn-cli) — `apiProperties.json` 구조(`connectionParameters.api_key` = `securestring` + `uiDefinition`, `iconBrandColor`, `capabilities`).
4. [pac connector (reference)](https://learn.microsoft.com/en-us/power-platform/developer/cli/reference/connector) — `pac connector create --api-definition-file --api-properties-file [--environment]`.

## 값 매핑

| 항목 | 값 | 이유 |
| --- | --- | --- |
| `host` | `<앱>.<환경ID>.koreacentral.azurecontainerapps.io` | `scripts/deploy.sh` 출력의 FQDN (https 포트 443, 포트 번호 없이) |
| `basePath` | `/` | 문서 예시와 동일 |
| 경로/메서드 | `POST /mcp` | 서버의 Streamable HTTP 엔드포인트 |
| `x-ms-agentic-protocol` | `mcp-streamable-1.0` | Copilot Studio가 이 오퍼레이션을 MCP로 취급하는 표시 |
| 보안 | `apiKey`, `in: header`, `name: x-api-key` | 서버 미들웨어가 요구하는 헤더 |
| 연결 파라미터 | `api_key` (`securestring`) | 보안 정의 키 이름(`api_key`)과 동일하게 맞춤 |

## 사용 방법 (다음 랩에서)

```bash
cd CopilotStudio_Harness_CodeLab/labs/04-azure-mcp

# 1) swagger의 host를 .env.local 의 MCP_ENDPOINT 와 맞추고(다른 곳에 배포한 경우 자동 수정) 필드를 검증
python3 scripts/render_connector.py

# 2-a) pac CLI로 등록 (이 랩에서는 실행하지 않음)
pac connector create \
  --api-definition-file ./connector/apiDefinition.swagger.json \
  --api-properties-file ./connector/apiProperties.json
#   (필요하면 --environment <환경 ID>)

# 2-b) 또는 Power Apps/Power Automate 포털 > 사용자 지정 커넥터 > "OpenAPI 파일 가져오기" 로
#      apiDefinition.swagger.json 을 올리고, 보안 탭에서 API 키(헤더 x-api-key)를 확인
```

연결(connection)을 만들 때 **API Key** 칸에는 `.env.local` 의 `API_KEY` 값을 붙여 넣습니다. 키는 채팅·문서·커밋에 남기지 마세요.
