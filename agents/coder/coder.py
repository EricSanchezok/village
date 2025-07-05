from core import AgentBase, AgentMessage, AgentCard, ToolRegistry, ToolBase
from tools import ShellTool

from typing import Dict, Any, List
import json

class Coder(AgentBase):
    def __init__(self):
        super().__init__(
            provider="deepseek",
            model="deepseek-chat",
            temperature=0.7,
            max_tokens=8000
        )

        self.tool_registry.register(ShellTool())

    def _build_llm_messages(self, agent_message: AgentMessage) -> List[Dict[str, Any]]:
        return [
            {"role": "system", "content": self.system_prompt.format(
                agent_card=self.card,
                routing_prompt=self._add_routing_instructions(agent_message)
            )},
            {"role": "user", "content": self.user_prompt.format(
                agent_message=agent_message
            )}
        ]

    async def invoke(self, agent_message: AgentMessage, **kwargs) -> AgentMessage:
        llm_messages = self._build_llm_messages(agent_message) 
        llm_response = await self.chat(messages=llm_messages, **kwargs)
        final_llm_response = await self._execute_tool_calls_loop(llm_response, llm_messages, **kwargs)

        json_content = json.loads(final_llm_response.get("content", ""))
        receiver = json_content.get("receiver", None)

        new_agent_message = AgentMessage(
            content=json_content.get("content", ""),
            sender=str(self.card.name),
            receiver=receiver,
            token_usage=llm_response.get("usage", {}).get("total_tokens", 0),
            task_id=agent_message.task_id
        )

        return new_agent_message
    