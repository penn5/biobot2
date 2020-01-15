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
import asyncio


async def get_bios(backend):
    if isinstance(backend, chain.Forest):
        return backend
    users = await backend.get_joined_users()
    ret = await asyncio.gather(*[backend.get_bio_links(*u) for u in users])
    return dict(zip(users, ret))


async def get_chain(target, backend):
    return chain.make_chain(await get_bios(backend), target)


async def get_chains(backend):
    return chain.make_all_chains(await get_bios(backend))

async def get_diff(old, backend):
    if not isinstance(old, chain.Forest):
        raise TypeError("old should be a Backend")
    new_forest = chain.make_forest(await get_bios(backend))
    print(new_forest, old)
    return new_forest, diff.diff_forests(old, new_forest)
