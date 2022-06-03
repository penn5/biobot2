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

from abc import abstractmethod, ABC
import re
import logging


USERNAME_REGEX = re.compile(r'@[a-z][_0-9a-z]{4,31}', re.I)
logger = logging.getLogger(__name__)


class Backend(ABC):
    def _setup_logging(self, name=None):
        full_name = type(self).__module__
        if name:
            full_name += "." + name
        self.logger = logging.getLogger(full_name)

    @classmethod
    @abstractmethod
    def get_instances(cls, common_config, configs):
        """Return an iterable of instances that implement Backend"""

    async def init(self):
        """Initialise the class"""

    async def close(self):
        """Prepare for destruction, this may be called multiple times"""


class JoinedUsersGetterBackend(Backend):
    @abstractmethod
    async def get_joined_users(self):
        """Fetch the users in the group, returning an iterable"""


class BioLinksGetterBackend(Backend):
    @abstractmethod
    async def get_bio_links(self, uid, username):
        """Return an iterable of usernames present in the bio, excluding the @"""

class BioTextGetterBackend(BioLinksGetterBackend):
    @abstractmethod
    async def get_bio_text(self, uid, username):
        """Return the user's bio text"""

    async def get_bio_links(self, uid, username):
        """Return an iterable of usernames present in the bio, excluding the @"""
        return [x.group()[1:] for x in USERNAME_REGEX.finditer(await self.get_bio_text(uid, username))]



class Unavailable(RuntimeError):
    def __init__(self, message, seconds=0, retry_elsewhere=False):
        super().__init__(message)
        self.seconds = seconds
        self.retry_elsewhere = retry_elsewhere


class Broken(RuntimeError):
    pass
