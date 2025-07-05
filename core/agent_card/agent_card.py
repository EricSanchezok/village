import yaml
from types import SimpleNamespace

class AgentCard:
    """
    一个用于加载和表示智能体配置卡片（Agent Card）的类。

    这个类会从一个 YAML 文件中读取智能体的配置信息，
    并将其转换为易于通过属性访问的对象结构。

    用法:
        card = AgentCard('path/to/your_agent.yaml')
        print(card.name)
        print(card.capabilities.skills)
    """

    def __init__(self, filepath: str):
        """
        初始化 AgentCard 实例。

        Args:
            filepath (str): agent card YAML 文件的路径。
        """
        self.filepath = filepath
        self.name = None
        self.role = None
        self.description = None
        try:
            # 加载并设置所有属性
            self._load_and_set_attrs()
        except FileNotFoundError:
            # 提供更明确的错误信息
            raise FileNotFoundError(f"AgentCard错误：找不到指定的配置文件 '{filepath}'")
        except yaml.YAMLError as e:
            # 捕获并重新抛出YAML解析错误
            raise yaml.YAMLError(f"解析YAML文件 '{filepath}' 时出错: {e}")

    def _load_and_set_attrs(self):
        """
        私有方法：打开并解析YAML文件，然后将内容递归地设置为类的属性。
        """
        with open(self.filepath, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
        
        # 递归地将加载的字典转换为对象的属性
        self._data_to_attributes(data)

    def _data_to_attributes(self, data: dict):
        """
        将字典的键值对转换成对象的属性。
        如果值是另一个字典，则递归地将其转换为一个可以用点访问的对象。
        """
        for key, value in data.items():
            if isinstance(value, dict):
                # 使用 SimpleNamespace 将嵌套的字典也变成可以用点访问的对象
                setattr(self, key, self._dict_to_simplenamespace(value))
            else:
                setattr(self, key, value)

    def _dict_to_simplenamespace(self, data: dict) -> SimpleNamespace:
        """
        一个辅助函数，递归地将字典及其嵌套字典转换为 SimpleNamespace 对象。
        """
        for key, value in data.items():
            if isinstance(value, dict):
                data[key] = self._dict_to_simplenamespace(value)
        return SimpleNamespace(**data)

    def __repr__(self) -> str:
        """
        返回一个官方的、可供开发者阅读的对象表示。
        """
        # 尝试获取name和role属性，如果不存在则使用None
        name = getattr(self, 'name', 'N/A')
        role = getattr(self, 'role', 'N/A')
        return f"AgentCard(name='{name}', role='{role}')"

    @property
    def prompt(self) -> str:
        """
        获取AgentCard的prompt
        """
        prompt = f"""
你是{self.name}，你的角色是{self.role}，你的描述是{self.description}
        """
        return prompt
