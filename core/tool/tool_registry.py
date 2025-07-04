from .tool_base import ToolBase
from typing import Dict, Any, Optional, List


class ToolRegistry:
    def __init__(self):
        self.tools: Dict[str, ToolBase] = {}

    def register(self, tool: ToolBase):
        if tool.name in self.tools:
            raise ValueError(f"工具 '{tool.name}' 已经注册。")
        self.tools[tool.name] = tool

    def get_tool(self, name: str) -> Optional[ToolBase]:
        return self.tools.get(name)
    
    def get_tool_schemas(self) -> List[Dict[str, Any]]:
        return [tool.schema for tool in self.tools.values()]