from core import AgentBase, AgentMessage, AgentCard, ToolRegistry, ToolBase
from tools import ShellTool

from typing import Dict, Any, List
import json

class Coordinator(AgentBase):
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
                format_prompt=self._add_routing_instructions(agent_message)
            )},
            {"role": "user", "content": self.user_prompt.format(
                agent_message=agent_message
            )}
        ]

    async def invoke(self, message: AgentMessage, **kwargs) -> AgentMessage:
        llm_messages = self._build_llm_messages(message) 
        response = await self.chat(messages=llm_messages, **kwargs)
        final_response = await self._execute_tool_calls_loop(response, llm_messages, **kwargs)

        json_content = json.loads(final_response.get("content", ""))
        receiver = json_content.get("receiver", None)
        next_receiver = json_content.get("next_receiver", None)

        new_agent_message = AgentMessage(
            content=json_content.get("content", ""),
            sender=str(self.card.name),
            receiver=receiver,
            next_receiver=next_receiver,
            token_usage=response.get("usage", {}).get("total_tokens", 0),
            task_id=message.task_id
        )

        return new_agent_message
    