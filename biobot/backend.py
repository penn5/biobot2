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

from abc import abstractmethod


class Backend:
    @classmethod
    @abstractmethod
    def get_instances(cls, common_config, configs):
        """Return an iterable of instances that implement Backend"""

    async def init(self):
        """Initialise the class"""

    @abstractmethod
    async def get_joined_users(self):
        """Fetch the users in the group, returning an iterable"""
        raise Unavailable("Not implemented.")

    @abstractmethod
    async def get_bio_links(self, uid, username):
        """Return an iterable of usernames present in the bio, excluding the @"""

    async def close(self):
        """Prepare for destruction"""


class Unavailable(RuntimeError):
    pass
