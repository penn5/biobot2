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

import functools
import telethon
import io
import re
import pickle
from telethon.tl.custom.button import Button
from . import core
from .translations import tr
import logging
import time

logger = logging.getLogger(__name__)


def error_handler(func):
    @functools.wraps(func)
    async def wrapper(self, event):
        try:
            return await func(self, event)
        except Exception:
            await event.reply(await tr(event, "fatal_error"))
            raise
    return wrapper


def protected(func):
    @functools.wraps(func)
    async def wrapper(self, event):
        if event.chat_id != self.main_group and \
                event.chat_id != self.bot_group and \
                event.chat_id not in self.extra_groups and \
                event.from_id.user_id not in self.sudo_users:
            await event.reply(await tr(event, "forbidden"))
        else:
            return await func(self, event)
    return wrapper


def escape(text):
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


async def anext(aiter, default=False):
    """Stopgap because PEP 525 isn't fully implemented yet"""
    try:
        return await aiter.__anext__()
    except StopAsyncIteration:
        if default is False:
            raise
        return default


class BioBot:
    def __init__(self, api_id, api_hash, bot_token, main_group,
                 admissions_group, bot_group, data_group, rules_username, extra_groups=[], sudo_users=[]):
        self.bot_token, self.main_group, self.admissions_group = bot_token, main_group, admissions_group
        self.bot_group, self.data_group, self.rules_username = bot_group, data_group, rules_username
        self.extra_groups, self.sudo_users = extra_groups, sudo_users
        self.client = telethon.TelegramClient(telethon.sessions.MemorySession(), api_id, api_hash)
        self.client.parse_mode = "html"

    async def init(self):
        await self.client.start(bot_token=self.bot_token)
        await self.client.get_participants(self.main_group)
        me = await self.client.get_me()
        self.username = me.username
        eoc_regex = f"(?:$|\s|@{me.username}(?:$|\s))"
        self.client.add_event_handler(self.ping_command,
                                      telethon.events.NewMessage(incoming=True, pattern="/ping" + eoc_regex))
        self.client.add_event_handler(self.chain_command,
                                      telethon.events.NewMessage(incoming=True, pattern="/chain"
                                                                 + eoc_regex + "(?:#data)?(\d+)?"))
        self.client.add_event_handler(self.allchains_command,
                                      telethon.events.NewMessage(incoming=True, pattern="/allchains"
                                                                 + eoc_regex + "(?:#data)?(\d+)?"))
        self.client.add_event_handler(self.fetchdata_command,
                                      telethon.events.NewMessage(incoming=True, pattern="/fetchdata"
                                                                 + eoc_regex + "(?:#data)?(\d+)"))
        self.client.add_event_handler(self.diff_command,
                                      telethon.events.NewMessage(incoming=True, pattern="/diff"
                                                                 + eoc_regex + "(?:#data)?(\d*)(?: )?(?:#data)?(\d*)"))
        self.client.add_event_handler(self.link_command,
                                      telethon.events.NewMessage(incoming=True, pattern="/(?:perma)?link"
                                                                 + eoc_regex + "(?:#data)?(\d*) ([a-zA-z0-9_]{5,})"))
        self.client.add_event_handler(self.start_command,
                                      telethon.events.NewMessage(incoming=True, pattern="/start\s?(.*)"))
        self.client.add_event_handler(self.user_joined_admission,
                                      telethon.events.ChatAction(chats=self.admissions_group))
        self.client.add_event_handler(self.user_joined_main,
                                      telethon.events.ChatAction(chats=self.main_group))
        self.client.add_event_handler(self.callback_query,
                                      telethon.events.CallbackQuery())
        self.admissions_entity = await self.client.get_entity(self.admissions_group)
        self.target = self.admissions_entity.username
        self.data_group = await self.client.get_input_entity(self.data_group)
        return self.client

    async def run(self, backend):
        self.backend = backend
        await self.client.send_message(self.bot_group, "🆙 and 🏃ing!")
        print("Up and running!")
        await self.client.run_until_disconnected()

    @error_handler
    async def ping_command(self, event):
        await event.reply(await tr(event, "pong"), silent=True)

    @error_handler
    @protected
    async def chain_command(self, event):
        new = await event.reply(await tr(event, "please_wait"), silent=True)
        forest, chain = await core.get_chain(self.target, await self._select_backend(event))
        data = await self._store_data(forest)
        await send(new, (await tr(event, "chain_format")).format(len(chain), data,
                                                                 (await tr(event, "chain_delim")).join(user.username
                                                                                                       for user in
                                                                                                       chain)))

    @error_handler
    @protected
    async def allchains_command(self, event):
        new = await event.reply(await tr(event, "please_wait"), silent=True)
        forest, chains = await core.get_chains(await self._select_backend(event))
        data = await self._store_data(forest)
        out = [" ⇒ ".join(user.username for user in chain) for chain in chains]
        await send(new, data + " " + "\n\n".join(out))

    @error_handler
    @protected
    async def fetchdata_command(self, event):
        await event.reply((await self._fetch_data(int(event.pattern_match[1]))) or await tr(event, "invalid_id"),
                          silent=True)

    @error_handler
    @protected
    async def diff_command(self, event):
        new = await event.reply(await tr(event, "please_wait"), silent=True)
        backend = await self._select_backend(event, default_backend=False)
        if not backend:
            await send(new, await tr(event, "invalid_id"))
            return
        forest, diff = await core.get_diff(backend, await self._select_backend(event, 1))
        data = await self._store_data(forest)
        print(data, diff)
        new_uids, gone_uids, username_replacements, username_changes, new_bios, gone_bios = diff
        delim = await tr(event, "diff_delim")
        new_uids = delim.join(_format_user(user) for user in new_uids)
        gone_uids = delim.join(_format_user(user) for user in gone_uids)
        username_delim = await tr(event, "diff_username_delim")
        username_replacements = delim.join(_format_user(user1) + username_delim + _format_user(user2)
                                           for user1, user2 in username_replacements)
        username_changes = delim.join(_format_user(user1) + username_delim + _format_user(user2)
                                      for user1, user2 in username_changes)
        parent_delim = await tr(event, "diff_parents_delim")
        new_bios = delim.join(_format_user(parent1) + parent_delim + _format_user(parent2)
                              + username_delim + user
                              for parent1, parent2, user in new_bios)
        gone_bios = delim.join(_format_user(parent1) + parent_delim + _format_user(parent2)
                               + username_delim + user
                               for parent1, parent2, user in gone_bios)

        await send(new, (await tr(event, "diff_format")).format(data, new_uids, gone_uids, username_replacements,
                                                                username_changes, new_bios, gone_bios))

    @error_handler
    @protected
    async def link_command(self, event):
        new = await event.reply(await tr(event, "please_wait"), silent=True)
        data = await self._select_backend(event, default_backend=False)
        if not data:
            await send(new, await tr(event, "invalid_id"))
            return
        ret = data.get_node(event.pattern_match[2], add=False)
        await send(new, "<a href=\"tg://user?id={}\">".format(ret.uid) + ret.username + "</a>")

    async def start_command(self, event):
        if not event.is_private:
            return
        msg = event.pattern_match[1]
        if msg:
            if msg.startswith("invt"):
                await event.respond((await tr(event, "invite_format")).format(msg[12:]), link_preview=False)
                await self.client.delete_messages(self.admissions_entity.id, int(msg[4:12], 16))
                return
            if msg.startswith("help"):
                buttons = [Button.url(await tr(event, "return_to_group"),
                                      "t.me/c/{}/{}".format(self.admissions_entity.id, int(msg[5:13], 16)))]
                if msg[4] == "s":
                    await event.respond((await tr(event, "start_help")).format(self.rules_username), buttons=buttons)
                    return
                if msg[4] == "j":
                    await event.respond((await tr(event, "join_help")).format(msg[5:]), buttons=buttons)
                    return
                if msg[4] == "u":
                    await event.respond(await tr(event, "username_help"), buttons=buttons)
                    return
        await event.respond((await tr(event, "pm_start")).format(self.target))

    @error_handler
    async def user_joined_admission(self, event):
        if event.user_joined or event.user_added:
            cb = event.user_id.to_bytes(4, "big")
            await event.reply(await tr(event, "welcome_admission"),
                              buttons=[Button.inline(await tr(event, "click_me"), b"s" + cb)])

    @error_handler
    async def user_joined_main(self, event):
        if event.user_joined or event.user_added:
            await self.client(telethon.tl.functions.messages.ExportChatInviteRequest(event.chat_id))
            await self.chain_command(event)

    @error_handler
    async def callback_query(self, event):
        for_user = int.from_bytes(event.data[1:5], "big")
        if for_user != event.sender_id:
            await event.answer(await tr(event, "click_forbidden"))
            return
        message = await event.get_message()
        if event.data[0] == b"s"[0]:
            await self.callback_query_start(event, message)
        elif event.data[0] == b"j"[0]:
            await self.callback_query_join(event, message)
        elif event.data[0] == b"d"[0]:
            await self.callback_query_done(event, message)
        elif event.data[0] == b"h"[0]:
            await self.callback_query_help(event, message)
        elif event.data[0] == b"c"[0]:
            await self.callback_query_cancel(event, message)
        else:
            logger.error("Unknown callback query state %r", event)

    async def callback_query_start(self, event, message):
        try:
            await message.edit(await tr(event, "please_click"),
                               buttons=[[Button.url(await tr(event, "rules_link"), "https://t.me/" + self.rules_username)],
                                        [Button.inline(await tr(event, "rules_accept"), b"j" + event.data[1:5])],
                                        [Button.inline(await tr(event, "rules_reject"), b"c" + event.data[1:5])],
                                        [Button.inline(await tr(event, "get_help"), b"h" + event.data[1:5] + b"s")]])
        except telethon.errors.rpcerrorlist.MessageNotModifiedError:
            await event.answer(await tr(event, "button_loading"))
            return
        await event.answer((await tr(event, "read_rules")).format(self.rules_username), alert=True)

    async def callback_query_join(self, event, message):
        try:
            await message.edit(await tr(event, "loading_1m"), buttons=None)
        except telethon.errors.rpcerrorlist.MessageNotModifiedError:
            await event.answer(await tr(event, "button_loading"))
            return
        forest, chain = await core.get_chain(self.target, self.backend)
        input_entity = await event.get_input_sender()
        entity = await self.client.get_entity(input_entity)  # To prevent caching
        if entity.username and entity.username.lower() in (user.username.lower() for user in chain):
            await event.answer(await tr(event, "already_in_chain"), alert=True)
            await message.edit(await tr(event, "already_in_chain"), buttons=None)
            return
        await self.callback_query_done(event, message, b"d" + event.data[1:5] + int(time.time()).to_bytes(4, "big") + chain[0].username.encode("ascii"))

    async def callback_query_done(self, event, message, data=None):
        if data is None:
            skip = False
            data = event.data
        else:
            skip = True
        if not skip:
            print(int.from_bytes(data[5:9], "big"), int(time.time()) - 120)
            if int.from_bytes(data[5:9], "big") < int(time.time()) - 120:
                await self.callback_query_join(event, message)
                return
            try:
                await message.edit(await tr(event, "verifying_10s"), buttons=None)
            except telethon.errors.rpcerrorlist.MessageNotModifiedError:
                await event.answer(await tr(event, "button_loading"))
                return
            input_entity = await event.get_input_sender()
            entity = await self.client.get_entity(input_entity)  # To prevent caching
            bio = [username.lower() for username in await self.backend.get_bio_links(entity.id, entity.username)]
        if skip or data[9:].decode("ascii").lower() not in bio:
            await message.edit(await tr(event, "please_click"),
                               buttons=[[Button.inline(await tr(event, "continue"), data)],
                                        [Button.inline(await tr(event, "cancel"), b"c" + data[1:5])],
                                        [Button.inline(await tr(event, "get_help"),
                                                       b"h" + data[1:5] + b"j" + data[9:])]])
            msg = (await tr(event, "set_bio")).format(data[9:].decode("ascii"))
            try:
                await event.answer(msg, alert=True)
            except telethon.errors.rpcerrorlist.QueryIdInvalidError:
                pass
            return
        if not skip and entity.username is None:
            try:
                await event.answer(await tr(message, "set_username"), alert=True)
            except telethon.errors.rpcerrorlist.QueryIdInvalidError:
                pass
            await message.edit(await tr(message, "please_click"),
                               buttons=[[Button.inline(await tr(message, "continue"), data)],
                                        [Button.inline(await tr(message, "cancel"), b"c" + data[1:5])],
                                        [Button.inline(await tr(message, "get_help"),
                                                       b"h" + data[1:5] + b"u" + data[5:9])]])
            return
        invite = await self.client(telethon.tl.functions.messages.ExportChatInviteRequest(self.main_group))
        escaped = invite.link.split("/")[-1]
        await event.answer(url="t.me/{}?start=invt{:08X}{}".format(self.username, message.id, escaped))
        await message.edit(await tr(message, "please_click"),
                           buttons=[[Button.inline(await tr(message, "continue"), data)],
                                    [Button.inline(await tr(message, "cancel"), b"c" + data[1:5])],
                                    [Button.inline(await tr(message, "get_help"),
                                                   b"h" + data[1:5] + b"j" + data[9:])]])

    async def callback_query_help(self, event, message):
        await event.answer(url="t.me/{}?start=help{}{:08X}{}".format(self.username, event.data[5:6].decode("ascii"),
                                                                     message.id, event.data[6:].decode("ascii")))

    async def callback_query_cancel(self, event, message):
        await event.answer(await tr(message, "cancelled"), alert=True)
        await message.delete()

    async def _select_backend(self, event, match_id=0, default_backend=None, no_error=False):
        if default_backend is None:
            default_backend = self.backend
        try:
            match = getattr(event, "pattern_match", ())[match_id + 1]
        except IndexError:
            match = None
        if match:
            message = await self._fetch_data(int(match))
            return pickle.loads(await message.download_media(bytes))
        if getattr(event, "is_reply", False) and not match_id:
            reply = await event.get_reply_message()
            print(reply)
            if getattr(getattr(reply, "file", None), "name", None) == "raw_chain.forest":
                if event.from_id.user_id in self.sudo_users:
                    return pickle.loads(await reply.download_media(bytes))
                else:
                    await event.reply(await tr(message, "untrusted_forbidden"), silent=True)
            try:
                data_id = int(re.search(r"\s#data(\d+)\s", reply.text)[1])
            except (ValueError, TypeError):
                if not no_error:
                    await event.reply(await tr(event, "invalid_id"), silent=True)
                return default_backend
            else:
                msg = await self.client.get_messages(self.data_group, ids=data_id)
                return pickle.loads(await msg.download_media(bytes))
        return default_backend

    async def _fetch_data(self, data_id):
        ret = await self.client.get_messages(self.data_group, ids=data_id)
        if getattr(getattr(ret, "file", None), "name", None) != "raw_chain.forest":
            return None
        return ret

    async def _store_data(self, forest):
        nodes = forest.get_nodes()
        await self.client.get_participants(self.main_group)
        for node in nodes:
            try:
                entity = await self.client.get_input_entity(node.uid)
            except (ValueError, TypeError):
                entity = None
            if isinstance(entity, telethon.tl.types.InputPeerUser) and entity.user_id != node.uid and node.uid:
                logger.error("Username %s changed UID from %d to %r", node.username, node.uid, entity)
                continue
            node.extras["entity"] = entity
        data = io.BytesIO()
        data.name = "raw_chain.forest"
        pickle.dump(forest, data)
        data.seek(0)
        message = await self.client.send_message(self.data_group, file=data)
        return "#data{}".format(message.id)


def _format_user(user):
    return "<a href=\"tg://user?id={}\">".format(user.uid) + str(user.uid) + "</a>:" + str(user.username)


async def send(message, text):
    await message.edit(text[:4096])
    text = text[4096:]
    while text:
        await message.reply(text[:4096], silent=True)
        text = text[4096:]
