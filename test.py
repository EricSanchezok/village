from agents import EchoAgent, TestAgent, BrowserAgent
from core.agent_message import AgentMessage

if __name__ == "__main__":
    import asyncio
    
    async def main():
        agent = EchoAgent()

        # 创建一个消息对象
        agent_message = AgentMessage.from_dict({
            'content': "本我深度调研一下强生公司在心脏内超声动态三维重建方面做到什么程度了。”"
        })

        response = await agent.invoke(agent_message, debug=True)
        print(response)

    
    asyncio.run(main())