#!/usr/bin/env python3
"""Copilot chat harness(선언형 에이전트) 앱 패키지를 코드로 생성한다.

산출물: appPackage/manifest.json, appPackage/declarativeAgent.json, build/issue-triage-copilot.zip
인자: --app-id <GUID>  (Teams 앱 ID; 재배포 시 같은 값을 유지)
      --knowledge-url <url> (선택: OneDrive/SharePoint 파일 URL 을 지식으로 연결)
"""
import argparse
import json
import pathlib
import uuid
import zipfile

HERE = pathlib.Path(__file__).resolve().parent
LAB = HERE.parents[1]
PKG = HERE / "appPackage"
BUILD = HERE / "build"

ap = argparse.ArgumentParser()
ap.add_argument("--app-id", default=None)
ap.add_argument("--knowledge-url", default=None)
ap.add_argument("--version", default="1.0.0")
a = ap.parse_args()

id_file = HERE / ".app-id"
app_id = a.app_id or (id_file.read_text().strip() if id_file.exists() else str(uuid.uuid4()))
id_file.write_text(app_id)

instructions = (LAB / "shared" / "triage-instructions.md").read_text().strip()
instructions += ("\n\nOUTPUT FORMAT\nAnswer with the JSON object only. If the user message is not a GitHub issue to triage, "
                 "ask for the issue title and body.")

agent = {
    "$schema": "https://developer.microsoft.com/json-schemas/copilot/declarative-agent/v1.5/schema.json",
    "version": "v1.5",
    "name": "Issue Triage Copilot",
    "description": "Caldova GitHub 이슈를 라벨 정책에 따라 분류(category/priority/team/needsHumanReview)합니다.",
    "instructions": instructions,
    "conversation_starters": [
        {"title": "서비스 장애 이슈 분류",
         "text": "Title: Checkout API returns 503 for all customers. Body: Started after the latest deployment. No workaround is available."},
        {"title": "문서 오류 이슈 분류",
         "text": "Title: Python quickstart uses the old package name. Body: Step 2 says to install contoso-sdk-old."},
        {"title": "라벨 정책 질문", "text": "P0 와 P1 의 차이를 라벨 정책 기준으로 설명해 줘."},
    ],
}
if a.knowledge_url:
    agent["capabilities"] = [{"name": "OneDriveAndSharePoint", "items_by_url": [{"url": a.knowledge_url}]}]

manifest = {
    "$schema": "https://developer.microsoft.com/json-schemas/teams/v1.22/MicrosoftTeams.schema.json",
    "manifestVersion": "1.22",
    "version": a.version,
    "id": app_id,
    "developer": {
        "name": "Caldova Harness Lab",
        "websiteUrl": "https://www.microsoft.com",
        "privacyUrl": "https://www.microsoft.com/privacy",
        "termsOfUseUrl": "https://www.microsoft.com/servicesagreement",
    },
    "icons": {"color": "color.png", "outline": "outline.png"},
    "name": {"short": "Issue Triage Copilot", "full": "Issue Triage Copilot (Caldova harness lab)"},
    "description": {
        "short": "GitHub 이슈를 라벨 정책으로 분류하는 Copilot 에이전트",
        "full": "Copilot chat harness 실습용 선언형 에이전트입니다. 이슈 제목·본문을 받아 category, priority, team, summary, needsHumanReview 를 JSON 으로 답합니다.",
    },
    "accentColor": "#005FB8",
    "copilotAgents": {"declarativeAgents": [{"id": "issueTriageCopilot", "file": "declarativeAgent.json"}]},
    "permissions": ["identity", "messageTeamMembers"],
    "validDomains": [],
}

PKG.mkdir(exist_ok=True)
(PKG / "declarativeAgent.json").write_text(json.dumps(agent, indent=2, ensure_ascii=False) + "\n")
(PKG / "manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n")

BUILD.mkdir(exist_ok=True)
zip_path = BUILD / "issue-triage-copilot.zip"
with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
    for f in ("manifest.json", "declarativeAgent.json", "color.png", "outline.png"):
        z.write(PKG / f, f)
print(f"app id : {app_id}\npackage: {zip_path} ({zip_path.stat().st_size} bytes)")
