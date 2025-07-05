from core import AgentBase, AgentMessage, AgentCard, ToolRegistry, ToolBase
from tools.file_tool.tool import FileTool
from tools.project_tool.tool import ProjectTool
from tools.shell_tool.tool import ShellTool

from typing import Dict, Any

class Coordinator(AgentBase):
    def __init__(self):
        super().__init__(
            provider="deepseek",
            model="deepseek-chat",
            temperature=0.0,
            max_tokens=8000
        )

        self.tool_registry.register(FileTool())
        self.tool_registry.register(ProjectTool())
        self.tool_registry.register(ShellTool())

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

        return AgentMessage(
            sender=self.card.name or "coordinator",
            receiver="user",
            content=response.get("content", "")
        )
    