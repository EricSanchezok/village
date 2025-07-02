import abc
import asyncio
import json
from typing import List, Dict, Optional, Any, Union, AsyncGenerator

from ..llm_api import BaseAPIAdapter, create_api_adapter
from ..tool import ToolBase, ToolRegistry
from ..agent_message import AgentMessage

class BaseAgent(abc.ABC):
    """
    Agent的基类（优化工具调用历史管理）
    """
    def __init__(
        self,
        name: str,
        description: str,
        provider: str,
        model: str,
        tool_registry: ToolRegistry = ToolRegistry(),
        temperature: float = 0.7,
        max_tokens: int = 4096,
        max_function_calls: int = 10,
    ):
        self.name = name
        self.description = description
        self.provider = provider
        self.model = model
        self.tool_registry = tool_registry
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.max_function_calls = max_function_calls
        
        # 创建API适配器实例
        self.api_adapter: BaseAPIAdapter = create_api_adapter(
            provider=provider,
            model=model
        )
        
    @abc.abstractmethod
    async def invoke(
        self, 
        message: AgentMessage,
        **kwargs
    ) -> Dict[str, Any]:
        """子类需要实现的调用入口"""
        pass

    async def chat(
        self, 
        messages: List[Dict[str, Any]],
        **kwargs
    ) -> Dict[str, Any]:
        """获取LLM的完整响应（不包含工具调用处理）"""
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