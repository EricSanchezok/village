import os
from typing import Optional, Dict, Any
from dotenv import load_dotenv
from pydantic_settings import BaseSettings
from pydantic import Field


class Config(BaseSettings):
    """系统配置类"""
    
    # DeepSeek配置
    deepseek_api_key: Optional[str] = Field(default=None, env="DEEPSEEK_API_KEY")  # type: ignore
    deepseek_base_url: str = Field(default="https://api.deepseek.com", env="DEEPSEEK_BASE_URL")  # type: ignore
    
    # 系统配置
    log_level: str = Field(default="INFO", env="LOG_LEVEL")  # type: ignore
    max_history_size: int = Field(default=1000, env="MAX_HISTORY_SIZE")  # type: ignore
    default_timeout: int = Field(default=30, env="DEFAULT_TIMEOUT")  # type: ignore
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"  # 忽略额外的环境变量
        

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
    else:
        raise ValueError(f"不支持的API提供商: {provider}")


# 全局配置实例
config = load_config()

