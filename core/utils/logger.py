"""
日志管理模块
提供统一的日志记录功能，支持中文无乱码输出
"""

import logging
import sys
import os
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime
import structlog
from rich.logging import RichHandler
from rich.console import Console
from collections import OrderedDict

from ..config import config


class UTF8StreamHandler(logging.StreamHandler):
    """支持UTF-8编码的流处理器"""
    
    def __init__(self, stream=None):
        super().__init__(stream)
        # 确保输出流支持UTF-8编码
        if hasattr(self.stream, 'reconfigure'):
            try:
                self.stream.reconfigure(encoding='utf-8', errors='replace')
            except Exception:
                pass


class UTF8FileHandler(logging.FileHandler):
    """支持UTF-8编码的文件处理器"""
    
    def __init__(self, filename, mode='a', encoding='utf-8', delay=False, errors='replace'):
        super().__init__(filename, mode, encoding, delay, errors)

def order_keys_processor(logger, method_name, event_dict):
    """
    自定义的structlog处理器，用于对日志字典的键进行排序。
    """
    # 期望顺序
    key_order = ['timestamp', 'logger', 'level', 'event']
    
    # 使用OrderedDict来保证顺序
    ordered_event_dict = OrderedDict()
    
    # 优先放入指定顺序的键
    for key in key_order:
        if key in event_dict:
            ordered_event_dict[key] = event_dict.pop(key)
            
    # 将剩余的键按字母顺序追加到后面
    for key in sorted(event_dict.keys()):
        ordered_event_dict[key] = event_dict[key]
        
    return ordered_event_dict


def setup_console_encoding():
    """设置控制台编码为UTF-8"""
    try:
        # 设置标准输出编码
        if hasattr(sys.stdout, 'reconfigure'):
            sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        if hasattr(sys.stderr, 'reconfigure'):
            sys.stderr.reconfigure(encoding='utf-8', errors='replace')
        
        # 设置环境变量
        os.environ.setdefault('PYTHONIOENCODING', 'utf-8')
        
    except Exception as e:
        print(f"Warning: Could not set console encoding: {e}")


def create_utf8_formatter() -> logging.Formatter:
    """创建支持UTF-8的格式化器"""
    return logging.Formatter(
        fmt='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )


def setup_logging(
    log_level: Optional[str] = None,
    log_file: Optional[str] = None,
    enable_rich: bool = True,
    enable_file_logging: bool = True
) -> structlog.stdlib.BoundLogger:
    """
    设置日志系统，支持中文无乱码输出
    
    Args:
        log_level: 日志级别
        log_file: 日志文件路径
        enable_rich: 是否启用Rich格式化
        enable_file_logging: 是否启用文件日志
    
    Returns:
        配置好的logger
    """
    # 设置控制台编码
    setup_console_encoding()
    
    # 设置日志级别
    level = log_level or config.log_level
    log_level_num = getattr(logging, level.upper(), logging.INFO)
    
    # 配置structlog处理器
    processors = [
        structlog.processors.TimeStamper(fmt="iso", key="timestamp"),
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        # structlog.stdlib.filter_by_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        
        order_keys_processor,
    ]
    
    # 根据输出方式选择不同的渲染器
    if enable_rich:
        # Rich输出使用JSONRenderer
        processors.append(structlog.processors.JSONRenderer(ensure_ascii=False))
    else:
        # 普通输出使用KeyValueRenderer，确保中文正确显示
        processors.append(structlog.processors.KeyValueRenderer(
            key_order=['timestamp', 'level', 'event'],
            drop_missing=True
        ))
    
    structlog.configure(
        processors=processors,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )
    
    # 获取根logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level_num)
    
    # 清除现有handlers
    root_logger.handlers.clear()
    
    # 添加控制台handler
    if enable_rich:
        # 创建支持中文的Rich控制台
        console = Console(
            force_terminal=True,
            force_interactive=False,
            color_system="auto",
            legacy_windows=False,
            file=sys.stdout
        )
        
        console_handler = RichHandler(
            console=console,
            show_time=True,
            show_path=True,
            markup=True,
            rich_tracebacks=True,
            show_level=True,
            enable_link_path=False,  # 避免路径链接问题
            locals_max_length=10,
            locals_max_string=80
        )
        console_handler.setLevel(log_level_num)
    else:
        # 使用UTF-8流处理器
        console_handler = UTF8StreamHandler(sys.stdout)
        console_handler.setFormatter(create_utf8_formatter())
        console_handler.setLevel(log_level_num)
    
    root_logger.addHandler(console_handler)
    
    # 添加文件handler
    if enable_file_logging and log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        file_handler = UTF8FileHandler(
            filename=str(log_path),
            mode='a',
            encoding='utf-8',
            errors='replace'
        )
        file_handler.setFormatter(create_utf8_formatter())
        file_handler.setLevel(log_level_num)
        root_logger.addHandler(file_handler)
    
    return structlog.get_logger()


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    """获取指定名称的logger"""
    return structlog.get_logger(name)


def get_agent_logger(agent_id: str) -> structlog.stdlib.BoundLogger:
    """获取智能体专用logger，支持中文输出"""
    log_file = f"logs/agent_logs/agent_{agent_id}_{datetime.now().strftime('%Y%m%d')}.log"
    logger = get_logger(f"agent.{agent_id}")
    
    # 为智能体添加专用文件handler
    agent_logger = logging.getLogger(f"agent.{agent_id}")
    
    # 检查是否已经有文件handler
    has_file_handler = any(
        isinstance(handler, (logging.FileHandler, UTF8FileHandler)) 
        and getattr(handler, 'baseFilename', '').endswith(log_file.split('/')[-1])
        for handler in agent_logger.handlers
    )
    
    if not has_file_handler:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        file_handler = UTF8FileHandler(
            filename=str(log_path),
            mode='a',
            encoding='utf-8',
            errors='replace'
        )
        file_handler.setFormatter(create_utf8_formatter())
        file_handler.setLevel(logging.INFO)
        agent_logger.addHandler(file_handler)
    
    return logger


def get_swarm_logger(swarm_id: str) -> structlog.stdlib.BoundLogger:
    """获取Swarm专用logger，支持中文输出"""
    log_file = f"logs/swarm_logs/swarm_{swarm_id}_{datetime.now().strftime('%Y%m%d')}.log"
    logger = get_logger(f"swarm.{swarm_id}")
    
    # 为Swarm添加专用文件handler
    swarm_logger = logging.getLogger(f"swarm.{swarm_id}")
    
    # 检查是否已经有文件handler
    has_file_handler = any(
        isinstance(handler, (logging.FileHandler, UTF8FileHandler))
        and getattr(handler, 'baseFilename', '').endswith(log_file.split('/')[-1])
        for handler in swarm_logger.handlers
    )
    
    if not has_file_handler:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        file_handler = UTF8FileHandler(
            filename=str(log_path),
            mode='a',
            encoding='utf-8',
            errors='replace'
        )
        file_handler.setFormatter(create_utf8_formatter())
        file_handler.setLevel(logging.INFO)
        swarm_logger.addHandler(file_handler)
    
    return logger


def create_simple_logger(
    name: str,
    level: str = "INFO",
    log_file: Optional[str] = None,
    enable_console: bool = True
) -> logging.Logger:
    """
    创建简单的Python标准logger，确保中文正确显示
    
    Args:
        name: logger名称
        level: 日志级别
        log_file: 日志文件路径
        enable_console: 是否启用控制台输出
    
    Returns:
        配置好的logger
    """
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, level.upper(), logging.INFO))
    
    # 避免重复添加handler
    if logger.handlers:
        return logger
    
    formatter = create_utf8_formatter()
    
    # 控制台handler
    if enable_console:
        console_handler = UTF8StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
    
    # 文件handler
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        file_handler = UTF8FileHandler(
            filename=str(log_path),
            mode='a',
            encoding='utf-8',
            errors='replace'
        )
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    return logger


def test_chinese_logging():
    """测试中文日志输出"""
    logger = get_logger("test")
    
    test_messages = [
        "这是一条中文测试消息",
        "包含特殊字符：你好世界！@#￥%……&*（）",
        "English and 中文 mixed message",
        "数字和中文：123 个智能体正在运行",
        "错误信息：文件未找到 - 请检查路径是否正确"
    ]
    
    print("=== 中文日志测试 ===")
    for i, msg in enumerate(test_messages, 1):
        logger.info(f"测试消息 {i}", message=msg)
    
    print("=== 测试完成 ===")


# 初始化默认logger
try:
    default_logger = setup_logging()
except Exception as e:
    print(f"Warning: Failed to setup logging: {e}")
    # 创建一个简单的fallback logger
    default_logger = create_simple_logger("fallback")


# 导出主要函数
__all__ = [
    'setup_logging',
    'get_logger', 
    'get_agent_logger',
    'get_swarm_logger',
    'create_simple_logger',
    'test_chinese_logging',
    'default_logger'
]


if __name__ == "__main__":
    # 运行中文日志测试
    test_chinese_logging()

