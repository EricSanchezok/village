from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, Union, List, Type, Tuple


class ToolBase(ABC):
    def __init__(self, name: str, description: str, parameters: Optional[Dict[str, Any]] = None):
        self.name = name
        self.description = description
        self.parameters = parameters if parameters else {}

    @property
    def schema(self) -> Dict[str, Any]:
        """返回OpenAI函数调用格式的工具模式"""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self._parameters
            }
        }
    
    @property
    def _parameters(self) -> Dict[str, Any]:
        properties = {}
        required_params = []
        
        for param_name, (param_type, param_desc) in self.parameters.items():
            # 映射Python类型到JSON类型
            json_type = self._map_python_type(param_type)
            
            # 构建参数属性
            param_info = {
                "type": json_type,
                "description": param_desc
            }
            
            # 检查是否为可选类型（Union[Type, None]）
            if self._is_optional_type(param_type):
                # 对于可选参数，不添加到必需列表
                properties[param_name] = param_info
            else:
                properties[param_name] = param_info
                required_params.append(param_name)
        
        return {
            "type": "object",
            "properties": properties,
            "required": required_params
        }
    
    def _map_python_type(self, py_type: Type) -> str:
        """将Python类型映射为JSON Schema类型"""
        type_map = {
            int: "integer",
            float: "number",
            bool: "boolean",
            list: "array",
            dict: "object",
            tuple: "array",
            str: "string",
            Optional[str]: "string",
            Optional[int]: "integer",
            Optional[float]: "number",
            Optional[bool]: "boolean",
            Optional[list]: "array",
            Optional[dict]: "object",
        }
        
        # 处理Union类型
        if hasattr(py_type, '__origin__') and py_type.__origin__ is Union:
            # 检查Union中是否包含NoneType（即Optional）
            if type(None) in py_type.__args__:
                # 获取非None的类型
                non_none_types = [t for t in py_type.__args__ if t is not type(None)]
                if non_none_types:
                    return self._map_python_type(non_none_types[0])
        
        return type_map.get(py_type, "string")
    
    def _is_optional_type(self, py_type: Type) -> bool:
        """检查类型是否为可选类型（Union[Type, None]）"""
        if hasattr(py_type, '__origin__') and py_type.__origin__ is Union:
            return type(None) in py_type.__args__
        return False

    @abstractmethod
    async def run(self, *args, **kwargs) -> Any:
        """
        执行工具的核心逻辑。
        子类需要实现这个方法。
        """
        raise NotImplementedError("Subclasses should implement this method.")
    
    def __str__(self) -> str:
        """返回工具的字符串表示"""
        param_descs = []
        for param, (ptype, desc) in self.parameters.items():
            type_name = ptype.__name__ if hasattr(ptype, '__name__') else str(ptype)
            param_descs.append(f"{param} ({type_name}): {desc}")
        
        return f"Tool(name={self.name}, description={self.description}" + \
               (f"\nParameters:\n  " + "\n  ".join(param_descs) if param_descs else "") + \
               ")"
    

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
    
    def generate_tool_prompt(self) -> str:
        """生成工具描述文本，用于提示工程"""
        tool_descriptions = []
        for tool in self.tools.values():
            # 描述工具功能
            desc = f"- {tool.name}: {tool.description}"
            
            # 描述参数
            params = tool._get_parameters_schema()
            if params['properties']:
                param_list = []
                for param_name, param_info in params['properties'].items():
                    param_desc = f"{param_name} ({param_info['type']})"
                    if 'description' in param_info:
                        param_desc += f": {param_info['description']}"
                    param_list.append(param_desc)
                
                desc += f"\n  参数: {', '.join(param_list)}"
            
            tool_descriptions.append(desc)
        
        return "可用工具:\n" + "\n".join(tool_descriptions)