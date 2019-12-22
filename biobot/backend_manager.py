from . import backends, utils
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
        await asyncio.gather(*[backend.init() for backend in self.backends])

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
