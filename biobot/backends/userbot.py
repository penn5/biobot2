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

from .. import backends
import telethon
import re
import time


USERNAME_REGEX = re.compile(r'@[_0-9a-z]{5,32}')


class UserbotBackend(backends.Backend):
    def __init__(self, phone, api_id, api_hash, group_id, auth_key=None):
        self.phone = phone
        self.group_id = group_id
        self.auth_key = auth_key
        session = telethon.sessions.MemorySession() if not auth_key else telethon.sessions.StringSession(auth_key)
        self.client = telethon.TelegramClient(session, api_id, api_hash)
        self.waiting_until = [0, 0]

    @classmethod
    def get_instances(cls, common_config, configs):
        for config in configs:
            yield cls(**common_config, **config)

    async def init(self):
        if not self.auth_key:
            print(f"Signing in for {self.phone}")
        try:
            await self.client.start(self.phone)
        except telethon.errors.rpcerrorlist.AuthKeyDuplicatedError:
            print(f"Unable to sign in to {self.phone}")
            raise
        if not self.auth_key:
            self.auth_key = telethon.sessions.StringSession.save(self.client.session)
            print(f"Please put '{self.auth_key}' as the auth_key for {self.phone} in the config.json")
        async for dialog in self.client.iter_dialogs():
            if dialog.id == self.group_id:
                self.group = dialog.entity
                break
        assert isinstance(self.group, telethon.tl.types.Channel)
        self.client.flood_sleep_threshold = 0

    async def get_joined_users(self):
        if time.time() < self.waiting_until[0]:
            raise backends.Unavailable(f"Was flood-waited for {self.waiting_until[0] - time.time()}")
        ret = []
        try:
            async for user in self.client.iter_participants(self.group, aggressive=True):
                ret.append((user.id, user.username))
        except telethon.errors.FloodWaitError as fwe:
            self.waiting_until[1] = time.time() + fwe.seconds
            raise backends.Unavailable(f"Flood-waited for {fwe.seconds}")
        return ret

    async def get_bio_links(self, uid, username):
        if time.time() < self.waiting_until[1]:
            raise backends.Unavailable(f"Was flood-waited for {self.waiting_until[1] - time.time()}")
        try:
            full = await self.client(telethon.tl.functions.users.GetFullUserRequest(uid))
        except telethon.errors.FloodWaitError as fwe:
            self.waiting_until[1] = time.time() + fwe.seconds
            raise backends.Unavailable(f"Flood-waited for {fwe.seconds}")
        except ValueError:
            await self.get_joined_users()
            return await self.get_bio_links(uid, username)
        if full.user.username != username:
            raise backends.Unavailable("Usernames do not match.")
        if not full.about:
            return []
        return [x.group()[1:] for x in USERNAME_REGEX.finditer(full.about.lower())]

    async def close(self):
        await self.client.disconnect()
