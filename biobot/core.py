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

from . import chain, diff
from .user import FullUser
import asyncio
import networkx


async def get_bios(backend):
    if isinstance(backend, (chain.Forest, tuple, networkx.DiGraph)):
        return chain.make_graph(backend)
    users = await backend.get_joined_users()
    bios = await asyncio.gather(*[backend.get_bio_text(u) for u in users])
    full_users = [FullUser(user, bio) for user, bio in zip(users, bios)]
    return chain.make_graph(full_users)


async def get_chain(target, backend):
    graph = await get_bios(backend)
    return graph, chain.make_chain(graph, target)


async def get_notinchain(target, backend):
    graph = await get_bios(backend)
    return graph, chain.make_notinchain(graph, target)


async def get_chains(backend):
    graph = await get_bios(backend)
    return graph, chain.make_all_chains(graph)


async def get_diff(old, backend, *args, **kwargs):
    old = chain.make_graph(old)
    new = await get_bios(backend)
    return new, await asyncio.to_thread(diff.textual_chain_diff, old, new, *args, **kwargs)


async def get_gdiff(old, backend, *args, **kwargs):
    old = chain.make_graph(old)
    new = await get_bios(backend)
    return new, await asyncio.to_thread(diff.draw_chain_diff, old, new, *args, **kwargs)
