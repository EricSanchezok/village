import os
from typing import Optional, Dict, Any
from dotenv import load_dotenv
from pydantic_settings import BaseSettings
from pydantic import Field


class Config(BaseSettings):
    """系统配置类"""
    
    # DeepSeek配置
    deepseek_api_key: Optional[str] = Field(env="DEEPSEEK_API_KEY")  # type: ignore
    deepseek_base_url: str = Field(default="https://api.deepseek.com", env="DEEPSEEK_BASE_URL")  # type: ignore
    
    # 智谱AI配置
    zhipu_api_key: Optional[str] = Field(env="ZHIPU_API_KEY")  # type: ignore
    zhipu_base_url: str = Field(default="https://open.bigmodel.cn/api/paas/v4", env="ZHIPU_BASE_URL")  # type: ignore
    
    # OpenAI配置
    openai_api_key: Optional[str] = Field(env="OPENAI_API_KEY")  # type: ignore
    openai_base_url: str = Field(default="https://api.openai.com/v1", env="OPENAI_BASE_URL")  # type: ignore
    
    # Google配置
    google_api_key: Optional[str] = Field(env="GOOGLE_API_KEY")  # type: ignore
    
    # Anthropic配置
    anthropic_api_key: Optional[str] = Field(env="ANTHROPIC_API_KEY")  # type: ignore

    # 硅基流动配置
    siliconflow_api_key: Optional[str] = Field(env="SILICONFLOW_API_KEY")  # type: ignore
    siliconflow_base_url: str = Field(default="https://api.siliconflow.cn/v1", env="SILICONFLOW_BASE_URL")  # type: ignore
    
    # 系统配置
    log_level: str = Field(default="INFO", env="LOG_LEVEL")  # type: ignore
    max_history_size: int = Field(default=1000, env="MAX_HISTORY_SIZE")  # type: ignore
    default_timeout: int = Field(default=30, env="DEFAULT_TIMEOUT")  # type: ignore
    browser_use_cloud_sync: bool = Field(default=False, env="BROWSER_USE_CLOUD_SYNC")  # type: ignore
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        

def load_config() -> Config:
    """加载配置"""
    # 加载.env文件
    load_dotenv()
    return Config()  # type: ignore


def get_api_config(provider: str) -> Dict[str, Any]:
    """获取指定提供商的API配置"""
    config = load_config()
    
    if provider.lower() == "deepseek":
        return {
            "api_key": config.deepseek_api_key,
            "base_url": config.deepseek_base_url,
            "timeout": config.default_timeout
        }
    elif provider.lower() == "zhipu":
        return {
            "api_key": config.zhipu_api_key,
            "base_url": config.zhipu_base_url,
            "timeout": config.default_timeout
        }
    elif provider.lower() == "openai":
        return {
            "api_key": config.openai_api_key,
            "base_url": config.openai_base_url,
            "timeout": config.default_timeout
        }
    elif provider.lower() == "google":
        return {
            "api_key": config.google_api_key,
            "timeout": config.default_timeout
        }
    elif provider.lower() == "anthropic":
        return {
            "api_key": config.anthropic_api_key,
            "timeout": config.default_timeout
        }
    else:
        raise ValueError(f"不支持的API提供商: {provider}")


# 全局配置实例
config = load_config()

