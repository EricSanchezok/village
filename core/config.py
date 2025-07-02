import os
from typing import Optional, Dict, Any
from dotenv import load_dotenv
from pydantic_settings import BaseSettings
from pydantic import Field


class Config(BaseSettings):
    """系统配置类"""
    
    # DeepSeek配置
    deepseek_api_key: Optional[str] = Field(None, env="DEEPSEEK_API_KEY")
    deepseek_base_url: str = Field("https://api.deepseek.com", env="DEEPSEEK_BASE_URL")
    
    # 智谱AI配置
    zhipu_api_key: Optional[str] = Field(None, env="ZHIPU_API_KEY")
    zhipu_base_url: str = Field("https://open.bigmodel.cn/api/paas/v4", env="ZHIPU_BASE_URL")
    
    # OpenAI配置
    openai_api_key: Optional[str] = Field(None, env="OPENAI_API_KEY")
    openai_base_url: str = Field("https://api.openai.com/v1", env="OPENAI_BASE_URL")
    
    # Google配置
    google_api_key: Optional[str] = Field(None, env="GOOGLE_API_KEY")
    
    # Anthropic配置
    anthropic_api_key: Optional[str] = Field(None, env="ANTHROPIC_API_KEY")

    # 硅基流动配置
    siliconflow_api_key: Optional[str] = Field(None, env="SILICONFLOW_API_KEY")
    siliconflow_base_url: str = Field("https://api.siliconflow.cn/v1", env="SILICONFLOW_BASE_URL")
    
    # 系统配置
    log_level: str = Field("INFO", env="LOG_LEVEL")
    max_history_size: int = Field(1000, env="MAX_HISTORY_SIZE")
    default_timeout: int = Field(30, env="DEFAULT_TIMEOUT")
    browser_use_cloud_sync: bool = Field(False, env="BROWSER_USE_CLOUD_SYNC")
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        

def load_config() -> Config:
    """加载配置"""
    # 加载.env文件
    load_dotenv()
    return Config()


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
    elif provider.lower() == "siliconflow":
        return {
            "api_key": config.siliconflow_api_key,
            "base_url": config.siliconflow_base_url,
            "timeout": config.default_timeout
        }
    else:
        raise ValueError(f"不支持的API提供商: {provider}")


# 全局配置实例
config = load_config()

