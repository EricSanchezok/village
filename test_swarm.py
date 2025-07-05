from core import Swarm
from agents import Echoer, Coordinator, Planner
import asyncio

if __name__ == "__main__":
    swarm = Swarm()
    swarm.register_agent(Echoer())
    swarm.register_agent(Coordinator())
    swarm.register_agent(Planner())


    async def main():
        message = await swarm.invoke("帮看一下当前系统时间")
        print(message)

    asyncio.run(main())