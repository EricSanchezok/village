from core import Swarm
from agents import Echoer, Coordinator, Planner, Coder, BrowserOperator
import asyncio

if __name__ == "__main__":
    swarm = Swarm()
    swarm.register_agent(Echoer())
    swarm.register_agent(Coordinator())
    swarm.register_agent(Planner())
    swarm.register_agent(Coder())
    swarm.register_agent(BrowserOperator())

    async def main():
        message = await swarm.invoke("请你分析一下你当前的项目结构，并且生成项目分析文档，并提出改进意见")
        print(message)

    asyncio.run(main())