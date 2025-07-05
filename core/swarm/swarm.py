from ..agent_card.agent_card import AgentCard
from ..agent_message.agent_message import AgentMessage
from ..agent.agent_base import AgentBase
from ..utils.logger import get_logger
from .roster import Roster
from typing import List, Dict, Optional, Any
import uuid
import asyncio
from .task import Task

class Swarm:
    def __init__(self):
        self.logger = get_logger("swarm")
        self.roster = Roster()
        self.agents: Dict[Optional[str], AgentBase] = {}
        self.tasks: Dict[str, Task] = {}

    def register_agent(self, agent: AgentBase):
        self.roster.register_card(agent.card)
        self.agents[agent.card.name] = agent

    def unregister_agent(self, agent: AgentBase):
        self.roster.unregister_card(agent.card)
        self.agents.pop(agent.card.name)

    async def invoke(self, user_input: str, task_id: Optional[str] = None) -> AgentMessage:
        if task_id is None:
            task_id = str(uuid.uuid4())
        if task_id not in self.tasks:
            self.tasks[task_id] = Task(self.roster, self.agents)
        return await self.tasks[task_id].invoke(user_input)


