from .. import backends
import telethon
import re
import time
import asyncio


USERNAME_REGEX = re.compile(r'@[_0-9a-z]{5,32}')


class UserbotBackend(backends.Backend):
    def __init__(self, phone, api_id, api_hash, group_id, auth_key=None):
        self.phone = phone
        self.group_id = group_id
        self.auth_key = auth_key
        session = telethon.sessions.MemorySession() if auth_key is None else telethon.sessions.StringSession(auth_key)
        self.client = telethon.TelegramClient(session, api_id, api_hash)
        self.waiting_until = [0, 0]

    @classmethod
    def get_instances(cls, common_config, configs):
        for config in configs:
            yield cls(**common_config, **config)

    async def init(self):
        await self.client.start(self.phone)
        if self.auth_key is None:
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
