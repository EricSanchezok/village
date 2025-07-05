from agents import Echoer, BrowserOperator
from core import AgentMessage

if __name__ == "__main__":
    import asyncio
    
    async def main():
        agent = Echoer()

        # 创建一个消息对象
        agent_message = AgentMessage.from_dict({
            'content': "帮我对比一下GPT4o和DeepseekV3的价格"
        })

        response = await agent.invoke(agent_message, debug=True)
        print(response)

    
    asyncio.run(main())