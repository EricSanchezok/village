import abc
import asyncio
import json
import os
import inspect
import yaml
from typing import List, Dict, Optional, Any, Union, AsyncGenerator

from langchain.prompts import load_prompt

from ..llm_api.api_adapters import BaseAPIAdapter, create_api_adapter
from ..tool.tool_base import ToolBase
from ..tool.tool_registry import ToolRegistry
from ..agent_message.agent_message import AgentMessage
from ..agent_card.agent_card import AgentCard
from ..utils.logger import get_logger

class AgentBase(abc.ABC):
    """
    Agent的基类（优化工具调用历史管理）
    """
    def __init__(
        self,
        card: Optional[AgentCard] = None,
        provider: str = "deepseek",
        model: str = "deepseek-chat",
        tool_registry: ToolRegistry = ToolRegistry(),
        temperature: float = 0.7,
        max_tokens: int = 4096,
        max_function_calls: int = 10,
    ):
        # 如果没有提供card，则自动查找
        if card is None:
            card = self._auto_find_card()
        
        self.logger = get_logger(f"agent.{card.name}")
        self.card = card
        self.provider = provider
        self.model = model
        self.tool_registry = tool_registry
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.max_function_calls = max_function_calls

        if self.provider and self.model:
            self.api_adapter = create_api_adapter(
                provider=provider,
                model=model
            )
        else:
            self.api_adapter = None
        
        # 自动加载提示词模板
        self.prompt_template = self._auto_load_prompt_template()
    
    def _auto_find_card(self) -> AgentCard:
        """
        自动根据类名查找对应的配置文件
        例如：Coordinator -> coordinator_card.yaml
        """
        # 获取当前类的名称
        class_name = self.__class__.__name__
        # 转换为小写并添加后缀
        card_filename = f"{class_name.lower()}_card.yaml"
        
        # 获取当前文件所在的目录
        current_file = inspect.getfile(self.__class__)
        current_dir = os.path.dirname(current_file)
        
        # 在当前目录下查找配置文件
        card_path = os.path.join(current_dir, card_filename)
        
        if os.path.exists(card_path):
            self.logger.info(f"自动找到配置文件: {card_path}")
            return AgentCard(card_path)
        else:
            # 如果找不到配置文件，创建一个默认的
            self.logger.warning(f"未找到配置文件: {card_path}，使用默认配置")
            raise FileNotFoundError(f"未找到配置文件: {card_path}")
    
    def _auto_load_prompt_template(self):
        """
        自动根据类名查找并加载提示词模板
        例如：Echoer -> echoer_prompt.yaml
        """
        # 获取当前类的名称
        class_name = self.__class__.__name__
        # 转换为小写并添加后缀
        prompt_filename = f"{class_name.lower()}_prompt.yaml"
        
        # 获取当前文件所在的目录
        current_file = inspect.getfile(self.__class__)
        current_dir = os.path.dirname(current_file)
        
        # 在当前目录下查找提示词文件
        prompt_path = os.path.join(current_dir, prompt_filename)
        
        if os.path.exists(prompt_path):
            self.logger.info(f"自动找到提示词文件: {prompt_path}")
            try:
                return load_prompt(prompt_path)
            except Exception as e:
                self.logger.error(f"加载提示词模板失败: {e}")
                raise FileNotFoundError(f"提示词文件格式错误: {prompt_path} - {e}")
        else:
            # 如果找不到提示词文件，报错
            self.logger.error(f"未找到提示词文件: {prompt_path}")
            raise FileNotFoundError(f"智能体必须要有系统提示词！未找到文件: {prompt_path}")
    
    def _build_messages(self, message: AgentMessage) -> List[Dict[str, Any]]:
        """
        构建消息列表，使用langchain提示词模板
        """
        # 使用提示词模板格式化
        system_prompt = self.prompt_template.format(
            agent_card=self.card,
            agent_message=message
        )
        
        return [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": message.content}
        ]

    @abc.abstractmethod
    async def invoke(
        self, 
        message: AgentMessage,
        **kwargs
    ) -> AgentMessage:
        """子类需要实现的调用入口"""
        pass

    async def chat(
        self, 
        messages: List[Dict[str, Any]],
        **kwargs
    ) -> Dict[str, Any]:
        """获取LLM的完整响应（不包含工具调用处理）"""
        if self.api_adapter is None:
            raise ValueError("API adapter not initialized")
        tools = self.tool_registry.get_tool_schemas()
        if tools:
            kwargs["tools"] = tools
        return await self.api_adapter.chat_completion(
            messages=messages,
            temperature=self.temperature,
            max_tokens=self.max_tokens,
            **kwargs
        )
    
    async def process_with_tools(
        self, 
        response: Dict[str, Any],  # 确保这是字典类型
        messages: List[Dict[str, Any]], 
        **kwargs
    ) -> Dict[str, Any]:
        """
        处理带工具调用的完整流程，保持原始消息历史纯净
        """
        working_messages = messages.copy()
        iteration = 0
        
        while iteration <= self.max_function_calls and response.get("tool_calls"):
            tool_results = await self.handle_tool_calls(response["tool_calls"])
            
            # 获取工具消息列表
            tool_messages = self.build_tool_message(tool_results, response)
            
            # 添加助手消息
            working_messages.append({
                "role": "assistant",
                "content": response.get("content", ""),
                "tool_calls": response["tool_calls"]
            })
            
            # 添加所有工具消息
            working_messages.extend(tool_messages)
            
            iteration += 1
            response = await self.chat(messages=working_messages, **kwargs)

        if iteration > self.max_function_calls and response.get("tool_calls"):
            return {
                "error": f"达到最大工具调用次数限制 ({self.max_function_calls})",
                "last_response": response
            }
        return response
    
    async def handle_tool_calls(
        self, 
        tool_calls: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """执行并返回工具调用结果"""
        results = []
        for call in tool_calls:
            tool_name = call["function"]["name"]
            arguments = self.parse_tool_arguments(call)
            
            tool = self.tool_registry.get_tool(tool_name)
            if not tool:
                results.append({
                    "tool_name": tool_name,
                    "arguments": arguments,
                    "status": "error",
                    "content": f"工具未找到: {tool_name}"
                })
                continue
            
            try:
                result = await tool.run(**arguments)
                results.append({
                    "tool_name": tool_name,
                    "arguments": arguments,
                    "status": "success",
                    "content": str(result)
                })
            except Exception as e:
                results.append({
                    "tool_name": tool_name,
                    "arguments": arguments,
                    "status": "error",
                    "content": f"执行错误: {str(e)}"
                })
        
        return results
    
    def parse_tool_arguments(
        self, 
        call: Dict[str, Any]
    ) -> Dict[str, Any]:
        """安全解析工具参数"""
        try:
            return json.loads(call["function"]["arguments"])
        except (json.JSONDecodeError, KeyError):
            return {}
    
    def build_tool_message(
        self,
        tool_results: List[Dict[str, Any]],
        original_response: Dict[str, Any]
    ) -> List[Dict[str, Any]]:  # 返回类型改为列表
        """
        为每个工具调用构建单独的工具消息
        """
        tool_messages = []
        
        # 确保工具结果与原始响应中的工具调用顺序一致
        for i, (call, res) in enumerate(zip(original_response["tool_calls"], tool_results)):
            content = f"工具调用结果:\n"
            content += f"- 工具名称: {res['tool_name']}\n"
            content += f"- 参数: {json.dumps(res['arguments'], ensure_ascii=False)}\n"
            content += f"- 状态: {res['status']}\n"
            content += f"- 结果: {res['content']}\n"
            
            tool_messages.append({
                "role": "tool",
                "tool_call_id": call["id"],  # 使用对应工具调用的id
                "content": content
            })
        
        return tool_messages