from ..agent.agent_base import AgentBase
from ..agent_message.agent_message import AgentMessage
from .roster import Roster
from typing import List, Optional, Dict
import uuid
import asyncio
from ..utils.logger import get_logger

class Task:
    def __init__(self, roster: Roster, agents: Dict[Optional[str], AgentBase]):
        self.task_id = str(uuid.uuid4())
        self.roster = roster
        self.agents = agents
        self.logger = get_logger(f"task.{self.task_id}")
        
        for name, agent in self.agents.items():
            agent.task_id = self.task_id
            agent.task = self

        self.message_pool: List[AgentMessage] = []
        self.message_history: List[AgentMessage] = []

    def get_agent(self, name: Optional[str]) -> Optional[AgentBase]:
        if name is None:
            # 尝试获取协调者
            coordinator = self.agents.get("Eric")
            if coordinator:
                return coordinator
            # 如果没有协调者，返回第一个可用的智能体
            if self.agents:
                return list(self.agents.values())[0]
            return None
        return self.agents.get(name)
        
    async def invoke(self, user_input: str) -> AgentMessage:
        user_message = AgentMessage(
            sender="user",
            receiver="Eric",
            content=user_input,
            task_id=self.task_id
        )

        self.message_pool.append(user_message)
        self.message_history.append(user_message)

        return await self._pipeline()

    async def _pipeline(self) -> AgentMessage:
        max_iterations = 50  # 防止无限循环
        iteration = 0
        
        while iteration < max_iterations:
            if not self.message_pool:
                await asyncio.sleep(0.1)
                iteration += 1
                continue

            message = self.message_pool.pop(0)
            receiver = message.receiver

            if receiver == "user":
                self.logger.info(f"Task {self.task_id} finished")
                return message
            else:
                agent = self.get_agent(receiver)
                if agent is None:
                    self.logger.error(f"Agent {receiver} not found")
                    # 创建错误消息返回给用户
                    error_message = AgentMessage(
                        sender="system",
                        receiver="user",
                        content=f"错误：找不到智能体 {receiver}",
                        task_id=self.task_id
                    )
                    return error_message
                
                try:
                    new_message = await agent.invoke(message, debug=True)
                    if new_message:
                        self.message_pool.append(new_message)
                        self.message_history.append(new_message)
                        self.logger.info(f"Agent {receiver} processed message, next: {new_message.receiver}")
                    else:
                        self.logger.warning(f"Agent {receiver} returned None")
                        break
                except Exception as e:
                    self.logger.error(f"Agent {receiver} error: {e}")
                    # 创建错误消息
                    error_message = AgentMessage(
                        sender="system",
                        receiver="user",
                        content=f"智能体 {receiver} 处理消息时出错: {str(e)}",
                        task_id=self.task_id
                    )
                    return error_message
            
            iteration += 1
        
        # 如果达到最大迭代次数，返回超时消息
        timeout_message = AgentMessage(
            sender="system",
            receiver="user",
            content=f"任务处理超时，已处理 {len(self.message_history)} 条消息",
            task_id=self.task_id
        )
        return timeout_message

    @property
    def roster_prompt(self) -> str:
        return self.roster.prompt
    
    def get_message_history(self) -> List[AgentMessage]:
        """获取任务的消息历史"""
        return self.message_history.copy()
            