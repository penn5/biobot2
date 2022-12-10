#    Bio Bot (Telegram bot for managing the @Bio_Chain_2)
#    Copyright (C) 2022 Hackintosh Five

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
import typing

import grapheme
import telethon
from telethon.events.common import EventBuilder

from biobot.translations import tr
from biobot.user import FullUser


def get_user_filter(name):
    try:
        name = int(name)
    except ValueError:
        name = name.casefold()
        filterfunc = lambda user: any(
            name == username.casefold() for username in user.usernames
        )
    else:
        filterfunc = lambda user: user.id == name
    return filterfunc


async def format_user(user: typing.Union[FullUser, typing.Iterable[FullUser]], link):
    if not isinstance(user, FullUser):
        return [await format_user(this_name, link) for this_name in user]
    if link:
        if user.id is None:
            ret = '<a href="https://t.me/{}">{}</a>'
        else:
            ret = '<a href="tg://user?id={}">{}</a>'
        return ret.format(user.id or user.usernames[0], ",".join(user.usernames))
    else:
        return ", ".join(user.usernames)


async def format_backend(event, backend):
    if backend == "file":
        return await tr(event, "backend_file")
    if backend == "default":
        return await tr(event, "backend_default")
    assert isinstance(backend, int)
    return "#data_{}".format(backend)


def move_entities(text, entities, move=0):
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
    :param split_on: characters (or strings) which are preferred for a message break,
                     sorted by priority on the first dimension (highest priority first)
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
        codepoint_count = len(
            encoded[bytes_offset : bytes_offset + length * 2].decode(
                "utf-16le", errors="ignore"
            )
        )
        for priority_group in split_on:
            first_search_index = -1
            for search in priority_group:
                search_index = text.rfind(
                    search, text_offset + min_length, text_offset + codepoint_count
                )
                if search_index != -1 and search_index > first_search_index:
                    first_search_index = search_index
            if first_search_index != -1:
                break
        else:
            first_search_index = text_offset + codepoint_count
        split_index = grapheme.safe_split_index(text, first_search_index)
        assert split_index > text_offset
        split_offset_utf16 = (
            len(text[text_offset:split_index].encode("utf-16le"))
        ) // 2
        exclude = 0
        while (
            split_index + exclude < text_length
            and text[split_index + exclude] in split_on
        ):
            exclude += 1
        current_entities = []
        entities = pending_entities.copy()
        pending_entities = []
        for entity in entities:
            if (
                entity.offset < split_offset_utf16
                and entity.offset + entity.length > split_offset_utf16 + exclude
            ):
                # spans boundary
                current_entities.append(
                    _copy_tl(entity, length=split_offset_utf16 - entity.offset)
                )
                pending_entities.append(
                    _copy_tl(
                        entity,
                        offset=0,
                        length=entity.offset
                        + entity.length
                        - split_offset_utf16
                        - exclude,
                    )
                )
            elif entity.offset < split_offset_utf16 < entity.offset + entity.length:
                # overlaps boundary
                current_entities.append(
                    _copy_tl(entity, length=split_offset_utf16 - entity.offset)
                )
            elif entity.offset < split_offset_utf16:
                # wholly left
                current_entities.append(entity)
            elif (
                entity.offset + entity.length
                > split_offset_utf16 + exclude
                > entity.offset
            ):
                # overlaps right boundary
                pending_entities.append(
                    _copy_tl(
                        entity,
                        offset=0,
                        length=entity.offset
                        + entity.length
                        - split_offset_utf16
                        - exclude,
                    )
                )
            elif entity.offset + entity.length > split_offset_utf16 + exclude:
                # wholly right
                pending_entities.append(
                    _copy_tl(
                        entity, offset=entity.offset - split_offset_utf16 - exclude
                    )
                )
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
    del d["_"]
    d.update(kwargs)
    return o.__class__(**d)


async def send(message, text, split_on=("\n", " "), **kwargs):
    text, entities = telethon.extensions.html.parse(text)
    messages = split(text, entities, split_on=split_on)
    if getattr(message, "out", False):
        current_text, current_entities = next(messages)
        current_html = telethon.extensions.html.unparse(current_text, current_entities)
        try:
            await message.edit(current_html, parse_mode="html", **kwargs)
        except telethon.errors.rpcerrorlist.MessageNotModifiedError:
            pass
        ret = None
    else:
        ret = True
    for current_text, current_entities in messages:
        current_html = telethon.extensions.html.unparse(current_text, current_entities)
        message = await message.reply(
            current_html, parse_mode="html", silent=True, **kwargs
        )
        if ret is True:
            ret = message
    return ret


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
        if (
            event.chat_id != self.main_group
            and event.chat_id != self.bot_group
            and event.chat_id not in self.extra_groups
            and event.sender_id not in self.sudo_users
        ):
            await event.reply(await tr(event, "forbidden"))
        else:
            return await func(self, event)

    return wrapper


def escape(text):
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


class ChatActionJoinedByRequest(EventBuilder):
    @classmethod
    def build(cls, update, others=None, self_id=None):
        if isinstance(
            update,
            (
                telethon.tl.types.UpdateNewMessage,
                telethon.tl.types.UpdateNewChannelMessage,
            ),
        ) and isinstance(update.message, telethon.tl.types.MessageService):
            msg = update.message
            action = update.message.action
            if isinstance(action, telethon.tl.types.MessageActionChatJoinedByRequest):
                return telethon.events.ChatAction.Event(msg, users=msg.from_id)
