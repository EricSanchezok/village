import google.generativeai as genai
from google.api_core.exceptions import GoogleAPICallError, ResourceExhausted
from google.generativeai.types import GenerationConfig, HarmCategory, HarmBlockThreshold
from google.generativeai.generative_models import GenerativeModel, ChatSession

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any, TypeVar, overload
import json

import httpx
from pydantic import BaseModel

from browser_use.llm.base import BaseChatModel
from browser_use.llm.exceptions import ModelProviderError
from browser_use.llm.messages import BaseMessage, AIMessage, HumanMessage, SystemMessage
from browser_use.llm.schema import SchemaOptimizer
from browser_use.llm.views import ChatInvokeCompletion, ChatInvokeUsage

T = TypeVar('T', bound=BaseModel)

@dataclass
class ChatGemini(BaseChatModel):
    """
    A wrapper around google.generativeai that implements the BaseChatModel protocol.

    This class mimics the structure of the original DeepSeek/OpenAI class but is adapted
    for the Google Gemini API. It accepts an api_key for configuration.
    """

    # Model configuration
    model: str  # e.g., 'gemini-1.5-pro-latest'

    # Model params
    temperature: float | None = None
    
    # Client initialization parameters - Kept for interface compatibility
    # Gemini SDK primarily uses an API key set via environment or genai.configure.
    api_key: str | None = None
    timeout: float | httpx.Timeout | None = None # Not directly applicable to genai SDK
    max_retries: int = 2 # Not directly applicable to genai SDK

    # Internal client, not meant to be initialized directly
    _model_client: GenerativeModel = field(init=False, repr=False)

    def __post_init__(self):
        """Configure the Gemini client after the object is created."""
        try:
            # The google-generativeai library will automatically use the
            # GOOGLE_API_KEY environment variable if api_key is not provided.
            if self.api_key:
                genai.configure(api_key=self.api_key)
        except Exception as e:
            raise ModelProviderError(f"Failed to configure Google Gemini: {e}") from e

    # Static
    @property
    def provider(self) -> str:
        return 'google'
    
    # This function is kept for structural consistency but is simplified for Gemini
    def _get_client_params(self) -> dict[str, Any]:
        """Prepare client parameters dictionary."""
        # Gemini's GenerativeModel takes generation_config for these params
        config = {}
        if self.temperature is not None:
            config['temperature'] = self.temperature
        
        return {
            "model_name": self.model,
            "generation_config": GenerationConfig(**config) if config else None,
            # Gemini has built-in safety settings which can be configured here if needed
            "safety_settings": {
                HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
            }
        }

    def get_model_client(self) -> GenerativeModel:
        """
        Returns a GenerativeModel client instance.
        """
        if not hasattr(self, '_model_client') or self._model_client.model_name != self.model:
            client_params = self._get_client_params()
            self._model_client = genai.GenerativeModel(**client_params)
        return self._model_client

    @property
    def name(self) -> str:
        return str(self.model)

    def _serialize_messages_for_gemini(self, messages: list[BaseMessage]) -> list[dict[str, Any]]:
        """
        Serializes a list of BaseMessage objects into the format expected by Gemini.
        Note: Gemini has a different role system ('user' and 'model'). System messages
        are handled as initial user messages.
        """
        gemini_messages = []
        system_prompt_parts = []

        for msg in messages:
            if isinstance(msg, SystemMessage):
                # Gemini doesn't have a dedicated 'system' role in the same way.
                # It's common practice to prepend system instructions to the first user message.
                system_prompt_parts.append(msg.content)
            elif isinstance(msg, HumanMessage):
                content = "\n\n".join(system_prompt_parts + [msg.content])
                gemini_messages.append({'role': 'user', 'parts': [content]})
                system_prompt_parts = [] # Clear after use
            elif isinstance(msg, AIMessage):
                # The 'assistant' role in OpenAI maps to 'model' in Gemini.
                gemini_messages.append({'role': 'model', 'parts': [msg.content]})
        
        # If there was a system prompt but no user message to attach it to
        if system_prompt_parts:
            gemini_messages.insert(0, {'role': 'user', 'parts': ["\n\n".join(system_prompt_parts)]})

        return gemini_messages


    def _get_usage(self, response: Any) -> ChatInvokeUsage | None:
        """Extract usage data from a Gemini response."""
        usage_metadata = getattr(response, 'usage_metadata', None)
        if usage_metadata:
            return ChatInvokeUsage(
                prompt_tokens=usage_metadata.prompt_token_count,
                prompt_cached_tokens=None,  # Not provided by Gemini
                prompt_cache_creation_tokens=None, # Not provided by Gemini
                prompt_image_tokens=None, # Needs specific logic if images are used
                completion_tokens=usage_metadata.candidates_token_count,
                total_tokens=usage_metadata.total_token_count,
            )
        return None

    @overload
    async def ainvoke(self, messages: list[BaseMessage], output_format: None = None) -> ChatInvokeCompletion[str]: ...

    @overload
    async def ainvoke(self, messages: list[BaseMessage], output_format: type[T]) -> ChatInvokeCompletion[T]: ...

    async def ainvoke(
        self, messages: list[BaseMessage], output_format: type[T] | None = None
    ) -> ChatInvokeCompletion[T] | ChatInvokeCompletion[str]:
        """
        Invoke the model with the given messages.

        Args:
            messages: List of chat messages
            output_format: Optional Pydantic model class for structured output

        Returns:
            Either a string response or an instance of output_format
        """
        gemini_messages = self._serialize_messages_for_gemini(messages)
        model_client = self.get_model_client()

        try:
            if output_format is None:
                # Return string response
                response = await model_client.generate_content_async(
                    gemini_messages
                )

                usage = self._get_usage(response)
                return ChatInvokeCompletion(
                    completion=response.text,
                    usage=usage,
                )

            else:
                # Prepare for structured (JSON) response
                schema = SchemaOptimizer.create_optimized_json_schema(output_format)
                
                # Instruct the model to produce JSON according to the schema.
                # This is more directive than just setting a response format.
                schema_prompt = f"""
Please provide a response in JSON format. The JSON object must strictly adhere to the following JSON Schema.
Do not include any other text or explanations outside of the JSON object.

JSON SCHEMA:
{json.dumps(schema)}
"""
                # Append the instruction to the last user message
                # Note: This is a robust way to ensure the instruction is seen last.
                if gemini_messages and gemini_messages[-1]['role'] == 'user':
                    gemini_messages[-1]['parts'].append(f"\n\n{schema_prompt}")
                else:
                    gemini_messages.append({'role': 'user', 'parts': [schema_prompt]})

                # Configure the client for JSON output
                json_generation_config = GenerationConfig(
                    temperature=self.temperature, 
                    response_mime_type="application/json"
                )
                
                response = await model_client.generate_content_async(
                    gemini_messages,
                    generation_config=json_generation_config
                )
                
                response_text = response.text
                if not response_text:
                    raise ModelProviderError(
                        message='Failed to parse structured output from model response (response was empty)',
                        model=self.name,
                    )
                
                usage = self._get_usage(response)
                parsed = output_format.model_validate_json(response_text)

                return ChatInvokeCompletion(
                    completion=parsed,
                    usage=usage,
                )

        except ResourceExhausted as e:
            # This is the equivalent of RateLimitError
            raise ModelProviderError(
                message=f"Rate limit exceeded: {e.message}",
                status_code=429, # Standard code for rate limiting
                model=self.name,
            ) from e

        except GoogleAPICallError as e:
            # This is a general error for API calls, similar to APIStatusError
            status_code = getattr(e, 'code', None) # Get gRPC status code if available
            raise ModelProviderError(
                message=f"Google API call failed: {e.message}",
                status_code=status_code,
                model=self.name,
            ) from e

        except Exception as e:
            # Catch any other unexpected errors, including JSON validation
            raise ModelProviderError(message=str(e), model=self.name) from e