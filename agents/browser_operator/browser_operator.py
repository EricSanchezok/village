from core import AgentBase, AgentMessage
from browser_use import Agent, BrowserProfile, BrowserSession
from .chat_deepseek import ChatDeepSeek
import os
from core import get_api_config
from browser_use.agent.views import AgentHistoryList

from typing import Dict, Any, Optional, List
from pathlib import Path
import shutil


class BrowserOperator(AgentBase):
    def __init__(self):
        super().__init__(
            provider="deepseek",
            model="deepseek-reasoner",
            temperature=0.0,
            max_tokens=64000
        )

        self.api_config = get_api_config("deepseek")

    def clear_data(self):
        self.project_root = Path(__file__).parent.parent.parent
        self.base_dir = self.project_root / ".data" / str(self.task_id) / str(self.card.name)

        shutil.rmtree(self.base_dir, ignore_errors=True)
        self.base_dir.mkdir(parents=True, exist_ok=True)

        self.downloads_path = self.base_dir / "downloads"
        self.downloads_path.mkdir(parents=True, exist_ok=True)

        self.file_system_path = self.base_dir / "file_system"
        self.file_system_path.mkdir(parents=True, exist_ok=True)

        self.user_data_path = self.base_dir / "user_data"
        self.user_data_path.mkdir(parents=True, exist_ok=True)

        self.save_conversation_path = self.base_dir / f"{self.card.name}_internal_conversation"
        self.save_conversation_path.mkdir(parents=True, exist_ok=True)

        self.result_path = self.file_system_path / "browseruse_agent_data" / "results.md"
        self.result_path.parent.mkdir(parents=True, exist_ok=True)
        self.result_path.touch(exist_ok=True)


    def _build_llm_messages(self, agent_message: AgentMessage, agent_history: AgentHistoryList) -> List[Dict[str, Any]]:
        return [
            {"role": "system", "content": self.system_prompt.format(
                agent_card=self.card,
                agent_message=agent_message,
                conversation_path=str(self.save_conversation_path)
            )},
            {"role": "user", "content": self.user_prompt.format(
                agent_message=agent_message,
                agent_history=agent_history,
                browser_result=self.result_path.read_text(),
                message_history=self.task.get_message_history() if self.task is not None else ""
            )}
        ]
 
    async def invoke(self, agent_message: AgentMessage, **kwargs) -> AgentMessage:
        self.clear_data()

        browser_profile = BrowserProfile(
            user_data_dir=str(self.user_data_path),
            downloads_path=str(self.downloads_path),
            chromium_sandbox=True,
            channel="chromium", # type: ignore
            headless=True,
            ignore_default_args=["--disable-extensions"],
        )
        browser_session = BrowserSession(
            browser_profile=browser_profile
        )

        browser_agent = Agent(
            file_system_path=str(self.file_system_path),
            use_vision=False,
            browser_session=browser_session,
            task=str(agent_message.content),
            llm=ChatDeepSeek(
                model="deepseek-chat",
                base_url=self.api_config.get("base_url"),
                api_key=self.api_config.get("api_key")
                ),
            save_conversation_path = str(self.save_conversation_path)
        )

        agent_history = await browser_agent.run()

        response = await self.chat(
            messages=self._build_llm_messages(agent_message, agent_history)
        )

        new_agent_message = AgentMessage(
            sender=str(self.card.name),
            receiver=agent_message.sender,
            content=response.get("content", ""),
            token_usage=response.get("usage", {}).get("total_tokens", 0),
            task_id=agent_message.task_id
        )

        return new_agent_message
    