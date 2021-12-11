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

from .. import backends, utils
import telethon
import re


USERNAME_REGEX = re.compile(r'@[a-z][_0-9a-z]{4,31}', re.I)


class UserbotBackend(backends.Backend):
    def __init__(self, phone, api_id, api_hash, group_id, auth_key=None, test_dc=0):
        self.phone = phone
        self.group_id = utils.config_to_peer(group_id)
        self.auth_key = auth_key
        session = telethon.sessions.MemorySession() if not auth_key else telethon.sessions.StringSession(auth_key)
        if test_dc:
            session.set_dc(test_dc, "149.154.167.40", 80)
            self.login_code = str(test_dc) * 5
        else:
            self.login_code = None
        self.client = telethon.TelegramClient(session, api_id, api_hash, connection_retries=None)

    @classmethod
    def get_instances(cls, bot, common_config, configs):
        for config in configs:
            yield cls(**common_config, **config)

    async def init(self):
        if not self.auth_key:
            print(f"Signing in for {self.phone}")
        try:
            await self.client.start(self.phone, code_callback=self.login_code and (lambda: self.login_code) or (lambda: input(f"Enter login the code you received on {self.phone}: ")))
        except telethon.errors.AuthKeyDuplicatedError:
            print(f"Unable to sign in to {self.phone}")
            raise
        if not self.auth_key and not self.login_code:
            self.auth_key = telethon.sessions.StringSession.save(self.client.session)
            print(f"Please put '{self.auth_key}' as the auth_key for {self.phone} in the config.json")
        async for dialog in self.client.get_dialogs():
            if dialog.id == self.group_id:
                self.group = dialog.entity
                break
        assert isinstance(self.group, telethon._tl.Channel)
        self.client.flood_sleep_threshold = 0

    async def get_joined_users(self):
        ret = {}
        try:
            async for user in self.client.get_participants(self.group):
                ret[(user.id, user.username)] = {"deleted": user.deleted, "access_hash": user.access_hash}
        except telethon.errors.FloodWaitError as e:
            raise backends.Unavailable("Flood Wait", e.seconds)
        except telethon.errors.UserDeactivatedBanError:
            raise backends.Broken("User deactivated")
        except telethon.errors.AuthKeyDuplicatedError:
            raise backends.Broken("Auth key duplicated")
        return ret

    async def get_bio_links(self, uid, username):
        if isinstance(uid, int):
            user = telethon._tl.PeerUser(uid)
        else:
            user = uid
        try:
            full = await self.client(telethon._tl.fn.users.GetFullUser(user))
        except telethon.errors.FloodWaitError as e:
            raise backends.Unavailable("Flood Wait", e.seconds)
        except telethon.errors.UserDeactivatedBanError:
            raise backends.Broken("User deactivated")
        except telethon.errors.AuthKeyDuplicatedError:
            raise backends.Broken("Auth key duplicated")
        except ValueError:
            assert isinstance(uid, int), "Recursing ValueError clauses"
            members = await self.get_joined_users()
            try:
                user = telethon._tl.InputUser(uid, members[(uid, username)]["access_hash"])
            except KeyError:
                # either uid was already a Peer in which case we should fail to avoid infinite retries, or the user just isn't there, in which case they have effectively a blank bio
                return []
            return await self.get_bio_links(user, username)
        if full.user.username != username:
            raise backends.Unavailable("Usernames do not match.")
        if not full.about:
            return []
        return [x.group()[1:] for x in USERNAME_REGEX.finditer(full.about)]

    async def close(self):
        if self.client is not None:
            await self.client.disconnect()
            self.client = None
