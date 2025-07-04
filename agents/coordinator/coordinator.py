from core.agent import BaseAgent
from core.agent_message import AgentMessage
from core.agent_card import AgentCard
from core.tool import ToolRegistry, ToolBase
from tools import FileTool, ProjectTool, ShellTool

from typing import Dict, Any

class Coordinator(BaseAgent):
    def __init__(self):
        super().__init__(
            card=AgentCard("agents/coordinator/coordinator_card.yaml"),
            provider="deepseek",
            model="deepseek-chat",
            temperature=0.0,
            max_tokens=8000
        )

        self.tool_registry.register(FileTool())
        self.tool_registry.register(ProjectTool())
        self.tool_registry.register(ShellTool())

    def _build_messages(self, message: AgentMessage) -> list[dict[str, Any]]:
        system_prompt = "你是一个测试智能体，请你尽可能的满足用户的请求，请确保提供准确的结果和反馈。"
        return [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": message.content}
        ]
 
    async def invoke(self, agent_message: AgentMessage, **kwargs) -> AgentMessage:
        """
        调用智能体的核心逻辑。
        子类需要实现这个方法。
        """
        messages = self._build_messages(agent_message)

        response = await self.chat(
            messages=messages,
            **kwargs
        )

        response = await self.process_with_tools(response, messages, **kwargs)

        return response
    