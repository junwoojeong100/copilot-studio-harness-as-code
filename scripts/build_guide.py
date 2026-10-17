#!/usr/bin/env python3
"""docs/*.md 를 GUIDE.ko.md 로 병합하고 단일 파일 GUIDE.ko.html 을 만든다. (pip install markdown)"""
import base64
import pathlib
import re

import markdown
from markdown.extensions.toc import slugify_unicode

LAB = pathlib.Path(__file__).resolve().parents[1]
import json


def _cases_block(target):
    d = json.loads((LAB / "evidence" / f"{target}.json").read_text())
    rows = []
    for r in d["results"]:
        mark = ("PASS*" if r.get("blocked") else "PASS") if r["passed"] else "FAIL"
        p = r["parsed"]
        body = ("{}   ← 플랫폼이 입력을 차단" if r.get("blocked") else
                "{" + ", ".join(f'"{k}":{json.dumps(p[k])}' for k in ("category", "priority", "team", "needsHumanReview") if k in p) + ", …}")
        rows.append(f"{mark:5} {r['id']:26} {r['seconds']:5.1f}s  {body}")
    star = "  (* = 플랫폼 보호가 차단)" if any(r.get("blocked") for r in d["results"]) else ""
    rows.append(f"[{d['target']}] {d['passed']}/{d['total']} passed{star}")
    return "```text\n" + "\n".join(rows) + f"\n```\n(실제 출력 발췌 — `evidence/{target}.json`, 빌드 시점의 최신 실행)\n"


def _mcp_times():
    d = json.loads((LAB / "evidence" / "github-mcp.json").read_text())
    secs = [r["seconds"] for r in d["results"]]
    sub = json.loads((LAB / "labs/04-azure-mcp/copilot-studio/evidence/github-mcp-cases-run3.json").read_text())
    s2 = [r["seconds"] for r in sub["results"]]
    f = lambda xs: " · ".join(f"{x:.1f}" for x in xs)
    return ("```text\n[github-mcp] %d/%d passed\n  최종 90-verify-all (evidence/github-mcp.json): %s s, 평균 %.1f s\n  서브 에이전트 3회차 (…/copilot-studio/evidence/github-mcp-cases-run3.json): %s s, 평균 %.1f s\n```\n(서로 다른 시간대의 실행입니다)"
            % (d["passed"], d["total"], f(secs), sum(secs) / len(secs), f(s2), sum(s2) / len(s2)))


def _render(text):
    text = re.sub(r"<!-- AUTO:cases:([\w-]+) -->\n<!-- /AUTO -->\n", lambda m: _cases_block(m.group(1)), text)
    text = re.sub(r"<!-- AUTO:mcp-times -->\n<!-- /AUTO -->", lambda m: _mcp_times(), text)
    return text


parts = sorted((LAB / "docs").glob("[0-9][0-9]-*.md"))
md = _render("\n\n---\n\n".join(p.read_text().strip() for p in parts) + "\n")
(LAB / "GUIDE.ko.md").write_text(md)

body = markdown.markdown(md, extensions=["tables", "fenced_code", "toc", "sane_lists", "attr_list"],
                         extension_configs={"toc": {"permalink": False, "slugify": slugify_unicode}})
def _inline(m):
    alt, path = m.group(1), m.group(2)
    f = LAB / path
    if f.exists():
        return f'<img alt="{alt}" style="max-width:100%;border:1px solid #d0d7de;border-radius:6px" src="data:image/png;base64,{base64.b64encode(f.read_bytes()).decode()}">'
    return m.group(0)


body = re.sub(r'<img alt="([^"]*)" src="([^"]+\.png)"\s*/?>', _inline, body)
css = """
:root{color-scheme:light dark} body{font:15px/1.65 -apple-system,'Apple SD Gothic Neo','Segoe UI',sans-serif;max-width:1040px;margin:2rem auto;padding:0 1.2rem;color:#1b1f24}
h1{border-bottom:2px solid #0b5fb3;padding-bottom:.3rem;margin-top:2.6rem;color:#0b3d73} h2{margin-top:2rem;color:#0b5fb3} h3{margin-top:1.6rem}
table{border-collapse:collapse;margin:1rem 0;width:100%;font-size:13.5px} th,td{border:1px solid #d0d7de;padding:.4rem .6rem;vertical-align:top} th{background:#f0f4f9;text-align:left}
code{background:#f1f3f5;padding:.1rem .3rem;border-radius:4px;font:12.5px ui-monospace,Menlo,monospace} pre{background:#0f1720;color:#e6edf3;padding:1rem;border-radius:8px;overflow:auto;line-height:1.45}
pre code{background:none;color:inherit;padding:0} blockquote{border-left:4px solid #0b5fb3;background:#f2f7fd;margin:1rem 0;padding:.4rem 1rem;color:#24292f} hr{border:0;border-top:1px dashed #c8d1da;margin:2.5rem 0}
@media (prefers-color-scheme:dark){body{background:#0d1117;color:#e6edf3} th{background:#161b22} td,th{border-color:#30363d} code{background:#1f2630} blockquote{background:#10243b;color:#e6edf3} h1,h2{color:#79b8ff}}
"""
html = f"<!doctype html><html lang='ko'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'><title>Copilot Studio 하네스 코드 실습</title><style>{css}</style></head><body>{body}</body></html>"
(LAB / "GUIDE.ko.html").write_text(html)
print(f"GUIDE.ko.md {len(md):,} chars ({len(parts)} docs) / GUIDE.ko.html {len(html):,} bytes")
