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

import logging
from abc import ABC, abstractmethod
from typing import Iterable

import telethon

from biobot.user import User

logger = logging.getLogger(__name__)


class Backend(ABC):
    def _setup_logging(self, name: str = None):
        full_name = type(self).__module__
        if name:
            full_name += "." + name
        self.logger = logging.getLogger(full_name)

    @classmethod
    @abstractmethod
    def get_instances(
        cls, bot: telethon.TelegramClient, common_config: dict, configs: list[dict]
    ) -> Iterable["Backend"]:
        """Return an iterable of instances that implement Backend"""

    async def init(self):
        """Initialise the class"""

    async def close(self):
        """Prepare for destruction, this may be called multiple times"""


class JoinedUsersGetterBackend(Backend):
    @abstractmethod
    async def get_joined_users(self) -> Iterable[User]:
        """Fetch the users in the group, returning an iterable"""


class BioTextGetterBackend(Backend):
    @abstractmethod
    async def get_bio_text(self, user: User) -> str:
        """Return the user's bio text"""


class Unavailable(RuntimeError):
    def __init__(self, message: str, seconds: float = 0, retry_elsewhere: bool = False):
        super().__init__(message)
        self.seconds = seconds
        self.retry_elsewhere = retry_elsewhere


class Broken(RuntimeError):
    pass
