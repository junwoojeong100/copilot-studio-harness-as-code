"""환경 설정과 하네스별 대상(targets) 정의."""
import os
import pathlib

import yaml

LAB_ROOT = pathlib.Path(__file__).resolve().parents[2]


def _load_env_file(path: pathlib.Path) -> None:
    if not path.exists():
        return
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip().strip('"'))


_load_env_file(LAB_ROOT / "lab.env")


def env(name: str, default: str | None = None) -> str:
    v = os.environ.get(name, default)
    if v is None:
        raise SystemExit(f"환경 변수 {name} 가 필요합니다 (lab.env 를 확인하세요).")
    return v


TENANT_ID = lambda: env("CSLAB_TENANT_ID")           # noqa: E731
ENV_ID = lambda: env("CSLAB_ENV_ID")                 # noqa: E731  예: Default-<tenantId>
CLIENT_ID = lambda: env("CSLAB_CLIENT_ID")           # noqa: E731  Entra 공용 클라이언트 앱
MSAL_CACHE = lambda: os.path.expanduser(              # noqa: E731
    os.environ.get("CSLAB_MSAL_CACHE", "~/.cache/csharness-lab/msal_cache.json"))


def environment_host(environment_id: str) -> str:
    """SDK 와 동일한 규칙: 하이픈 제거 → 마지막 2자를 서브도메인 접미사로 분리 (Prod 클라우드)."""
    n = environment_id.lower().replace("-", "")
    return f"{n[:-2]}.{n[-2:]}.environment.api.powerplatform.com"


def agentic_3p_url(environment_id: str, schema_name: str) -> str:
    """GitHub Copilot harness(CliCopilot) 에이전트는 agenticruntime 3p 엔드포인트로 직접 연결한다."""
    return (f"https://{environment_host(environment_id)}/copilotstudio/agenticruntime/3p/"
            f"dataverse-backed/authenticated/bots/{schema_name}?api-version=1")


def load_targets() -> dict:
    return yaml.safe_load((LAB_ROOT / "harness" / "targets.yaml").read_text())["targets"]


def load_cases() -> list[dict]:
    return yaml.safe_load((LAB_ROOT / "shared" / "test-cases.yaml").read_text())["cases"]
