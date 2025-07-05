import abc
import asyncio
import json
import os
import inspect
import yaml
from typing import List, Dict, Optional, Any, Union, AsyncGenerator
import re

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

        self.task_id: Optional[str] = "test"
        self.task: Optional["Task"] = None # type: ignore
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
        self.system_prompt, self.user_prompt = self._auto_load_prompt_template()

    def _auto_find_card(self) -> AgentCard:
        """
        自动根据类名查找对应的配置文件
        例如：Coordinator -> coordinator_card.yaml
             BrowserOperator -> browser_operator_card.yaml
        注意：这个方法中不能调用logger，因为还没初始化
        """
        # 获取当前类的名称
        class_name = self.__class__.__name__
        # 驼峰命名转下划线命名
        snake_case = re.sub(r'(?<!^)(?=[A-Z])', '_', class_name).lower()
        card_filename = f"{snake_case}_card.yaml"
        
        # 获取当前文件所在的目录
        current_file = inspect.getfile(self.__class__)
        current_dir = os.path.dirname(current_file)
        
        # 在当前目录下查找配置文件
        card_path = os.path.join(current_dir, card_filename)
        
        if os.path.exists(card_path):
            return AgentCard(card_path)
        else:
            raise FileNotFoundError(f"未找到配置文件: {card_path}")
    
    def _auto_load_prompt_template(self):
        """
        自动加载包含system和user的双模板提示词
        返回包含system_prompt_tmp和user_prompt_tmp的字典
        """
        class_name = self.__class__.__name__
        snake_case = re.sub(r'(?<!^)(?=[A-Z])', '_', class_name).lower()
        prompt_filename = f"{snake_case}_prompt.yaml"
        current_dir = os.path.dirname(inspect.getfile(self.__class__))
        prompt_path = os.path.join(current_dir, prompt_filename)
        
        if not os.path.exists(prompt_path):
            raise FileNotFoundError(f"智能体提示词文件缺失: {prompt_path}")
        
        try:
            # 使用load_prompt直接加载文件，它会自动处理LangChain格式
            from langchain.prompts import load_prompt
            
            # 创建临时文件来分别加载system和user模板
            import tempfile
            
            with open(prompt_path, 'r', encoding='utf-8') as f:
                prompt_data = yaml.safe_load(f)
            
            # 分别创建system和user模板的临时文件
            with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False, encoding='utf-8') as temp_system:
                yaml.dump(prompt_data['system_prompt'], temp_system, default_flow_style=False, allow_unicode=True, encoding='utf-8')
                temp_system_path = temp_system.name
            
            with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False, encoding='utf-8') as temp_user:
                yaml.dump(prompt_data['user_prompt'], temp_user, default_flow_style=False, allow_unicode=True, encoding='utf-8')
                temp_user_path = temp_user.name
            
            try:
                system_template = load_prompt(temp_system_path, encoding="utf-8")
                user_template = load_prompt(temp_user_path, encoding="utf-8")
                return system_template, user_template
            finally:
                # 清理临时文件
                os.unlink(temp_system_path)
                os.unlink(temp_user_path)
            
        except KeyError as e:
            raise ValueError(f"提示词文件缺少必需字段: {e}")
        except Exception as e:
            raise RuntimeError(f"加载提示词失败: {str(e)}")

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

    def _add_routing_instructions(self, agent_message: AgentMessage) -> str:
        prompt = ""
        if self.task is None:
            return prompt
        if agent_message.next_receiver is None:
            prompt += f"""
{agent_message.sender}并没有指定下一个接收者是谁，
{self.task.roster_prompt}
请你在完成当前任务后根据已经获得的所有信息，确定你的消息发送给谁。如果你认为当前的任务已完成，请指定下一个接收者是"user"。
"""
        else:
            prompt += f"""
{agent_message.sender}已经指定下一个接收者是{agent_message.next_receiver}，
请你在完成当前任务后输出的消息中指定下一个接收者。
"""

        prompt += f"""
你同样也可以指定下下个接收者是谁，如果你需要指定则在输出的内容中填写"next_receiver"字段。
如果你不需要指定下下个接收者，则将该字段留空。
"""

        prompt += f"""
        # 输出格式要求
        输出格式务必为JSON格式，不要添加任何其他内容。

        例如：
        {{
            "receiver": <下一个接收者的名称>,
            "next_receiver": <下下一个接收者的名称>,
            "content": <你的消息内容>
        }}
        """
        return prompt
    
    async def _execute_tool_calls_loop(
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
            tool_results = await self._execute_tool_calls(response["tool_calls"])
            
            # 获取工具消息列表
            tool_messages = self._build_tool_response_messages(tool_results, response)
            
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
    
    async def _execute_tool_calls(
        self, 
        tool_calls: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """执行并返回工具调用结果"""
        results = []
        for call in tool_calls:
            tool_name = call["function"]["name"]
            arguments = self._parse_tool_arguments(call)
            
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
    
    def _parse_tool_arguments(
        self, 
        call: Dict[str, Any]
    ) -> Dict[str, Any]:
        """安全解析工具参数"""
        try:
            return json.loads(call["function"]["arguments"])
        except (json.JSONDecodeError, KeyError):
            return {}
    
    def _build_tool_response_messages(
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