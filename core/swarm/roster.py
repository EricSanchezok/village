from ..agent_card.agent_card import AgentCard
from ..utils.logger import get_logger
from typing import List, Dict, Optional, Any

class Roster:
    """智能体花名册，管理所有注册的智能体信息"""
    
    def __init__(self):
        self.logger = get_logger("roster")
        self.cards: List[AgentCard] = []
        self.agent_map: Dict[str, AgentCard] = {}  # 名称到卡片的映射

    def register_card(self, card: AgentCard):
        """注册智能体卡片"""
        if card.name and card.name in self.agent_map:
            self.logger.warning(f"智能体 {card.name} 已存在，将被覆盖")
            # 移除旧的卡片
            old_card = self.agent_map[card.name]
            if old_card in self.cards:
                self.cards.remove(old_card)
        
        self.cards.append(card)
        if card.name:
            self.agent_map[card.name] = card
        self.logger.info(f"智能体 {card.name} 已注册到花名册")

    def unregister_card(self, card: AgentCard):
        """取消注册智能体卡片"""
        if card.name and card.name in self.agent_map:
            del self.agent_map[card.name]
        
        if card in self.cards:
            self.cards.remove(card)
            self.logger.info(f"智能体 {card.name} 已从花名册中移除")

    def get_card(self, agent_name: str) -> Optional[AgentCard]:
        """根据名称获取智能体卡片"""
        return self.agent_map.get(agent_name)

    def get_all_cards(self) -> List[AgentCard]:
        """获取所有智能体卡片"""
        return self.cards.copy()

    def get_agent_names(self) -> List[str]:
        """获取所有智能体名称"""
        return list(self.agent_map.keys())

    def is_registered(self, agent_name: str) -> bool:
        """检查智能体是否已注册"""
        return agent_name in self.agent_map

    @property
    def prompt(self) -> str:
        """生成用于提示的智能体列表描述"""
        if not self.cards:
            return "当前没有可访问的智能体。"
        
        lines = ["当前可访问的智能体有：\n"]
        for i, card in enumerate(self.cards, 1):
            lines.append(f"{i}. 名称：{card.name}")
            lines.append(f"   角色：{card.role}")
            lines.append(f"   描述：{card.description}")
            lines.append("")  # 空行分隔
        
        return "\n".join(lines)

    def get_agents_by_role(self, role: str) -> List[AgentCard]:
        """根据角色获取智能体"""
        return [card for card in self.cards if card.role == role]

    def get_coordinator(self) -> Optional[AgentCard]:
        """获取协调者智能体"""
        coordinators = self.get_agents_by_role("coordinator")
        return coordinators[0] if coordinators else None

    def get_stats(self) -> Dict[str, Any]:
        """获取花名册统计信息"""
        roles: Dict[str, int] = {}
        for card in self.cards:
            if card.role:
                roles[card.role] = roles.get(card.role, 0) + 1
        
        return {
            "total_agents": len(self.cards),
            "roles": roles
        }