from ..agent_card import AgentCard
from ..utils.logger import get_logger

class Roster:
    def __init__(self):
        self.logger = get_logger("roster")
        self.cards = []

    def add_card(self, card: AgentCard):
        self.cards.append(card)

    def remove_card(self, card: AgentCard):
        self.cards.remove(card)

    @property
    def prompt(self) -> str:
        if not self.cards:
            return "当前没有可访问的Agent。"
        
        lines = ["当前可访问的Agent有：\n"]
        for card in self.cards:
            lines.append(f"- 名称：{card.name}  角色：{card.role}  描述：{card.description}\n")
        return "\n".join(lines)