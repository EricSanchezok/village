import asyncio
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional, AsyncGenerator, Union
from datetime import datetime
import json
from pprint import pprint

# 导入所有需要的库
import openai
import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold
from anthropic import AsyncAnthropic

import httpx

from ..config import get_api_config
from ..utils.logger import get_logger
from ..utils.exceptions import APIError

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
        # 在基类中使用更通用的 'tools'
        tools: Optional[List[Dict[str, Any]]] = None,
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

class GoogleGeminiAdapter(BaseAPIAdapter):
    """Google Gemini API 适配器"""

    def __init__(self, provider: str, model: str, **kwargs):
        super().__init__(provider, model, **kwargs)
        try:
            genai.configure(api_key=self.config.get("api_key"))
        except Exception as e:
            raise APIError(f"Google Gemini 配置失败: {e}")
        
        safety_settings = {
            HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
        }
        self.client = genai.GenerativeModel(self.model, safety_settings=safety_settings)

    # <--- 新增：递归更新 Schema 类型的辅助方法 --->
    def _recursively_update_schema_types(self, schema_dict: Dict[str, Any]):
        """
        递归遍历一个JSON Schema字典，将所有'type'字段的值转换为大写，以符合Gemini的要求。
        例如： "type": "string" -> "type": "STRING"
        """
        if not isinstance(schema_dict, dict):
            return

        # 转换当前层的type
        if "type" in schema_dict and isinstance(schema_dict["type"], str):
            schema_dict["type"] = schema_dict["type"].upper()

        # 递归处理 object 的 properties
        if "properties" in schema_dict and isinstance(schema_dict["properties"], dict):
            for prop_name in schema_dict["properties"]:
                self._recursively_update_schema_types(schema_dict["properties"][prop_name])

        # 递归处理 array 的 items
        if "items" in schema_dict and isinstance(schema_dict["items"], dict):
            self._recursively_update_schema_types(schema_dict["items"])

    # <--- 修改：更新工具转换方法以包含Schema类型转换 --->
    def _convert_tools(self, tools: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """将OpenAI兼容的工具格式转换为Gemini所需的格式，包括递归更新Schema类型。"""
        if not tools:
            return None
        
        gemini_tool_declarations = []
        for tool in tools:
            if tool.get("type") == "function" and "function" in tool:
                # 复制函数定义以避免修改原始对象
                func_decl = tool["function"].copy()
                
                # 如果存在参数定义，则递归更新其类型
                if "parameters" in func_decl and isinstance(func_decl["parameters"], dict):
                    self._recursively_update_schema_types(func_decl["parameters"])
                
                gemini_tool_declarations.append(func_decl)
        
        return gemini_tool_declarations

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

        generation_config = {
            "temperature": temperature,
        }
        if max_tokens:
            generation_config["max_output_tokens"] = max_tokens
        
        # 调用增强版的转换函数
        gemini_tools = self._convert_tools(tools) if tools else None

        tool_config = None
        if tool_choice and gemini_tools:
            if tool_choice == "auto":
                tool_config = {"function_calling_config": {"mode": "auto"}}
            elif tool_choice == "none":
                 tool_config = {"function_calling_config": {"mode": "none"}}
            elif tool_choice == "required" or tool_choice == "any":
                 tool_config = {"function_calling_config": {"mode": "any"}}
            elif isinstance(tool_choice, dict) and "function" in tool_choice:
                func_name = tool_choice["function"].get("name")
                if func_name:
                    tool_config = {
                        "function_calling_config": {
                            "mode": "any", 
                            "allowed_function_names": [func_name]
                        }
                    }

        gemini_messages = self._convert_messages(messages)
        
        request_params = {
            "contents": gemini_messages,
            "generation_config": genai.types.GenerationConfig(**generation_config),
            "tools": gemini_tools,
            "tool_config": tool_config
        }
        
        request_params = {k: v for k, v in request_params.items() if v is not None}

        self.logger.info(f"发送请求到 {self.provider}", extra={
            "model": self.model,
            "message_count": len(messages),
            "has_tools": bool(tools)
        })

        if debug_mode:
            print(40 * "-", f"API请求参数 ({self.provider})", 40 * "-")
            pprint(request_params)

        try:
            response = await self.client.generate_content_async(**request_params)
            formatted_response = self._format_response(response)
            
            if debug_mode:
                print(40 * "-", f"API响应 ({self.provider})", 40 * "-")
                pprint(formatted_response)
                
            return formatted_response
        except Exception as e:
            self.logger.error(f"{self.provider} API请求失败: {type(e).__name__} - {str(e)}")
            raise APIError(f"API请求失败: {str(e)}") from e

    # _convert_messages 和 _format_response 方法保持不变，这里省略以保持简洁
    # 请确保你保留了上一版中对这两个方法的正确实现
    def _convert_messages(self, messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """将标准消息格式转换为Gemini格式，特别是处理system角色的消息"""
        # (此方法保持不变)
        gemini_messages = []
        system_prompt = None
        for msg in messages:
            role = msg.get("role")
            content = msg.get("content")
            
            if role == "system":
                system_prompt = content
                continue
            
            gemini_role = "model" if role == "assistant" else "user"
            
            parts = []
            if system_prompt and gemini_role == "user" and not gemini_messages:
                parts.append({"text": f"{system_prompt}\n\n{content}"})
                system_prompt = None
            else:
                parts.append({"text": content})

            gemini_messages.append({"role": gemini_role, "parts": parts})
        
        if system_prompt:
             gemini_messages.append({"role": "user", "parts": [{"text": system_prompt}]})

        return gemini_messages

    def _format_response(self, response: genai.types.GenerateContentResponse) -> Dict[str, Any]:
        """将Gemini的响应格式化为标准格式"""
        # (此方法保持不变)
        choice = response.candidates[0]
        
        tool_calls = None
        content = None

        if choice.content.parts and hasattr(choice.content.parts[0], 'function_call') and choice.content.parts[0].function_call:
            tool_calls = []
            for part in choice.content.parts:
                if not hasattr(part, 'function_call'): continue
                
                fc = part.function_call
                arguments_dict = dict(fc.args)
                arguments_json_str = json.dumps(arguments_dict, ensure_ascii=False)

                tool_calls.append({
                    "id": f"call_{fc.name}_{abs(hash(arguments_json_str))}", 
                    "type": "function",
                    "function": {
                        "name": fc.name,
                        "arguments": arguments_json_str
                    }
                })
        else:
            try:
                content = response.text
            except ValueError:
                content = None

        usage = response.usage_metadata
        
        finish_reason = getattr(choice.finish_reason, 'name', 'UNKNOWN')

        return {
            "role": "assistant",
            "content": content,
            "tool_calls": tool_calls,
            "finish_reason": finish_reason,
            "usage": {
                "prompt_tokens": usage.prompt_token_count,
                "completion_tokens": usage.candidates_token_count,
                "total_tokens": usage.total_token_count
            }
        }


class SiliconflowAdapter(BaseAPIAdapter):
    """
    SiliconFlow API适配器 (基于httpx)
    """
    def __init__(self, provider: str, model: str, **kwargs):
        super().__init__(provider, model, **kwargs)
        self.client = httpx.AsyncClient(
            base_url=self.config.get("base_url"),
            headers={
                "Authorization": f"Bearer {self.config.get('api_key')}",
                "Content-Type": "application/json"
            },
            timeout=self.config.get("timeout", 120)
        )

    async def chat_completion(
        self,
        messages: List[Dict[str, Any]],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        # Siliconflow可能不支持工具，所以签名简化
        **kwargs
    ) -> Dict[str, Any]:
        """
        使用httpx调用SiliconFlow的聊天完成接口
        """
        debug_mode = kwargs.pop("debug", False)
        
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            **kwargs
        }
        if max_tokens:
            payload["max_tokens"] = max_tokens

        self.logger.info(f"发送请求到 {self.provider}", extra={
            "model": self.model,
            "message_count": len(messages)
        })

        if debug_mode:
            print(40 * "-", f"API请求参数 ({self.provider})", 40 * "-")
            pprint(payload)

        try:
            response = await self.client.post("/chat/completions", json=payload)
            response.raise_for_status() 
            
            response_data = response.json()
            formatted_response = self._format_response(response_data)

            if debug_mode:
                print(40 * "-", f"API响应 ({self.provider})", 40 * "-")
                pprint(formatted_response)
                
            return formatted_response

        except httpx.HTTPStatusError as e:
            self.logger.error(f"{self.provider} API请求失败: HTTP {e.response.status_code} - {e.response.text}")
            raise APIError(f"API请求失败: HTTP {e.response.status_code} - {e.response.text}")
        except Exception as e:
            self.logger.error(f"{self.provider} API请求失败: {str(e)}")
            raise APIError(f"API请求失败: {str(e)}")

    def _format_response(self, response: Dict[str, Any]) -> Dict[str, Any]:
        """
        将SiliconFlow的响应格式化为标准格式
        """
        choice = response.get("choices", [{}])[0]
        message = choice.get("message", {})
        usage = response.get("usage", {})

        return {
            "role": "assistant",
            "content": message.get("content"),
            "tool_calls": message.get("tool_calls"), 
            "finish_reason": choice.get("finish_reason"),
            "usage": {
                "prompt_tokens": usage.get("prompt_tokens"),
                "completion_tokens": usage.get("completion_tokens"),
                "total_tokens": usage.get("total_tokens")
            }
        }


def create_api_adapter(provider: str, model: str, **kwargs) -> BaseAPIAdapter:
    """创建API适配器工厂函数"""
    provider_lower = provider.lower()
    
    # 更新工厂函数以包含 google
    if provider_lower in ["deepseek", "minimax", "openai", "zhipu"]:
        return OpenAICompatibleAdapter(provider, model, **kwargs)
    elif provider_lower == "google":
        return GoogleGeminiAdapter(provider, model, **kwargs)
    elif provider_lower == "siliconflow":
        return SiliconflowAdapter(provider, model, **kwargs)
    else:
        raise ValueError(f"不支持的API提供商: {provider}\n"
                         # 更新支持列表
                         f"当前支持的API提供商有：'deepseek', 'minimax', 'openai', 'zhipu', 'google', 'siliconflow'")



if __name__ == "__main__":
    # 示例：如何使用API适配器
    async def main():
        print("--- 1. 测试 DeepSeek (OpenAI 兼容) ---")
        try:
            adapter_deepseek = create_api_adapter("deepseek", "deepseek-chat")
            messages_deepseek = [{"role": "user", "content": "你好，DeepSeek！"}]
            response_deepseek = await adapter_deepseek.chat_completion(messages_deepseek, debug=True)
            print("\n--- DeepSeek 最终结果 ---")
            pprint(response_deepseek)
        except Exception as e:
            print(f"\n调用DeepSeek失败: {e}")

        print("\n" + "="*80 + "\n")

        print("--- 2. 测试 SiliconFlow (HTTP) ---")
        try:
            adapter_siliconflow = create_api_adapter("siliconflow", "Qwen/Qwen2-7B-Instruct")
            messages_siliconflow = [{"role": "user", "content": "2025年中国大模型行业将面临哪些机遇与挑战？"}]
            response_siliconflow = await adapter_siliconflow.chat_completion(messages_siliconflow, debug=True)
            print("\n--- SiliconFlow 最终结果 ---")
            pprint(response_siliconflow)
        except Exception as e:
            print(f"\n调用SiliconFlow失败: {e}")

        print("\n" + "="*80 + "\n")

        # ================== 新增 Google Gemini 测试用例 ==================
        print("--- 3. 测试 Google Gemini (带工具使用) ---")
        try:
            adapter_google = create_api_adapter("google", "gemini-1.5-pro-latest")
            
            # 定义一个工具 (Function)
            weather_tool = {
                "type": "function",
                "function": {
                    "name": "get_current_weather",
                    "description": "获取指定地点的当前天气信息",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "location": {
                                "type": "string",
                                "description": "城市或地区，例如：北京",
                            },
                            "unit": {
                                "type": "string", 
                                "enum": ["celsius", "fahrenheit"]
                            },
                        },
                        "required": ["location"],
                    },
                }
            }

            messages_google = [{"role": "user", "content": "现在东京的天气怎么样？"}]
            
            response_google = await adapter_google.chat_completion(
                messages_google,
                tools=[weather_tool],
                tool_choice="auto", # 可以是 auto, none, 或强制指定
                debug=True
            )
            print("\n--- Google Gemini 最终结果 ---")
            pprint(response_google)

        except Exception as e:
            print(f"\n调用Google Gemini失败: {e}")

    asyncio.run(main())