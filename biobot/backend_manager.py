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
from .backend import Unavailable, Broken, JoinedUsersGetterBackend, BioTextGetterBackend
import logging
import asyncio
import itertools


logger = logging.getLogger(__name__)


OP_JOINED = 0
OP_BIO = 1


class Backends:
    _operations = (
        (lambda x: x.get_joined_users, JoinedUsersGetterBackend),
        (lambda x: x.get_bio_text, BioTextGetterBackend),
    )
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
        self._tasks = [[] for _ in self._backends]
        results = await asyncio.gather(*[backend.init() for backend in self._backends], return_exceptions=True)
        for backend_i, backend in enumerate(self._backends):
            result = results[backend_i]
            if isinstance(result, Exception):
                backend.logger.error("Initialisation failed", exc_info=result)
                self._backends[backend_i] = None
                continue
            backend.logger.debug("Backend ID %d", backend_i)
            for operation_i, (operation, test_class) in enumerate(self._operations):
                if isinstance(backend, test_class):
                    self._tasks[backend_i].append(asyncio.create_task(self._act(operation, operation_i, backend, backend_i)))
        if all(backend is None for backend in self._backends):
            logger.critical("All backends failed to initialise")
            self._dead = True

    async def __aenter__(self):
        await self.init()
        return self

    async def close(self):
        if self._dead:
            return
        self._dead = True
        self._config = None
        await asyncio.gather(*[backend.close() for backend in self._backends if backend is not None])
        self._backends = None
        for task in itertools.chain.from_iterable(self._tasks):
            task.cancel()
        for task in itertools.chain.from_iterable(self._tasks):
            try:
                await task
            except asyncio.CancelledError:
                pass
            except BaseException as e:
                logger.exception("Failed to cancel %r", task)
        self._tasks.clear()
        for queue_i, queue in enumerate(self._queues):
            while True:
                try:
                    args, kwargs, fut, _, _ = queue.get_nowait()
                except asyncio.QueueEmpty:
                    break
                if not fut.done():
                    logger.debug("Aborting pending task on %d (%r, %r) for %r", queue_i, args, kwargs, fut)
                    fut.set_exception(RuntimeError("Shutting down"))
                else:
                    logger.debug("Ignoring done task on %d (%r, %r) for %r", queue_i, args, kwargs, fut)

    async def __aexit__(self, exc_type, exc, tb):
        await self.close()

    async def _close_backend(self, tasks, backend, backend_id):
        # must be shielded
        for task in tasks:
            task.cancel()
        for task in tasks:
            try:
                await task
            except asyncio.CancelledError:
                pass
            except BaseException as e:
                logger.exception("Failed to cancel %r", task)
        tasks.clear()
        if backend in self._backends:
            self._backends[backend_id] = None
            await backend.close()
            if all(backend is None for backend in self._backends):
                logger.critical("No more serviceable backends!")
                await self.close()

    async def _do(self, operation, *args, **kwargs):
        if self._dead:
            raise RuntimeError("No serviceable backends available!")
        return await self._put_queue(operation, args, kwargs)

    def get_joined_users(self):
        return self._do(OP_JOINED)

    def get_bio_text(self, user):
        return self._do(OP_BIO, user)

    async def _get_queue(self, operation):
        return await self._queues[operation].get()

    def _put_queue(self, operation, args, kwargs, fut=None, allowed_backends=None, retry_count=5):
        if fut is None:
            fut = asyncio.Future()
        if allowed_backends and all(self._backends[backend] is None for backend in allowed_backends):
            if retry_count:
                retry_count -= 1
                allowed_backends = None
                logger.warning("No backends remaining on %d (%r, %r) for %r, resetting (remaining %d)", operation, args, kwargs, fut, retry_count)
            else:
                logger.error("No backends remaining on %d (%r, %r) for %r, failing", operation, args, kwargs, fut)
                fut.set_exception(RuntimeError("No backends remaining"))
                return fut
        if allowed_backends is None:
            allowed_backends = set(range(len(self._backends)))
        self._queues[operation].put_nowait((args, kwargs, fut, allowed_backends, retry_count))
        return fut

    async def _act(self, operation, operation_i, backend, backend_id):
        op = operation(backend)
        while True:
            await asyncio.sleep(0)  # prevent a single actor hogging the thread
            args, kwargs, fut, allowed_backends, retry_count = await self._get_queue(operation_i)
            if backend_id not in allowed_backends:
                self._put_queue(operation_i, args, kwargs, fut, allowed_backends)
                continue
            try:
                backend.logger.debug("Starting %r %d", args, self.request_timeout)
                ret = await asyncio.wait_for(op(*args, **kwargs), timeout=self.request_timeout)
            except BaseException as e:
                if isinstance(e, Unavailable):
                    if e.retry_elsewhere:
                        allowed_backends.remove(backend_id)
                    backend.logger.debug("Unavailable on %d (%r, %r) for %r (next %r) (delay %d)", operation_i, args, kwargs, fut, allowed_backends, e.seconds)
                    self._put_queue(operation_i, args, kwargs, fut, allowed_backends, retry_count)
                    await asyncio.sleep(e.seconds)
                elif isinstance(e, asyncio.TimeoutError):
                    backend.logger.warning("Timed out on %d (%r, %r) for %r", operation_i, args, kwargs, fut)
                    self._put_queue(operation_i, args, kwargs, fut, allowed_backends, retry_count)
                elif isinstance(e, Broken):
                    backend.logger.exception("Broken on %d (%r, %r) for %r", operation_i, args, kwargs, fut)
                    logging.debug("Remaining backends: %r", self._backends)
                    self._put_queue(operation_i, args, kwargs, fut, allowed_backends, retry_count)
                    await asyncio.shield(self._close_backend(self._tasks[backend_id], backend, backend_id))
                    backend.logger.error("Failed actor %d was not cancelled", operation_i)
                    return
                elif isinstance(e, asyncio.CancelledError):
                    # actor cancelled, return to queue
                    self._put_queue(operation_i, args, kwargs, fut, allowed_backends, retry_count)
                    backend.logger.debug("Cancelled")
                    raise
                else:
                    backend.logger.debug("Exception on %d (%r, %r) for %r", operation_i, args, kwargs, fut)
                    fut.set_exception(e)
            else:
                backend.logger.debug("Success on %d (%r, %r) for %r", operation_i, args, kwargs, fut)
                fut.set_result(ret)
