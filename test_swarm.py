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
        message = await swarm.invoke("帮我写一段python代码能够实现贪吃蛇游戏")
        print(message)

    asyncio.run(main())