#!/usr/bin/env python3
"""선언형 에이전트 패키지를 Microsoft Graph(Teams 앱 카탈로그)로 배포하고 사용자에게 설치한다.

흐름: (1) 디바이스 코드 로그인 → (2) POST /appCatalogs/teamsApps (조직 카탈로그 게시)
      → (3) POST /me/teamwork/installedApps (관리자 본인에게 설치) → (4) 설치 목록으로 검증
사용: python m365_publish.py [--zip build/issue-triage-copilot.zip] [--uninstall]
"""
import argparse
import json
import os
import pathlib
import sys
import urllib.error
import urllib.parse
import urllib.request

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "harness"))
import msal  # noqa: E402

from csharness.config import CLIENT_ID, MSAL_CACHE, TENANT_ID  # noqa: E402

GRAPH = "https://graph.microsoft.com/v1.0"
SCOPES = ["https://graph.microsoft.com/AppCatalog.ReadWrite.All",
          "https://graph.microsoft.com/TeamsAppInstallation.ReadWriteForUser",
          "https://graph.microsoft.com/User.Read"]
HERE = pathlib.Path(__file__).resolve().parent


def token() -> str:
    cache = msal.SerializableTokenCache()
    path = MSAL_CACHE()
    if os.path.exists(path):
        cache.deserialize(open(path).read())
    app = msal.PublicClientApplication(CLIENT_ID(), authority=f"https://login.microsoftonline.com/{TENANT_ID()}",
                                       token_cache=cache)
    res = None
    for acct in app.get_accounts():
        res = app.acquire_token_silent(SCOPES, account=acct)
        if res and "access_token" in res:
            break
    if not res or "access_token" not in res:
        flow = app.initiate_device_flow(scopes=SCOPES)
        print(flow["message"], file=sys.stderr, flush=True)
        res = app.acquire_token_by_device_flow(flow)
    if "access_token" not in res:
        raise SystemExit(f"로그인 실패: {res.get('error_description', res)}")
    if cache.has_state_changed:
        open(path, "w").write(cache.serialize())
        os.chmod(path, 0o600)
    return res["access_token"]


def call(method, url, tok, body=None, ctype="application/json"):
    data = body if isinstance(body, (bytes, type(None))) else json.dumps(body).encode()
    req = urllib.request.Request(url, data=data, method=method,
                                 headers={"Authorization": f"Bearer {tok}", "Content-Type": ctype})
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            raw = r.read()
            return r.status, (json.loads(raw) if raw else {})
    except urllib.error.HTTPError as e:
        raw = e.read().decode()
        try:
            return e.code, json.loads(raw)
        except json.JSONDecodeError:
            return e.code, {"raw": raw}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--zip", default=str(HERE / "build" / "issue-triage-copilot.zip"))
    ap.add_argument("--uninstall", action="store_true", help="설치·카탈로그 항목 삭제")
    a = ap.parse_args()
    tok = token()
    manifest_id = json.loads((HERE / "appPackage" / "manifest.json").read_text())["id"]

    st, found = call("GET", f"{GRAPH}/appCatalogs/teamsApps?$filter=" + urllib.parse.quote(f"externalId eq '{manifest_id}'"), tok)
    existing = (found.get("value") or [None])[0] if st == 200 else None

    if a.uninstall:
        if existing:
            st, r = call("DELETE", f"{GRAPH}/appCatalogs/teamsApps/{existing['id']}", tok)
            print("카탈로그 삭제:", st)
        else:
            print("삭제할 앱이 없습니다.")
        return

    zip_bytes = open(a.zip, "rb").read()
    if existing:
        st, r = call("POST", f"{GRAPH}/appCatalogs/teamsApps/{existing['id']}/appDefinitions", tok, zip_bytes, "application/zip")
        print("앱 정의 업데이트:", st, json.dumps(r)[:200])
        app_id = existing["id"]
    else:
        st, r = call("POST", f"{GRAPH}/appCatalogs/teamsApps?requiresReview=false", tok, zip_bytes, "application/zip")
        print("카탈로그 게시:", st, json.dumps(r, ensure_ascii=False)[:300])
        if st not in (200, 201):
            raise SystemExit(1)
        app_id = r["id"]

    st, r = call("POST", f"{GRAPH}/me/teamwork/installedApps", tok,
                 {"teamsApp@odata.bind": f"{GRAPH}/appCatalogs/teamsApps/{app_id}"})
    if st in (200, 201, 204):
        print("사용자 설치: ok")
    elif st == 409:
        print("사용자 설치: 이미 설치되어 있음(정상, 앱 정의만 갱신됨)")
    else:
        print("사용자 설치 실패:", st, json.dumps(r, ensure_ascii=False)[:300])

    st, r = call("GET", f"{GRAPH}/me/teamwork/installedApps?$expand=teamsApp&$filter=" + urllib.parse.quote(f"teamsApp/id eq '{app_id}'"), tok)
    names = [(x["teamsApp"]["displayName"], x["teamsApp"].get("distributionMethod")) for x in r.get("value", [])] if st == 200 else r
    print("설치 확인:", names)


if __name__ == "__main__":
    main()
