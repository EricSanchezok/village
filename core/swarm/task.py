from ..agent.agent_base import AgentBase
from ..agent_message.agent_message import AgentMessage
from .roster import Roster
from typing import List, Optional, Dict, cast
import uuid
import asyncio
from ..utils.logger import get_logger
from pathlib import Path
import json

class Task:
    """任务管理系统，协调多个智能体的协作处理流程"""
    
    MAX_ITERATIONS = 50  # 防止无限循环的最大迭代次数
    
    def __init__(self, roster: Roster, agents: Dict[Optional[str], AgentBase]):
        """
        初始化任务系统
        
        参数:
        - roster: 智能体花名册，包含可用智能体信息
        - agents: 参与本任务的智能体字典 {name: AgentBase}
        """
        self.task_id = str(uuid.uuid4())
        self.roster = roster
        self.agents = agents
        self.logger = get_logger(f"task.{self.task_id}")
        
        # 设置智能体与任务的关联
        for name, agent in self.agents.items():
            agent.task_id = self.task_id
            agent.task = self
            if agent.api_adapter is not None:
                agent.api_adapter.task_id = self.task_id

        self.message_pool: List[AgentMessage] = []  # 待处理消息队列
        self.message_history: List[AgentMessage] = []  # 完整消息历史

        self.message_history_path = Path(__file__).parent.parent.parent / ".data" / self.task_id / "message_history.json"
        self.message_history_path.parent.mkdir(parents=True, exist_ok=True)

    def get_agent(self, name: Optional[str]) -> Optional[AgentBase]:
        """根据名称获取智能体实例"""
        # 如果未指定名称，优先返回协调者(Eric)
        if name is None:
            coordinator = self.agents.get("Eric")
            if coordinator:
                return coordinator
            # 如果没有协调者，返回第一个可用的智能体
            if self.agents:
                return next(iter(self.agents.values()), None)
            return None
        return self.agents.get(name)
        
    async def invoke(self, user_input: str) -> AgentMessage:
        """
        启动任务处理流程
        
        参数:
        - user_input: 用户输入内容
        
        返回:
        - 最终处理结果消息
        """
        user_message = AgentMessage(
            sender="user",
            receiver="Eric",  # 默认路由到Eric进行任务分配
            content=user_input,
            task_id=self.task_id
        )

        self.logger.info(f"Starting task with input: {user_input}")
        self.message_pool.append(user_message)

        return await self._process_messages()

    async def _process_messages(self) -> AgentMessage:
        """
        内部消息处理管道
        从消息池中处理消息，直到任务完成或达到最大迭代次数
        """
        iterations = 0
        
        while iterations < self.MAX_ITERATIONS:
            # 当消息池为空时短暂等待
            if not self.message_pool:
                await asyncio.sleep(0.1)
                iterations += 1
                continue

            # 获取并处理下一个消息
            message = self.message_pool.pop(0)
            self.message_history.append(message)
            self.message_history_path.write_text(json.dumps([message.model_dump() for message in self.message_history], indent=4, ensure_ascii=False, default=str))

            receiver = message.receiver

            self.logger.debug(f"Processing message from {message.sender} to {receiver}")
            
            # 当消息路由回用户时，任务结束
            if receiver == "user":
                self.logger.info(f"Task completed successfully after {iterations} iterations")
                return message
            
            # 获取目标智能体
            agent = self.get_agent(receiver)
            if agent is None:
                self.logger.error(f"Agent {receiver} not found in roster")
                message = AgentMessage(
                    sender="system",
                    receiver="Eric",
                    content=f"智能体 {receiver} 未找到",
                    task_id=self.task_id
                )
                self.message_pool.append(message)
                continue
            
            try:
                # 调用智能体处理消息
                response_message = await agent.invoke(message, debug=False)
                
                if response_message:
                    self.message_pool.append(response_message)
                    self.logger.debug(
                        f"Agent {receiver} processed message. Next receiver: {response_message.receiver}"
                    )
                else:
                    self.logger.warning(
                        f"Agent {receiver} returned None. Ending task early."
                    )
                    break
                    
            except Exception as e:
                self.logger.exception(
                    f"Error processing message by {receiver}: {str(e)}"
                )
                message = AgentMessage(
                    sender=str(agent.card.name),
                    receiver="Eric",
                    content=f"智能体 {receiver} 处理消息时出错: {str(e)}",
                    task_id=self.task_id
                )
                self.message_pool.append(message)
            
            iterations += 1
        
        # 超时处理
        self.logger.warning(
            f"Task timeout reached after {iterations} iterations and "
            f"{len(self.message_history)} processed messages"
        )
        return AgentMessage(
            sender="system",
            receiver="user",
            content=f"任务处理超时，已处理 {len(self.message_history)} 条消息",
            task_id=self.task_id
        )

    @property
    def roster_prompt(self) -> str:
        """获取智能体花名册的提示信息"""
        return self.roster.prompt
    
    def get_message_history(self) -> List[AgentMessage]:
        """获取完整的任务消息历史记录"""
        return self.message_history.copy()