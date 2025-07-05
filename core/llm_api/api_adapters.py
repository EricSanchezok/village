# core/llm_api/api_adapters.py
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional
from pprint import pprint

import openai

from ..config import get_api_config
from ..utils.logger import get_logger
from ..utils.exceptions import APIError

class BaseAPIAdapter(ABC):
    """API适配器基类"""
    
    def __init__(self, provider: str, model: str, **kwargs):
        self.provider = provider
        self.model = model
        self.api_config = get_api_config(provider)
        self.logger = get_logger(f"api.{provider}")
        self.task_id: Optional[str] = 'test'
    
    @abstractmethod
    async def chat_completion(
        self,
        messages: List[Dict[str, str]],
        # 在基类中使用更通用的 'tools'
        tools: Optional[List[Dict[str, Any]]] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """聊天完成接口"""
        pass


class OpenAICompatibleAdapter(BaseAPIAdapter):
    """OpenAI兼容的API适配器"""
    
    def __init__(self, provider: str, model: str, **kwargs):
        super().__init__(provider, model, **kwargs)
        
        self.client = openai.AsyncOpenAI(
            api_key=self.api_config.get("api_key"),
            base_url=self.api_config.get("base_url"),
            timeout=self.api_config.get("timeout", 60),
        )
    
    async def chat_completion(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
        tool_choice: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> Dict[str, Any]:
        debug_mode = kwargs.pop("debug", False)

        request_params = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "stream": False,
            "response_format": {"type": "json_object"},
            **kwargs
        }
        
        if max_tokens:
            request_params["max_tokens"] = max_tokens
        
        if tools:
            request_params["tools"] = tools
            request_params["tool_choice"] = tool_choice or "auto"

        if debug_mode:
            print(40 * "-", f"API请求参数 ({self.provider})", 40 * "-")
            pprint(request_params)

        try:            
            response = await self.client.chat.completions.create(**request_params)
            response = self._format_response(response)
            if debug_mode:
                print(40 * "-", f"API响应 ({self.provider})", 40 * "-")
                pprint(response)
            return response
        except Exception as e:
            self.logger.error(f"{self.provider} API请求失败: {str(e)}")
            raise APIError(f"API请求失败: {str(e)}")
    
    
    def _format_response(self, response) -> Dict[str, Any]:
        choice = response.choices[0]
        message = choice.message
        
        result = {
            "role": "assistant",
            "content": message.content,
            "tool_calls": None,
            "finish_reason": choice.finish_reason,
            "usage": {
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens
            }
        }
        
        if message.tool_calls:
            result["tool_calls"] = [
                {
                    "id": tool.id,
                    "type": "function",
                    "function": {
                        "name": tool.function.name,
                        "arguments": tool.function.arguments,
                    },
                }
                for tool in message.tool_calls
            ]
        return result


def create_api_adapter(provider: str, model: str, **kwargs) -> BaseAPIAdapter:
    """创建API适配器工厂函数"""
    provider_lower = provider.lower()
    
    if provider_lower in ["deepseek", "minimax", "openai", "zhipu"]:
        return OpenAICompatibleAdapter(provider, model, **kwargs)
    else:
        raise ValueError(f"不支持的API提供商: {provider}\n"
                         # 更新支持列表
                         f"当前支持的API提供商有：'deepseek', 'minimax', 'openai', 'zhipu'")