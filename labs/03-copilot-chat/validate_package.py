#!/usr/bin/env python3
"""앱 패키지 JSON 을 공식 JSON Schema 로 검증한다(오프라인 검증, 로그인 불필요)."""
import json
import pathlib
import sys
import urllib.request

from jsonschema import Draft7Validator  # pip install jsonschema

PKG = pathlib.Path(__file__).resolve().parent / "appPackage"
ok = True
for name in ("manifest.json", "declarativeAgent.json"):
    doc = json.loads((PKG / name).read_text())
    schema = json.load(urllib.request.urlopen(doc["$schema"], timeout=30))
    errs = sorted(Draft7Validator(schema).iter_errors(doc), key=lambda e: list(e.path))
    print(f"{'OK  ' if not errs else 'FAIL'} {name}  ({doc['$schema'].split('/')[-2]})")
    for e in errs[:10]:
        ok = False
        print("   -", "/".join(map(str, e.path)) or "(root)", ":", e.message[:200])
sys.exit(0 if ok else 1)
