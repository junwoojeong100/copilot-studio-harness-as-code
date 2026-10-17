"""Copilot Studio 에이전트와의 대화 세션 (Microsoft 365 Agents SDK - CopilotClient)."""
from dataclasses import dataclass, field

from microsoft_agents.copilotstudio.client import (AgentType, ConnectionSettings, CopilotClient,
                                                   PowerPlatformCloud)

from .auth import get_token
from .config import ENV_ID, agentic_3p_url


@dataclass
class Turn:
    user: str
    messages: list[str] = field(default_factory=list)   # type == message 인 봇 응답
    steps: list[str] = field(default_factory=list)      # 도구·스킬 호출 등 진행 단서(informative)
    thoughts: list[str] = field(default_factory=list)   # 추론 요약(thought 엔터티)
    typing_chars: int = 0


class Session:
    """한 에이전트와의 대화. runtime: published(Standard 등) | agentic3p(GitHub Copilot harness)."""

    def __init__(self, schema_name: str, runtime: str = "published"):
        direct = agentic_3p_url(ENV_ID(), schema_name) if runtime == "agentic3p" else None
        self.settings = ConnectionSettings(
            environment_id=ENV_ID(), agent_identifier=schema_name, cloud=PowerPlatformCloud.PROD,
            copilot_agent_type=AgentType.PUBLISHED, direct_connect_url=direct)
        self.client = CopilotClient(self.settings, get_token())
        self.conversation_id: str | None = None
        self.greeting: list[str] = []

    async def start(self) -> list[str]:
        async for act in self.client.start_conversation(True):
            if act.conversation and act.conversation.id:
                self.conversation_id = act.conversation.id
            if act.type == "message" and act.text:
                self.greeting.append(act.text)
        return self.greeting

    async def say(self, text: str) -> Turn:
        turn = Turn(user=text)
        async for act in self.client.ask_question(text, self.conversation_id):
            if act.conversation and act.conversation.id:
                self.conversation_id = act.conversation.id
            if act.type == "message" and act.text:
                turn.messages.append(act.text)
            elif act.type == "typing" and act.text:
                turn.typing_chars += len(act.text)
            data = act.model_dump(by_alias=True, exclude_none=True)
            cd = data.get("channelData") or {}
            if cd.get("streamType") == "informative" and data.get("text"):
                if data["text"].strip() not in turn.steps:
                    turn.steps.append(data["text"].strip())
            for e in data.get("entities") or []:
                if e.get("type") == "thought" and e.get("text", "").strip():
                    if e["text"].strip() not in turn.thoughts:
                        turn.thoughts.append(e["text"].strip())
        # thought 는 누적 스트림이므로 다른 항목의 접두어인 조각은 제거
        turn.thoughts = [t for t in turn.thoughts
                         if not any(o != t and o.startswith(t) for o in turn.thoughts)]
        return turn
