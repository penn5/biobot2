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
from ..user import User, FullUser
import telethon


class UserbotBackend(backends.JoinedUsersGetterBackend, backends.BioTextGetterBackend):
    def __init__(self, phone, api_id, api_hash, group_id, auth_key=None, test_dc=0):
        self._setup_logging(phone + "@" + str(test_dc))
        self.phone = phone
        self.group_id = group_id
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
            self.logger.info(f"Signing in")
        try:
            await self.client.start(self.phone, code_callback=self.login_code and (lambda: self.login_code) or (lambda: input(f"Enter login the code you received on {self.phone}: ")))
        except telethon.errors.rpcerrorlist.AuthKeyDuplicatedError:
            self.logger.error("Unable to sign in due to duplicate auth key")
            raise
        if not self.auth_key and not self.login_code:
            self.auth_key = telethon.sessions.StringSession.save(self.client.session)
            self.logger.info("Please put '%s' as the auth_key in the config.json", self.auth_key)
        async for dialog in self.client.iter_dialogs():
            if dialog.id == self.group_id:
                self.group = dialog.entity
                break
        assert isinstance(self.group, telethon.tl.types.Channel)
        self.client.flood_sleep_threshold = 0

    async def get_joined_users(self):
        ret = []
        try:
            async for user in self.client.iter_participants(self.group):
                usernames = [username.username for username in user.usernames] if user.usernames else []
                if user.username and user.username not in usernames:
                    usernames.insert(0, user.username)
                ret.append(User(user.id, usernames, user.deleted))
        except telethon.errors.rpcerrorlist.FloodWaitError as e:
            raise backends.Unavailable("Flood Wait", e.seconds)
        except telethon.errors.rpcerrorlist.UserDeactivatedBanError:
            raise backends.Broken("User deactivated/banned")
        except telethon.errors.rpcerrorlist.UserDeactivatedError:
            raise backends.Broken("User deactivated")
        except telethon.errors.rpcerrorlist.AuthKeyDuplicatedError:
            raise backends.Broken("Auth key duplicated")
        return ret

    async def get_bio_text(self, user, entity=None, allow_search=True):
        try:
            try:
                full = await self.client(telethon.tl.functions.users.GetFullUserRequest(entity or user.id))
            except ValueError:
                self.logger.debug("%r not cached", user)
                if user.usernames and allow_search:
                    username = user.usernames[0].casefold()
                    self.logger.debug("Searching for %s", username)
                    async for found_user in self.client.iter_participants(self.group, search=username):
                        if any(lambda found_username: found_username.username.casefold() == username, found_user.usernames):
                            break
                    else:
                        self.logger.debug("Didn't find user %s", username)
                        return ""
                elif user.uid and allow_search:
                    self.logger.debug("Fetching users")
                    async for found_user in self.client.iter_participants(self.group):
                        if found_user.uid == user.uid:
                            break
                    else:
                        raise backends.Unavailable("User not found in group by this userbot", retry_elsewhere=True)
                self.logger.debug("Fetching bio for %r", user)
                return await self.get_bio_text(user, found_user, False)
        except telethon.errors.rpcerrorlist.FloodWaitError as e:
            raise backends.Unavailable("Flood Wait", e.seconds)
        except telethon.errors.rpcerrorlist.UserDeactivatedBanError:
            raise backends.Broken("User deactivated/banned")
        except telethon.errors.rpcerrorlist.UserDeactivatedError:
            raise backends.Broken("User deactivated")
        except telethon.errors.rpcerrorlist.AuthKeyDuplicatedError:
            raise backends.Broken("Auth key duplicated")
        try:
            return full.full_user.about or ""
        except Exception as e:
            print("failed", e, full)

    async def close(self):
        if self.client is not None:
            await self.client.disconnect()
            self.client = None
