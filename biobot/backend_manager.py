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
from .backend import Unavailable, Broken
import logging
import asyncio
import itertools


logger = logging.getLogger(__name__)


OP_JOINED = 0
OP_BIO = 1


class Backends:
    _operations = [lambda x: x.get_joined_users, lambda x: x.get_bio_links]
    request_timeout = 10.0

    def __init__(self, config, bot):
        self._dead = False
        self._config = config
        self._bot = bot
        self._backends = []
        self._tasks = []
        self._queues = [asyncio.Queue() for _ in self._operations]

    async def init(self):
        backend_config = self._config["backend"]
        common_config = self._config["common"]
        for module, config in backend_config.items():
            backend = getattr(backends, module)
            self._backends += backend.get_instances(self._bot, common_config, config)
        # Initialise synchronously to make authentication easier
        for i, backend in enumerate(self._backends):
            await backend.init()
            self._tasks.append([])
            for operation in range(len(self._operations)):
                self._tasks[i].append(asyncio.create_task(self._act(operation, backend, i)))

    async def __aenter__(self):
        await self.init()
        return self

    async def close(self):
        if self._dead:
            return
        self._dead = True
        self._config = None
        await asyncio.gather(*[backend.close() for backend in self._backends])
        self._backends = None
        for task in itertools.chain.from_iterable(self._tasks):
            task.cancel()
        for task in itertools.chain.from_iterable(self._tasks):
            try:
                await task
            except asyncio.CancelledError:
                pass
            except BaseException as e:
                logging.error("Failed to cancel %r", task)
        self._tasks.clear()
        for queue in self._queues:
            while True:
                try:
                    _, _, fut = queue.get_nowait()
                except asyncio.QueueEmpty:
                    break
                fut.set_exception(RuntimeError("Shutting down"))

    async def __aexit__(self, exc_type, exc, tb):
        await self.close()

    async def _do(self, operation, *args, **kwargs):
        if self._dead:
            raise RuntimeError("No serviceable backends available!")
        return await (await self._put_queue(operation, args, kwargs))

    def get_joined_users(self):
        return self._do(OP_JOINED)

    def get_bio_links(self, uid, username):
        return self._do(OP_BIO, uid, username)

    async def _get_queue(self, operation):
        return await self._queues[operation].get()

    async def _put_queue(self, operation, args, kwargs, fut=None):
        if fut is None:
            fut = asyncio.Future()
        await self._queues[operation].put((args, kwargs, fut))
        return fut

    async def _act(self, operation, backend, backend_id):
        op = self._operations[operation](backend)
        while True:
            args, kwargs, fut = await self._get_queue(operation)
            try:
                ret = await asyncio.wait_for(op(*args, **kwargs), timeout=self.request_timeout)
            except BaseException as e:
                if isinstance(e, Unavailable) or isinstance(e, asyncio.TimeoutError):
                    if isinstance(e, asyncio.TimeoutError):
                        logging.warning("Backend %r timed out on %d (%r, %r) for %r", backend, operation, args, kwargs, fut)
                    await self._put_queue(operation, args, kwargs, fut)
                    await asyncio.sleep(e.seconds)
                elif isinstance(e, Broken):
                    logging.exception("Backend %r broken on %d (%r, %r) for %r", backend, operation, args, kwargs, fut)
                    await self._put_queue(operation, args, kwargs, fut)
                    self._tasks[backend_id].clear()
                    if all(not task for task in self._tasks):
                        logging.critical("No more backends serviceable!")
                        await self.close()
                    else:
                        await asyncio.shield(backend.close())
                    return  # give up.
                else:
                    fut.set_exception(e)
                    if isinstance(e, asyncio.CancelledError):
                        raise
            else:
                fut.set_result(ret)
