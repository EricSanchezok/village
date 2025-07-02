from core.agent import BaseAgent
from core.agent_message import AgentMessage
from core.tool import ToolRegistry, ToolBase
from tools import FileTool, ProjectTool, ShellTool

from typing import Dict, Any

class Robin(BaseAgent):
    def __init__(self):
        super().__init__(
            name="Robin",
            description=f"""
            我叫Robin，村里人都说我脑子好使。
            村长或者其他人有了想法，都会来找我。你把想做成什么样告诉我，我就能帮你画出详细的‘图纸’。
            这图纸会把一件大事，拆成一步一步的小活儿，比如先打地基，再砌墙，
            最后盖屋顶，每一步都清清楚楚，保证照着做就不会出错。
            如果你有个目标，但不知道具体该怎么动手，来我的工坊，我帮你把路铺好。""",
            provider="deepseek",
            model="deepseek-chat",
            temperature=0.0,
            max_tokens=8000
        )

        self.tool_registry.register(FileTool())
        self.tool_registry.register(ProjectTool())
        self.tool_registry.register(ShellTool())

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
    