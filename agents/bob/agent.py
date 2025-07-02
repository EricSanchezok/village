from core.agent import BaseAgent
from core.agent_message import AgentMessage
from core.tool import ToolRegistry, ToolBase
from tools import FileTool, ProjectTool
from browser_use import Agent, BrowserProfile, BrowserSession
from .chat_deepseek import ChatDeepSeek
import os
from core.config import load_config
from browser_use.agent.views import AgentHistoryList

from typing import Dict, Any
from pathlib import Path
import shutil

config = load_config()

class Bob(BaseAgent):
    def __init__(self):
        super().__init__(
            name="Bob",
            description=f"""
            我是Bob！我对村子外面的世界最好奇，脚程也最快。
            村里要是遇到什么难题，比如某个工具的用法搞不明白了，或者想知道别的地方是怎么解决类似问题的，尽管交给我。
            我能顺着信息的高速路（互联网）跑出去，帮你打听消息、查阅各种文献和资料，然后把最有用的情报带回来。
            需要任何来自村外的信息，我就是你的眼睛和耳朵。
            """,
            provider="deepseek",
            model="deepseek-reasoner",
            temperature=0.0,
            max_tokens=64000
        )

        self.project_root = Path(__file__).parent.parent.parent
        self.base_dir = self.project_root / ".data"

        shutil.rmtree(self.base_dir, ignore_errors=True)

        self.downloads_path = self.base_dir / "downloads"
        self.downloads_path.mkdir(parents=True, exist_ok=True)

        self.file_system_path = self.base_dir / "file_system"
        self.file_system_path.mkdir(parents=True, exist_ok=True)

        self.user_data_path = self.base_dir / "user_data"
        self.user_data_path.mkdir(parents=True, exist_ok=True)

        self.save_conversation_path = self.base_dir / f"{self.name}_internal_conversation"
        self.save_conversation_path.mkdir(parents=True, exist_ok=True)

        self.result_path = self.file_system_path / "browseruse_agent_data" / "results.md"
        self.result_path.parent.mkdir(parents=True, exist_ok=True)
        self.result_path.touch(exist_ok=True)

    def _build_messages(self, message: AgentMessage, agent_history: AgentHistoryList) -> Dict[str, Any]:
        # 读取
        with open(self.result_path, "r") as f:
            result = f.read()

        system_prompt = f"""
        {message.sender}给{message.receiver}发送了一条信息，{message.receiver}进行了思考总结并得出了结果。
        你的任务就是阅读{message.receiver}的思考历史，并分析{message.sender}的需求，然后阅读{message.receiver}的结果，
        并最终整理一份让{message.sender}满意的结果。
        注意：要严格按照{message.sender}的要求来，禁止输出额外的内容。
        """

        user_prompt = f"""
        {message.sender}的消息内容为{message.content},
        {message.receiver}的思考历史为{agent_history},
        {message.receiver}的思考结果为{result}
        """

        return [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
 
    async def invoke(self, agent_message: AgentMessage, **kwargs) -> str:
        """
        调用智能体的核心逻辑。
        子类需要实现这个方法。
        """

        browser_profile = BrowserProfile(
            user_data_dir=str(self.user_data_path),
            downloads_path=str(self.downloads_path),
            channel="chromium",
            chromium_sandbox=True,
            headless=True,
            ignore_default_args=["--disable-extensions"],
        )
        browser_session = BrowserSession(
            browser_profile=browser_profile
        )

        agent = Agent(
            file_system_path=str(self.file_system_path),
            use_vision=False,
            browser_session=browser_session,
            task=agent_message.content,
            llm=ChatDeepSeek(
                model="deepseek-chat",
                base_url=config.deepseek_base_url,
                api_key=config.deepseek_api_key
                ),
            save_conversation_path = str(self.save_conversation_path)
        )

        agent_history = await agent.run()

        response = await self.chat(
            messages=self._build_messages(agent_message, agent_history)
        )

        return response
    