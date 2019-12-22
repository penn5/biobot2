import logging


logging.basicConfig(level=logging.ERROR)


import asyncio
import json
from . import bot, backend_manager
import time

async def main():
    config = json.load(open("config.json"))
    frontend = bot.BioBot(main_group=config["common"]["group_id"], **config["frontend"])
    await frontend.init()
    async with backend_manager.Backends(config) as backend:
        await frontend.run(backend)
    assert False


asyncio.run(main())
