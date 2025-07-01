from agents import EchoAgent, TestAgent
from core.agent_message import AgentMessage

if __name__ == "__main__":
    import asyncio
    
    async def main():
        agent = TestAgent()

        # 创建一个消息对象
        agent_message = AgentMessage.from_dict({
            'content': "帮我联网搜索搜索一下美国最近发生过什么事"
        })

        response = await agent.invoke(agent_message, debug=True)
    
    asyncio.run(main())