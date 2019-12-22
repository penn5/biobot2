from . import backend_manager, chain
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
