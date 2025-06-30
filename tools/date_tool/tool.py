from datetime import datetime
from typing import Optional, Dict, Any
from core.tool import ToolBase, ToolRegistry

class DateTool(ToolBase):
    """获取当前日期时间工具"""
    
    def __init__(self):
        super().__init__(
            name="get_current_datetime",
            description="获取当前日期和时间。"
        )
    
    async def run(self, *args, **kwargs) -> Dict[str, Any]:
        """获取当前日期和时间"""
        current_datetime = datetime.now().isoformat()
        return {
            "current_datetime": current_datetime
        }