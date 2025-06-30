from agents import EchoAgent, TestAgent
from core.agent_message import AgentMessage

if __name__ == "__main__":
    import asyncio
    
    async def main():
        agent = TestAgent()

        # 创建一个消息对象
        agent_message = AgentMessage.from_dict({
            'content': "你能够分析一下当前的项目的代码结构，并挑选一个代码文件进行分析吗？"
        })

        response = await agent.invoke(agent_message, debug=True)
    
    asyncio.run(main())