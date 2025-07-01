from core.agent import BaseAgent
from core.agent_message import AgentMessage

from typing import Dict, Any

class EchoAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            name="EchoAgent",
            description="一个回声智能体，负责重复用户的输入内容。",
            provider="zhipu",
            model="glm-4v-flash",
            temperature=0.0,
            max_tokens=4096
        )

    def _build_messages(self, message: AgentMessage) -> Dict[str, Any]:
        system_prompt = "你是一个回声智能体。你的唯一任务是将收到的消息原样返回，不做任何修改或解释。"
        return [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": message.content}
        ]
 
    async def invoke(self, message: AgentMessage, **kwargs) -> str:
        """
        调用智能体的核心逻辑。
        子类需要实现这个方法。
        """
        response = await self.chat(
            messages=self._build_messages(message)
        )
        return response
    