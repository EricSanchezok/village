import time
from uuid import uuid4
from datetime import datetime
from typing import Any, Dict, Optional, List, Union

class AgentMessage:
    def __init__(
        self,
        content: Union[str, Dict, List],
        sender: Optional[str] = None,
        receiver: Optional[str] = None,
        next_receiver: Optional[str] = None,
        task_id: Optional[str] = None,
        token_usage: Optional[int] = 0,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        初始化智能体消息

        :param sender: 发送方标识（例如："user" 或 agent.name）
        :param receiver: 接收方标识（目标智能体的名称）
        :param content: 消息内容
        :param task_id: 会话ID（可选）
        :param metadata: 附加元数据（可选）
        """
        self.sender = sender
        self.receiver = receiver
        self.next_receiver = next_receiver
        self.content = content
        self.task_id = task_id
        self.token_usage = token_usage
        self.metadata = metadata or {}
        self.timestamp = datetime.now().isoformat()  # 标准化时间格式
        self.message_id = str(uuid4())  # 生成唯一ID

    def to_dict(self) -> Dict[str, Any]:
        """将消息转换为字典，便于序列化"""
        return {
            "message_id": self.message_id,
            "sender": self.sender,
            "receiver": self.receiver,
            "next_receiver": self.next_receiver,
            "content": self.content,
            "task_id": self.task_id,
            "metadata": self.metadata,
            "timestamp": self.timestamp
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AgentMessage":
        """从字典还原消息"""
        msg = cls(
            sender=data.get("sender", "user"), 
            receiver=data.get("receiver", ""),
            content=data["content"],
            task_id=data.get("task_id", None),
            metadata=data.get("metadata", {})
        )
        # 覆盖自动生成的ID和时间戳
        msg.message_id = data.get("message_id", str(uuid4()))
        msg.timestamp = data.get("timestamp", datetime.now().isoformat())
        return msg
    
    def __str__(self):
        return f"""
发送方：{self.sender}
接收方：{self.receiver}
下一接收方：{self.next_receiver}
内容：{self.content}
任务ID：{self.task_id}
token消耗：{self.token_usage}
元数据：{self.metadata}
时间戳：{self.timestamp}
消息ID：{self.message_id}
        """