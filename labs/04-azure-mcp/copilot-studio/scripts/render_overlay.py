#!/usr/bin/env python3
"""agent-overlay 의 템플릿을 에이전트 워크스페이스에 적용한다 (멱등, 비밀값 없음).

  python3 scripts/render_overlay.py --workspace DIR --connection-reference LOGICAL --connector-name shared_...

1) capabilities/tools/*.mcs.yml.tmpl 의 __CONNECTION_REFERENCE__ / __CONNECTOR_NAME__ 을 채워 워크스페이스에 쓴다.
2) settings.mcs.yml 의 첫 StaticSegment 지시문을 agent-overlay/instructions.md 로 바꾼다.
3) --fix-settings-conflict: pull 이 settings.mcs.yml 에 남긴 충돌 표시(<<<<<<< ... >>>>>>>)에서 publishedOn 줄만 남긴다.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

OVERLAY = Path(__file__).resolve().parent.parent / "agent-overlay"


def indent_of(line: str) -> int:
    return len(line) - len(line.lstrip(" "))


def set_instructions(settings: Path, text: str) -> bool:
    lines = settings.read_text(encoding="utf-8").split("\n")
    for i, line in enumerate(lines):
        if line.strip() == "- kind: StaticSegment" and i + 1 < len(lines) and lines[i + 1].strip().startswith("value:"):
            v = indent_of(lines[i + 1])
            end = i + 2
            while end < len(lines) and (lines[end].strip() == "" or indent_of(lines[end]) > v):
                end += 1
            body = [(" " * (v + 2) + t) if t.strip() else "" for t in text.strip("\n").split("\n")]
            trailing = 0                                   # 블록 뒤의 빈 줄(pac 가 다시 써 넣는 구분선)은 그대로 둔다
            while end - trailing - 1 > i + 1 and lines[end - trailing - 1].strip() == "":
                trailing += 1
            new = lines[:i + 1] + [" " * v + "value: |-"] + body + [""] * trailing + lines[end:]
            if new == lines:
                return False
            settings.write_text("\n".join(new), encoding="utf-8")
            return True
    sys.exit("settings.mcs.yml 에서 instructions 의 StaticSegment 를 찾지 못했습니다.")


def fix_conflict(settings: Path) -> bool:
    s = settings.read_text(encoding="utf-8")
    if "<<<<<<<" not in s:
        return False
    out, state = [], "normal"
    for line in s.split("\n"):
        if line.startswith("<<<<<<<"):
            state = "ours"
        elif line.startswith("=======") and state == "ours":
            state = "theirs"
        elif line.startswith(">>>>>>>") and state == "theirs":
            state = "normal"
        elif state == "normal":
            out.append(line)
        elif line.startswith("publishedOn:"):
            out.append(line) if not any(o.startswith("publishedOn:") for o in out) else out.__setitem__(
                max(i for i, o in enumerate(out) if o.startswith("publishedOn:")), line)
        else:
            sys.exit(f"충돌이 publishedOn 이외의 내용에도 있습니다: {line!r} — 직접 해결하세요.")
    settings.write_text("\n".join(out), encoding="utf-8")
    return True


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--workspace", required=True)
    ap.add_argument("--connection-reference")
    ap.add_argument("--connector-name")
    ap.add_argument("--fix-settings-conflict", action="store_true")
    a = ap.parse_args()
    ws = Path(a.workspace)
    settings = ws / "settings.mcs.yml"

    if a.fix_settings_conflict:
        print("[fix] settings.mcs.yml 충돌 표시를 정리했습니다." if fix_conflict(settings) else "[fix] 충돌 없음")
        return 0

    if not a.connection_reference or not a.connector_name:
        sys.exit("--connection-reference 와 --connector-name 이 필요합니다.")
    for tmpl in (OVERLAY / "capabilities" / "tools").glob("*.mcs.yml.tmpl"):
        dst = ws / "capabilities" / "tools" / tmpl.name[: -len(".tmpl")]
        dst.parent.mkdir(parents=True, exist_ok=True)
        rendered = (tmpl.read_text(encoding="utf-8")
                    .replace("__CONNECTION_REFERENCE__", a.connection_reference)
                    .replace("__CONNECTOR_NAME__", a.connector_name))
        if not dst.exists() or dst.read_text(encoding="utf-8") != rendered:
            dst.write_text(rendered, encoding="utf-8")
            print(f"[overlay] wrote {dst.relative_to(ws)}")
        else:
            print(f"[overlay] unchanged {dst.relative_to(ws)}")
    changed = set_instructions(settings, (OVERLAY / "instructions.md").read_text(encoding="utf-8"))
    print("[overlay] instructions updated" if changed else "[overlay] instructions unchanged")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
