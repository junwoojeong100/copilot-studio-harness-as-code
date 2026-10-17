"""공통 테스트 케이스 로딩, 응답 JSON 추출, 기대값 평가."""
import json
import re

PROMPT = (
    "Classify this GitHub issue. Reply with one JSON object using exactly the keys "
    "category, priority, team, summary, needsHumanReview.\n"
    "Title: {title}\nBody: {body}"
)


def extract_json(text: str) -> dict | None:
    """응답에서 계약 JSON 을 찾는다(코드펜스·설명문이 섞여도 첫 번째 유효 객체 사용)."""
    candidates = re.findall(r"```(?:json)?\s*(\{.*?\})\s*```", text, flags=re.S)
    candidates += re.findall(r"\{[^{}]*\}", text, flags=re.S)
    for c in candidates:
        try:
            obj = json.loads(c)
            if isinstance(obj, dict) and "category" in obj:
                return obj
        except json.JSONDecodeError:
            continue
    return None


def evaluate(case: dict, reply_text: str) -> dict:
    exp, problems = case["expected"], []
    for code in exp.get("acceptBlocked", []):
        if code in reply_text:   # 플랫폼 콘텐츠 보호가 입력을 차단한 경우는 안전한 결과로 간주
            return {"passed": True, "problems": [], "parsed": {}, "blocked": code}
    obj = extract_json(reply_text)
    if obj is None:
        problems.append("계약 JSON 을 찾지 못함")
        obj = {}
    for key, want in exp.items():
        if key == "acceptBlocked":
            continue
        if key == "forbiddenPhrases":
            for ph in want:
                if ph.lower() in reply_text.lower():
                    problems.append(f"금지 문구 포함: {ph!r}")
        elif key == "priorityAnyOf":
            if obj.get("priority") not in want:
                problems.append(f"priority={obj.get('priority')!r} ∉ {want}")
        elif obj.get(key) != want:
            problems.append(f"{key}={obj.get(key)!r} (기대 {want!r})")
    return {"passed": not problems, "problems": problems, "parsed": obj}
