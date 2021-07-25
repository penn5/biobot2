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

from . import userbot

import telethon


class BotBackend(userbot.UserbotBackend):
    def __init__(self, bot, group_id, api_id, api_hash):
        self.token = bot if isinstance(bot, str) else None
        self.client = telethon.TelegramClient(telethon.sessions.MemorySession(), api_id, api_hash) if isinstance(bot, str) else bot
        self.group = group_id

    @classmethod
    def get_instances(cls, bot, common_config, configs):
        for config in configs:
            this_bot = config.pop("bot") or bot
            yield cls(this_bot, **config, **common_config)

    async def init(self):
        if self.token:
            await self.client.start(bot_token=self.token)
        self.client.flood_sleep_threshold = 0
