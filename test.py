from agents import EchoAgent, TestAgent, BrowserAgent
from core.agent_message import AgentMessage

if __name__ == "__main__":
    import asyncio
    
    async def main():
        agent = TestAgent()

        # 创建一个消息对象
        agent_message = AgentMessage.from_dict({
            'content': "请查找当前系统时间"
        })

        response = await agent.invoke(agent_message, debug=True)
        print(response)

    
    asyncio.run(main())