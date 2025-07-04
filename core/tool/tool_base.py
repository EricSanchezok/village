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