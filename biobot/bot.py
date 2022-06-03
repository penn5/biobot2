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
from telethon.tl.custom.button import Button
from . import core, log
from .translations import tr
from .backends.bot import BotBackend
import logging
import time
import networkx
import base64
import datetime
import grapheme

logger = logging.getLogger(__name__)


FILE_NAMES = {"chain.gml", "raw_chain.forest"}
ALLOWED_FORMATS = {"svg", "svgz", "pdf"}


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
                event.sender_id not in self.sudo_users:
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


def _stringize(data):
    if data is None:
        return "None"
    if isinstance(data, str):
        return repr(data)
    raise ValueError


class BioBot:
    def __init__(self, api_id, api_hash, bot_token, main_group,
                 admissions_group, bot_group, data_group, rules_username, extra_groups=[], sudo_users=[],
                 test_dc=0):
        self.bot_token, self.main_group, self.admissions_group = bot_token, main_group, admissions_group
        self.bot_group, self.data_group, self.rules_username = bot_group, data_group, rules_username
        self.extra_groups, self.sudo_users = extra_groups, sudo_users
        self.client = telethon.TelegramClient(telethon.sessions.MemorySession(), api_id, api_hash)
        self.client.parse_mode = "html"
        if test_dc:
            self.client.session.set_dc(test_dc, "149.154.167.40", 80)

    async def init(self):
        await self.client.start(bot_token=self.bot_token)
        await self.client.get_participants(self.main_group)
        me = await self.client.get_me()
        self.username = me.username
        self.admissions_entity = await self.client.get_entity(self.admissions_group)
        self.target = self.admissions_entity.username
        self.data_group = await self.client.get_input_entity(self.data_group)
        self.bot_backend = BotBackend(bot=self.client, group_id=self.main_group, api_id=None, api_hash=None)
        await self.bot_backend.init()
        await self.add_handlers()
        return self.client

    async def add_handlers(self):
        start = r"^(?:\/|!)"
        eoc = fr"(?:$|\s|@{self.username}(?:$|\s))"
        data = r"(?:(?:#data_?)?(\d+))"
        username = r"(?:@?([a-zA-Z0-9_]{{5,}}|[0-9]+))"

        self.client.add_event_handler(self.ping_command,
                                      telethon.events.NewMessage(pattern=fr"{start}ping{eoc}"))
        self.client.add_event_handler(self.chain_command,
                                      telethon.events.NewMessage(pattern=fr"{start}chain{eoc}{data}?"))
        self.client.add_event_handler(self.chain_command,
                                      telethon.events.NewMessage(pattern=fr"{start}locate{eoc}{data}?(?: {username})?"))
        self.client.add_event_handler(self.notinchain_command,
                                      telethon.events.NewMessage(pattern=fr"{start}notinchain{eoc}{data}?"))
        self.client.add_event_handler(self.allchains_command,
                                      telethon.events.NewMessage(pattern=fr"{start}allchains{eoc}{data}?"))
        self.client.add_event_handler(self.fetchdata_command,
                                      telethon.events.NewMessage(pattern=fr"{start}(?:get|fetch)data{eoc}{data}?"))
        self.client.add_event_handler(self.diff_command,
                                      telethon.events.NewMessage(pattern=fr"{start}tdiff{eoc}(?:{data}(?: {data})?)?"))
        self.client.add_event_handler(self.gdiff_command,
                                      telethon.events.NewMessage(pattern=fr"{start}gdiff{eoc}(?:{data}(?: {data})?)?(?: \.(\w+))?"))
        self.client.add_event_handler(self.link_command,
                                      telethon.events.NewMessage(pattern=fr"{start}(?:perma)?link{eoc}(?:{data} )?{username}"))
        self.client.add_event_handler(self.start_command,
                                      telethon.events.NewMessage(pattern=fr"{start}start{eoc}(.*)"))
        self.client.add_event_handler(self.logs_command,
                                      telethon.events.NewMessage(pattern=fr"{start}logs{eoc}(\d*)"))
        self.client.add_event_handler(self.log_capacity_command,
                                      telethon.events.NewMessage(pattern=fr"{start}log_capacity{eoc}(\d*)"))
        self.client.add_event_handler(self.user_joined_admission,
                                      telethon.events.ChatAction(chats=self.admissions_group))
        self.client.add_event_handler(self.user_joined_main,
                                      telethon.events.ChatAction(chats=self.main_group))
        self.client.add_event_handler(self.callback_query,
                                      telethon.events.CallbackQuery())

    async def run(self, backend):
        self.backend = backend
        await self.client.send_message(self.bot_group, "🆙 and 🏃ing!")
        logger.info("Up and running!")
        await self.client.run_until_disconnected()

    @error_handler
    async def ping_command(self, event):
        await event.reply(await tr(event, "pong"))

    @error_handler
    @protected
    async def chain_command(self, event):
        new = await event.reply(await tr(event, "please_wait"))
        graph, chain = await core.get_chain(self.target, await self._select_backend(event, error=new))
        data = await self._store_data(graph)
        await send(new, (await tr(event, "chain_format")).format(f"#chain_{len(chain)} {data}", (await tr(event, "chain_delim")).join(user for user in await _format_user(chain, graph, False))))

    @error_handler
    @protected
    async def notinchain_command(self, event):
        new = await event.reply(await tr(event, "please_wait"))
        graph, antichain = await core.get_notinchain(self.target, await self._select_backend(event, error=new))
        data = await self._store_data(graph)
        await send(new, data + "\n" + "\n".join(user for user in await _format_user((user for user in antichain if graph.nodes[user]["uid"] is not None and not graph.nodes[user]["deleted"]), graph, True)))

    @error_handler
    @protected
    async def allchains_command(self, event):
        new = await event.reply(await tr(event, "please_wait"))
        graph, chains = await core.get_chains(await self._select_backend(event, error=new))
        data = await self._store_data(graph)
        out = [" ⇒ ".join(await _format_user(chain, graph, False)) for chain in chains if len(chain) > 1 or graph.nodes[chain[0]]["uid"] is not None]
        await send(new, data + " " + "\n\n".join(out))

    @error_handler
    @protected
    async def fetchdata_command(self, event):
        await event.reply((await self._fetch_data(int(event.pattern_match[1]))) or await tr(event, "invalid_id"))

    @error_handler
    @protected
    async def diff_command(self, event):
        new = await event.reply(await tr(event, "please_wait"))
        backend = await self._select_backend(event, default_backend=False, error=new)
        if not backend:
            return
        graph, diff = await core.get_diff(backend, await self._select_backend(event, 1, error=new), await tr(event, "diff_username_delim"), "\n")
        data = await self._store_data(graph)
        old_only_edges, new_only_edges, uid_edges, username_edges, old_only_names, new_only_names = diff
        await send(new, (await tr(event, "diff_format")).format(data, new_only_names, old_only_names, username_edges, uid_edges, new_only_edges, old_only_edges))

    @error_handler
    @protected
    async def gdiff_command(self, event):
        new = await event.reply(await tr(event, "please_wait"))
        backend = await self._select_backend(event, default_backend=False, error=new)
        if not backend:
            return
        format = event.pattern_match[3]
        if format not in ALLOWED_FORMATS:
            format = "svgz"
        graph, diff = await core.get_gdiff(backend, await self._select_backend(event, 1, error=new), self.target, format)
        await self._store_data(graph)
        await event.reply(file=diff, force_document=True)
        await new.delete()

    @error_handler
    @protected
    async def link_command(self, event):
        new = await event.reply(await tr(event, "please_wait"))
        data = await self._select_backend(event, error=new)
        graph = await core.get_bios(data)
        name = event.pattern_match[2]
        try:
            name = int(name)
        except ValueError:
            filterfunc = lambda x: x[1]["username"] and x[1]["username"].casefold() == name.casefold()
        else:
            filterfunc = lambda x: x[1]["uid"] == name
        ret = filter(filterfunc, graph.nodes.items())
        try:
            ret = next(ret)
        except StopIteration:
            await send(new, await tr(event, "invalid_user"))
            return
        await send(new, await _format_user(ret[0], graph, True))

    @error_handler
    async def start_command(self, event):
        if event.chat_id == self.admissions_group:
            return await self.user_joined_admission(event)
        if not event.is_private:
            return
        msg = event.pattern_match[1]
        if msg:
            if msg.startswith("invt"):
                encoded = msg[12:] + "=" * (-len(msg) % 4)
                unescaped = "https://" + base64.urlsafe_b64decode(encoded.encode("utf-8")).decode("utf-8")
                await event.respond((await tr(event, "invite_format")).format(unescaped), link_preview=False)
                await self.client.delete_messages(self.admissions_entity.id, int(msg[4:12], 16))
                return
            if msg.startswith("help"):
                buttons = [Button.url(await tr(event, "return_to_group"),
                                      "https://t.me/c/{}/{}".format(self.admissions_entity.id, int(msg[5:13], 16)))]
                if msg[4] == "s":
                    await event.respond((await tr(event, "start_help")).format(self.rules_username), buttons=buttons)
                    return
                if msg[4] == "j":
                    await event.respond((await tr(event, "join_help")).format(msg[13:]), buttons=buttons)
                    return
                if msg[4] == "u":
                    await event.respond(await tr(event, "username_help"), buttons=buttons)
                    return
        await event.respond((await tr(event, "pm_start")).format(self.target))

    @error_handler
    async def logs_command(self, event):
        if event.sender_id in self.sudo_users:
            level = int(event.pattern_match[1] or 0)
            entries = log.getMemoryHandler().dumps(level)
            if entries:
                logs = (
"<!DOCTYPE html>"
"<html>"
  "<head>"
    "<style>"
      # adapted from https://stackoverflow.com/a/41309213/5509575, CC BY-SA by Rounin
      + (
      "pre {"
        "white-space: pre-wrap;"
      "}"

      "pre::before {"
        "counter-reset: listing;"
      "}"

      "code {"
        "counter-increment: listing;"
        "text-align: left;"
        "float: left;"
        "clear: left;"
        "margin-left: 4em;"
        "margin-bottom: 1em;"
      "}"

      "code::before {"
        "content: counter(listing) \". \";"
        "display: block;"
        "float: left;"
        "text-align: right;"
        "width: 4em;"
        "margin-left: -4em;"
      "}"

      "code > br {"
        "display: none;"
      "}"
      ).replace(": ", ":").replace(" {", "{") +
    "</style>"
  "</head>"
  "<body>"
    "<pre class=\"code\">\n"
      + "<br>".join(entries) +
    "\n</pre>"
  "</body>"
"</html>"
).encode("utf-8")
                file = io.BytesIO(logs)
                file.name = "logs.html"
                await self.client.send_message(event.sender_id, file=file)
                resp = "logs_sent"
            else:
                resp = "logs_empty"
        else:
            resp = "logs_forbidden"
        await send(event, await tr(event, resp))

    @error_handler
    async def log_capacity_command(self, event):
        if event.sender_id in self.sudo_users:
            capacity = int(event.pattern_match[1])
            entries = log.getMemoryHandler().setCapacity(capacity)
            resp = "logs_capacity_updated"
        else:
            resp = "logs_forbidden"
        await send(event, await tr(event, resp))

    @error_handler
    async def user_joined_admission(self, event):
        cb = None
        if isinstance(event, telethon.events.ChatAction.Event) and (event.user_joined or event.user_added):
            cb = event.user_id
        if isinstance(event, telethon.events.NewMessage.Event):
            if isinstance(event.from_id, telethon.tl.types.PeerUser):
                cb = event.from_id.user_id
            else:
                cb = None
        if cb is None:
            await event.reply(await tr(event, "fix_anonymous"))
        else:
            cb = cb.to_bytes(8, "big")
            await event.reply(await tr(event, "welcome_admission"),
                              buttons=[Button.inline(await tr(event, "click_me"), b"s" + cb)])

    @error_handler
    async def user_joined_main(self, event):
        if event.user_joined or event.user_added:
            await self.chain_command(event)

    @error_handler
    async def callback_query(self, event):
        for_user = int.from_bytes(event.data[1:9], "big")
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
                                        [Button.inline(await tr(event, "rules_accept"), b"j" + event.data[1:9])],
                                        [Button.inline(await tr(event, "rules_reject"), b"c" + event.data[1:9])],
                                        [Button.inline(await tr(event, "get_help"), b"h" + event.data[1:9] + b"s")]])
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
        graph, chain = await core.get_chain(self.target, self.backend)
        input_entity = await event.get_input_sender()
        if not input_entity:
            # testmode support
            await event.answer(await tr(event, "start_bot"), alert=True)
            await message.edit(await tr(event, "please_click"),
                               buttons=[[Button.inline(await tr(event, "continue"), event.data)],
                                        [Button.inline(await tr(event, "cancel"), b"c" + event.data[1:9])],
                                        [Button.inline(await tr(event, "get_help"), b"h" + event.data[1:9] + b"s")]])
            return
        entity = await self.client.get_entity(input_entity)  # To prevent caching
        if entity.username and entity.username.lower() in (name.lower() for name in chain):
            await event.answer(await tr(event, "already_in_chain"), alert=True)
            await message.edit(await tr(event, "already_in_chain"), buttons=None)
            return
        await self.callback_query_done(event, message, b"d" + event.data[1:9] + int(time.time()).to_bytes(8, "big") + next(filter(lambda name: isinstance(name, str), chain)).encode("ascii"))

    async def callback_query_done(self, event, message, data=None):
        if data is None:
            skip = False
            data = event.data
        else:
            skip = True
        if not skip:
            if int.from_bytes(data[9:17], "big") < int(time.time()) - 120:
                await self.callback_query_join(event, message)
                return
            try:
                await message.edit(await tr(event, "verifying_10s"), buttons=None)
            except telethon.errors.rpcerrorlist.MessageNotModifiedError:
                await event.answer(await tr(event, "button_loading"))
                return
            input_entity = await event.get_input_sender()
            if not input_entity:
                # testmode support
                await event.answer(await tr(event, "start_bot"), alert=True)
                return
            entity = await self.client.get_entity(input_entity)  # To prevent caching
            bio = [username.casefold() for username in await self.bot_backend.get_bio_links(entity.id, entity.username)]
        if skip or data[17:].decode("ascii").casefold() not in bio:
            await message.edit(await tr(event, "please_click"),
                               buttons=[[Button.inline(await tr(event, "continue"), data)],
                                        [Button.inline(await tr(event, "cancel"), b"c" + data[1:9])],
                                        [Button.inline(await tr(event, "get_help"),
                                                       b"h" + data[1:9] + b"j" + data[17:])]])
            msg = (await tr(event, "set_bio")).format(data[17:].decode("ascii"))
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
                                        [Button.inline(await tr(message, "cancel"), b"c" + data[1:9])],
                                        [Button.inline(await tr(message, "get_help"),
                                                       b"h" + data[1:9] + b"u")]])
            return
        invite = await self.client(telethon.tl.functions.messages.ExportChatInviteRequest(self.main_group, expire_date=datetime.timedelta(hours=1), usage_limit=1))
        escaped = base64.urlsafe_b64encode(invite.link.removeprefix("https://").encode("utf-8")).decode("utf-8").replace("=", "")
        try:
            await event.answer(url="t.me/{}?start=invt{:08X}{}".format(self.username, message.id, escaped))
        except telethon.errors.rpcerrorlist.QueryIdInvalidError:
            pass
        await message.edit(await tr(message, "please_click"),
                           buttons=[[Button.inline(await tr(message, "continue"), data)],
                                    [Button.inline(await tr(message, "cancel"), b"c" + data[1:9])],
                                    [Button.inline(await tr(message, "get_help"),
                                                   b"h" + data[1:9] + b"j" + data[17:])]])

    async def callback_query_help(self, event, message):
        await event.answer(url="t.me/{}?start=help{}{:08X}{}".format(self.username, event.data[9:10].decode("ascii"),
                                                                     message.id, event.data[10:].decode("ascii")))

    async def callback_query_cancel(self, event, message):
        await event.answer(await tr(message, "cancelled"), alert=True)
        await message.delete()

    async def _select_backend(self, event, match_id=0, *, error=None, default_backend=None):
        if error is None:
            error = event
        if default_backend is None:
            default_backend = self.backend
        data_id = None
        try:
            data_id_str = getattr(event, "pattern_match", ())[match_id + 1]
            if data_id_str:
                data_id = int(data_id_str)
        except ValueError:
            await send(error, await tr(event, "invalid_id"))
        except IndexError:
            pass
        if data_id is None and getattr(event, "is_reply", False) and not match_id:
            reply = await event.get_reply_message()
            if getattr(getattr(reply, "file", None), "name", None) in FILE_NAMES:
                if event.sender_id in self.sudo_users:
                    return (await reply.download_media(bytes), reply.file.name)
                else:
                    await send(error, await tr(error, "untrusted_forbidden"))
                    return
            if data_id is None:
                try:
                    data_id = int(re.search(r"\s#data_?(\d+)\s", reply.text)[0])
                except (ValueError, TypeError, IndexError):
                    pass
        if data_id is None:
            return default_backend
        data = await self._fetch_data(data_id)
        if data is None:
            await send(error, await tr(event, "invalid_id"))
            return default_backend
        return (await data.download_media(bytes), data.file.name)

    async def _fetch_data(self, data_id):
        ret = await self.client.get_messages(self.data_group, ids=data_id)
        if getattr(getattr(ret, "file", None), "name", None) not in FILE_NAMES:
            return None
        return ret

    async def _store_data(self, graph):
        graph = graph.copy()
        await self.client.get_participants(self.main_group)
        for node, data in graph.nodes.items():
            if data["uid"] and not data.get("access_hash", None):
                try:
                    entity = await self.client.get_input_entity(telethon.tl.types.PeerUser(data["uid"]))
                except (ValueError, TypeError):
                    entity = None
                if isinstance(entity, telethon.tl.types.InputPeerUser):
                    data["access_hash"] = entity.access_hash
        data = io.BytesIO()
        data.name = "chain.gml"
        networkx.write_gml(graph, data, stringizer=_stringize)
        data.seek(0)
        message = await self.client.send_message(self.data_group, file=data)
        return "#data_{}".format(message.id)


async def _format_user(name, graph, link):
    # the data MUST have been stored before calling this function
    if not isinstance(name, (str, int)):
        return [await _format_user(this_name, graph, link) for this_name in name]
    if link:
        uid = graph.nodes[name]["uid"]
        if uid is None:
            ret = "<a href=\"https://t.me/{}\">{}</a>"
        else:
            ret = "<a href=\"tg://user?id={}\">{}</a>"
    else:
        return str(name)
    return ret.format(uid or name, name)


def _move_entities(text, entities, move=0):
    for entity in entities.copy():
        if move:
            entity.offset -= move
        if entity.offset + entity.length <= 0:
            entities.remove(entity)
            continue
        if entity.offset < 0:
            entity.length += entity.offset
            entity.offset = 0
    length = 4096
    count = 0
    current_entities = []
    for entity in entities:
        count += 1
        if count > 100:
            length = entity.offset
            break
        current_entities.append(entity)
    current_text = telethon.extensions.html.unparse(text[:length], current_entities)
    text = text[length:]
    return current_text, text, entities, length


def split(text, entities, length=4096, split_on=("\n", " "), min_length=1):
    """
    Split the message into smaller messages.
    A grapheme will never be broken. Entities will be displaced to match the right location. No inputs will be mutated.
    The end of each message except the last one is stripped of characters from [split_on]
    :param text: the plain text input
    :param entities: the entities
    :param length: the maximum length of a single message
    :param split_on: characters (or strings) which are preferred for a message break
    :param min_length: ignore any matches on [split_on] strings before this number of characters into each message
    :return:
    """
    encoded = text.encode("utf-16le")
    pending_entities = entities
    text_offset = 0
    bytes_offset = 0
    text_length = len(text)
    bytes_length = len(encoded)
    while text_offset < text_length:
        if bytes_offset + length * 2 >= bytes_length:
            yield text[text_offset:], pending_entities
            break
        codepoint_count = len(encoded[bytes_offset:bytes_offset + length * 2].decode("utf-16le", errors="ignore"))
        for search in split_on:
            search_index = text.rfind(search, text_offset + min_length, text_offset + codepoint_count)
            if search_index != -1:
                break
        else:
            search_index = text_offset + codepoint_count
        split_index = grapheme.safe_split_index(text, search_index)
        assert split_index > text_offset
        split_offset_utf16 = (len(text[text_offset:split_index].encode("utf-16le"))) // 2
        exclude = 0
        while split_index + exclude < text_length and text[split_index + exclude] in split_on:
            exclude += 1
        current_entities = []
        entities = pending_entities.copy()
        pending_entities = []
        for entity in entities:
            if entity.offset < split_offset_utf16 and entity.offset + entity.length > split_offset_utf16 + exclude:
                # spans boundary
                current_entities.append(_copy_tl(entity, length=split_offset_utf16 - entity.offset))
                pending_entities.append(_copy_tl(entity, offset=0, length=entity.offset + entity.length - split_offset_utf16 - exclude))
            elif entity.offset < split_offset_utf16 < entity.offset + entity.length:
                # overlaps boundary
                current_entities.append(_copy_tl(entity, length=split_offset_utf16 - entity.offset))
            elif entity.offset < split_offset_utf16:
                # wholly left
                current_entities.append(entity)
            elif entity.offset + entity.length > split_offset_utf16 + exclude > entity.offset:
                # overlaps right boundary
                pending_entities.append(_copy_tl(entity, offset=0, length=entity.offset + entity.length - split_offset_utf16 - exclude))
            elif entity.offset + entity.length > split_offset_utf16 + exclude:
                # wholly right
                pending_entities.append(_copy_tl(entity, offset=entity.offset - split_offset_utf16 - exclude))
            else:
                assert entity.length <= exclude
                # ignore entity in whitespace
        current_text = text[text_offset:split_index]
        yield current_text, current_entities
        text_offset = split_index + exclude
        bytes_offset += len(current_text.encode("utf-16le"))
        assert bytes_offset % 2 == 0


def _copy_tl(o, **kwargs):
    d = o.to_dict()
    del d['_']
    d.update(kwargs)
    return o.__class__(**d)


async def send(message, text, **kwargs):
    text, entities = telethon.extensions.html.parse(text)
    messages = split(text, entities)
    if message.out:
        current_text, current_entities = next(messages)
        try:
            await message.edit(current_text, formatting_entities=current_entities, **kwargs)
        except telethon.errors.rpcerrorlist.MessageNotModifiedError:
            pass
    for current_text, current_entities in messages:
        message = await message.reply(current_text, formatting_entities=current_entities, silent=True, **kwargs)
