from core.agent import BaseAgent
from core.agent_message import AgentMessage
from core.tool import ToolRegistry, ToolBase
from tools import DateTool, FileTool

from typing import Dict, Any

class TestAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            name="TestAgent",
            description="一个测试智能体，可以执行各种测试任务。",
            provider="deepseek",
            model="deepseek-chat",
            temperature=0.0,
            max_tokens=4096
        )

        self.tool_registry.register(DateTool())
        self.tool_registry.register(FileTool())

    def _build_messages(self, message: AgentMessage) -> Dict[str, Any]:
        system_prompt = "你是一个测试智能体，请你尽可能的满足用户的请求，请确保提供准确的结果和反馈。"
        return [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": message.content}
        ]
 
    async def invoke(self, agent_message: AgentMessage, **kwargs) -> str:
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
    