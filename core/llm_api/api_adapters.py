import asyncio
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional, AsyncGenerator, Union
from datetime import datetime
import json
from pprint import pprint

import openai
import google.generativeai as genai
from anthropic import AsyncAnthropic

import httpx
from ..config import get_api_config
from ..utils.logger import get_logger

from ..utils.exceptions import APIError

logger = get_logger(__name__)


class BaseAPIAdapter(ABC):
    """API适配器基类"""
    
    def __init__(self, provider: str, model: str, **kwargs):
        self.provider = provider
        self.model = model
        self.config = get_api_config(provider)
        self.logger = get_logger(f"api.{provider}")
    
    @abstractmethod
    async def chat_completion(
        self,
        messages: List[Dict[str, str]],
        functions: Optional[List[Dict[str, Any]]] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> Union[Dict[str, Any], AsyncGenerator[Dict[str, Any], None]]:
        """聊天完成接口"""
        pass


class OpenAICompatibleAdapter(BaseAPIAdapter):
    """OpenAI兼容的API适配器"""
    
    def __init__(self, provider: str, model: str, **kwargs):
        super().__init__(provider, model, **kwargs)
        
        self.client = openai.AsyncOpenAI(
            api_key=self.config.get("api_key"),
            base_url=self.config.get("base_url"),
            timeout=self.config.get("timeout", 60),
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
            **kwargs
        }
        
        if max_tokens:
            request_params["max_tokens"] = max_tokens
        
        if tools:
            request_params["tools"] = tools
            request_params["tool_choice"] = tool_choice or "auto"
        
        self.logger.info(f"发送请求到{self.provider}", extra={
            "model": self.model,
            "message_count": len(messages),
            "has_tools": bool(tools)
        })

        if debug_mode:
            print(40 * "-", "API请求参数", 40 * "-")
            pprint(request_params)

        try:            
            response = await self.client.chat.completions.create(**request_params)
            response = self._format_response(response)
            if debug_mode:
                print(40 * "-", "API响应", 40 * "-")
                pprint(response)
            return response
        except Exception as e:
            raise APIError(f"API请求失败: {str(e)}")
    
    
    def _format_response(self, response: openai.types.chat.ChatCompletion) -> Dict[str, Any]:
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
        raise ValueError(f"不支持的API提供商: {provider}\
                         当前支持的API提供商有：'deepseek', 'minimax', 'openai', 'zhipu'")



if __name__ == "__main__":
    # 示例：如何使用API适配器
    async def main():
        adapter = create_api_adapter("deepseek", "deepseek-chat")
        messages = [{"role": "user", "content": "Hello, world!"}]
        
        response = await adapter.chat_completion(messages)
        print(response)
    
    asyncio.run(main())