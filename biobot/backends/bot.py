#    Bio Bot (Telegram bot for managing the @Bio_Chain_2)
#    Copyright (C) 2022 Hackintosh Five

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

import telethon

from . import userbot


class BotBackend(userbot.UserbotBackend):
    # noinspection PyMissingConstructor
    def __init__(self, bot, group_id, api_id, api_hash):
        self.token = bot if isinstance(bot, str) else None
        self._setup_logging((self.token or "<bot>").partition(":")[0])
        self.client = (
            telethon.TelegramClient(telethon.sessions.MemorySession(), api_id, api_hash)
            if isinstance(bot, str)
            else bot
        )
        self.group = group_id

    @classmethod
    def get_instances(cls, bot, common_config, configs):
        for config in configs:
            this_bot = config.pop("bot") or bot
            yield cls(this_bot, **config, **common_config)

    async def init(self):
        if self.token:
            try:
                await self.client.start(bot_token=self.token)
            except telethon.errors.rpcerrorlist.AccessTokenExpiredError:
                self.logger.error("Bot token expired: %s", self.token.split(":")[0])
                raise
        self.client.flood_sleep_threshold = 0

    async def close(self):
        if self.token:
            await super().close()
        # else we're borrowing the bot and mustn't disconnect
