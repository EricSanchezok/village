import abc
import asyncio
import json
import os
import inspect
from tkinter import NO
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
        tool_registry: Optional[ToolRegistry] = None,
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
        self.tool_registry = tool_registry if tool_registry is not None else ToolRegistry()
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
        if self.task is None:
            return ""
        
        return f"""
    你作为{self.card.name}，收到了来自{agent_message.sender}的消息。

    # 你的任务
    1. 处理当前消息内容
    2. 生成回复并指定接收者(receiver)
    3. 根据当前任务状态，决定是否继续流转或结束：
    - 如果任务已完成，指定接收者为"user"
    - 如果还需继续处理，从下列角色中选择合适接收者：
    {self.task.roster_prompt}

    # 回复内容编写要求
    请基于以下规则撰写回复内容：
    - 内容应是针对接收者(receiver)的完整指令或回复
    - 使用接收者能理解的专业术语和表述风格
    - 包含所有必要上下文信息

    # 输出格式要求 (JSON格式)
    必须严格使用以下JSON格式输出：

    {{
        "receiver": "<接收者名称>",
        "content": "你的回复内容（针对接收者）"
    }}

    示例：
    {{
        "receiver": "数据工程师",
        "content": "张工，我已处理完销售数据清洗工作。请基于附件中的清洗结果进行ETL流程，重点处理Q3异常值问题"
    }}

    重要提示：
    - 接收者(receiver)字段必须明确指定
    - 内容(content)应直接与接收者对话，无需二次解释
    """
    
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