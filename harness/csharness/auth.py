"""MSAL 디바이스 코드 로그인 + 토큰 캐시 (최초 1회만 브라우저 승인 필요)."""
import atexit
import os
import sys

import msal

from .config import CLIENT_ID, MSAL_CACHE, TENANT_ID

SCOPE = ["https://api.powerplatform.com/.default"]


def get_token() -> str:
    cache_path = MSAL_CACHE()
    os.makedirs(os.path.dirname(cache_path), exist_ok=True)
    cache = msal.SerializableTokenCache()
    if os.path.exists(cache_path):
        cache.deserialize(open(cache_path).read())

    def _save():
        if cache.has_state_changed:
            with open(cache_path, "w") as f:
                f.write(cache.serialize())
            os.chmod(cache_path, 0o600)

    atexit.register(_save)
    app = msal.PublicClientApplication(
        CLIENT_ID(), authority=f"https://login.microsoftonline.com/{TENANT_ID()}", token_cache=cache)

    accounts = app.get_accounts()
    if accounts:
        result = app.acquire_token_silent(SCOPE, account=accounts[0])
        if result and "access_token" in result:
            return result["access_token"]

    flow = app.initiate_device_flow(scopes=SCOPE)
    if "message" not in flow:
        raise SystemExit(f"디바이스 코드 시작 실패: {flow}")
    print(flow["message"], file=sys.stderr, flush=True)
    result = app.acquire_token_by_device_flow(flow)
    if "access_token" not in result:
        raise SystemExit(f"로그인 실패: {result.get('error_description', result)}")
    return result["access_token"]
