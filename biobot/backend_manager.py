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

from . import backends
import logging
import asyncio


logger = logging.getLogger(__name__)


class Backends:
    operations = {"joined": lambda x: x.get_joined_users, "bio": lambda x: x.get_bio_links}

    def __init__(self, config):
        self.config = config
        self.backends = []
        self.round_robin = []

    async def init(self):
        backend_config = self.config["backend"]
        common_config = self.config["common"]
        for module, config in backend_config.items():
            backend = getattr(backends, module)
            self.backends += backend.get_instances(common_config, config)
        self.round_robin = {k: self.backends.copy() for k in self.operations}
        # Initialise synchronously to make authentication easier
        for backend in self.backends:
            await backend.init()

    async def __aenter__(self):
        await self.init()
        return self

    async def close(self):
        del self.config
        del self.round_robin
        await asyncio.gather(*[backend.close() for backend in self.backends])
        del self.backends

    async def __aexit__(self, exc_type, exc, tb):
        await self.close()

    async def _with_retry(self, operation, *args, **kwargs):
        op = self.operations[operation]
        round_robin = self.round_robin[operation]
        backend = round_robin[0]
        while True:
            try:
                return await op(backend)(*args, **kwargs)
            except Exception:
                logger.warning("Failed to get %s", operation, exc_info=True)
            round_robin.remove(backend)
            round_robin.append(backend)
            backend = round_robin[0]
            await asyncio.sleep(0)  # Allow switching to a concurrent task

    async def get_joined_users(self):
        return await self._with_retry("joined")

    async def get_bio_links(self, uid, username):
        return await self._with_retry("bio", uid, username)
