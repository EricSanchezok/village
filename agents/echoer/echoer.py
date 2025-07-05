from core import AgentBase
from core import AgentMessage

from typing import Dict, Any, List

class Echoer(AgentBase):
    def __init__(self):
        super().__init__(
            provider="deepseek",
            model="deepseek-chat",
            temperature=0.0,
            max_tokens=8000
        )

    async def invoke(self, message: AgentMessage, **kwargs) -> AgentMessage:
        response = await self.chat(messages=self._build_messages(message))
        return AgentMessage(
            sender=self.card.name or "echoer",
            receiver="user",
            content=response.get("content", "")
        )