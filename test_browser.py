import os
import shutil
import asyncio
from pathlib import Path
from dotenv import load_dotenv
from browser_use import Agent, BrowserProfile, BrowserContext, BrowserSession, Browser, BrowserConfig
from browser_use.llm import ChatOpenAI

load_dotenv()

async def main():
    base_path = Path(".cache")
    shutil.rmtree(base_path, ignore_errors=True)

    user_data_dir = base_path / "user_data"
    user_data_dir.mkdir(parents=True, exist_ok=True)

    downloads_dir = base_path / "downloads"
    downloads_dir.mkdir(parents=True, exist_ok=True)

    file_system_dir = base_path / "file_system"
    file_system_dir.mkdir(parents=True, exist_ok=True)


    browser_profile = BrowserProfile(
        browser_type="chromium",
        user_data_dir=str(user_data_dir),
        downloads_path=str(downloads_dir),
        keep_alive=True,
        executable_path="C:\\Users\\Tel13\\AppData\\Local\\ms-playwright\\chromium-1179\\chrome-win\\chrome.exe"
    )


    browser_session = BrowserSession(browser_profile=browser_profile)
    
    agent = Agent(
        task="对比一下gpt-4o和DeepSeek-V3的价格",
        llm=ChatOpenAI(model="deepseek-chat"),
        browser_session=browser_session,
        use_vision=False,
        file_system_path=str(file_system_dir)
    )
    
    await agent.run()
    
    shutil.rmtree(base_path, ignore_errors=True)

if __name__ == "__main__":
    asyncio.run(main())