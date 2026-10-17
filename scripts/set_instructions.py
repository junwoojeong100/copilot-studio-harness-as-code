#!/usr/bin/env python3
"""CLI(GitHub Copilot harness) 에이전트의 settings.mcs.yml 지침 블록을 파일 내용으로 교체한다(멱등).

사용: set_instructions.py <settings.mcs.yml> <instructions.md>
"""
import re
import sys

path, instr_path = sys.argv[1], sys.argv[2]
lines = open(path).read().split("\n")
instr = open(instr_path).read().rstrip().split("\n")

seg = next(i for i, l in enumerate(lines) if re.match(r"\s*- kind: StaticSegment", l))
vi = next(i for i in range(seg + 1, len(lines)) if re.match(r"\s*value:", lines[i]))
indent = len(lines[vi]) - len(lines[vi].lstrip())
end = vi + 1
while end < len(lines) and (lines[end].strip() == "" or len(lines[end]) - len(lines[end].lstrip()) > indent):
    end += 1
# 블록 뒤 빈 줄은 유지
while end > vi + 1 and lines[end - 1].strip() == "":
    end -= 1
body = [(" " * (indent + 2) + l) if l else "" for l in instr]
lines[vi:end] = [" " * indent + "value: |-"] + body
open(path, "w").write("\n".join(lines))
print(f"지침 {len(instr)}줄 적용: {path}")
