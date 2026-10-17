"""하네스 유형별 대화 방식: single(한 번에 질문) / dialog(Standard classic topic 다중 턴)."""
from .cases import PROMPT
from .client import Session


async def run_single(schema: str, runtime: str, case: dict) -> str:
    s = Session(schema, runtime)
    await s.start()
    i = case["input"]
    turn = await s.say(PROMPT.format(title=i["issueTitle"], body=i["issueBody"]))
    return "\n".join(turn.messages)


async def run_dialog(schema: str, runtime: str, case: dict) -> str:
    """classic orchestration: 트리거 문구 → 제목 질문 → 본문 질문 → 결과 메시지."""
    s = Session(schema, runtime)
    await s.start()
    i = case["input"]
    await s.say("classify an issue")
    await s.say(i["issueTitle"])
    last = await s.say(i["issueBody"])
    return "\n".join(last.messages)


DRIVERS = {"single": run_single, "dialog": run_dialog}
