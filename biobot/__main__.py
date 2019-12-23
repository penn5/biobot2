#    Bio Bot (Telegram bot for managing the @Bio_Chain_2)
#    Copyright (C) 2019 Hackintosh Five

#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.

#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.

#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <https://www.gnu.org/licenses/>.

import logging
import asyncio
import json
from . import bot, backend_manager


logging.basicConfig(level=logging.ERROR)


async def main():
    config = json.load(open("config.json"))
    frontend = bot.BioBot(main_group=config["common"]["group_id"], **config["frontend"])
    await frontend.init()
    async with backend_manager.Backends(config) as backend:
        await frontend.run(backend)
    assert False


asyncio.run(main())
