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

import base64
import datetime
import io
import logging
import re
import time

import telethon
from telethon.tl.custom.button import Button

from . import core, log
from .backends.bot import BotBackend
from .translations import tr
from .user import get_bio_links, node_to_user
from .utils import (
    get_user_filter,
    format_user,
    format_backend,
    send,
    error_handler,
    protected,
    ChatActionJoinedByRequest,
)

logger = logging.getLogger(__name__)

FILE_NAMES = {"chain.gml", "raw_chain.forest"}
ALLOWED_FORMATS = {"svg", "svgz", "pdf"}


class BioBot:
    def __init__(
        self,
        api_id,
        api_hash,
        bot_token,
        main_group,
        admissions_group,
        bot_group,
        data_group,
        rules_username,
        extra_groups=[],
        sudo_users=[],
        test_dc=0,
    ):
        self.bot_token, self.main_group, self.admissions_group = (
            bot_token,
            main_group,
            admissions_group,
        )
        self.bot_group, self.data_group, self.rules_username = (
            bot_group,
            data_group,
            rules_username,
        )
        self.extra_groups, self.sudo_users = extra_groups, sudo_users
        self.client = telethon.TelegramClient(
            telethon.sessions.MemorySession(), api_id, api_hash
        )
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
        self.bot_backend = BotBackend(
            bot=self.client, group_id=self.main_group, api_id=None, api_hash=None
        )
        await self.bot_backend.init()
        await self.add_handlers()
        return self.client

    async def add_handlers(self):
        start = r"^(?:\/|!)"
        eoc = rf"(?:@{self.username}|(?=\s)|$)"
        data = r"(?:(?:#data_?)?(\d+))"
        username = r"(?:@?([a-zA-Z0-9_]{4,}|[0-9]+))"

        self.client.add_event_handler(
            self.ping_command, telethon.events.NewMessage(pattern=rf"{start}ping{eoc}")
        )
        self.client.add_event_handler(
            self.help_command, telethon.events.NewMessage(pattern=rf"{start}help{eoc}")
        )
        self.client.add_event_handler(
            self.chain_command,
            telethon.events.NewMessage(pattern=rf"{start}chain{eoc}(?:\s{data})?"),
        )
        self.client.add_event_handler(
            self.locate_command,
            telethon.events.NewMessage(
                pattern=rf"{start}locate{eoc}(?:\s{data})?(?:\s{username})?"
            ),
        )
        self.client.add_event_handler(
            self.notinchain_command,
            telethon.events.NewMessage(pattern=rf"{start}notinchain{eoc}(?:\s{data})?"),
        )
        self.client.add_event_handler(
            self.allchains_command,
            telethon.events.NewMessage(pattern=rf"{start}allchains{eoc}(?:\s{data})?"),
        )
        self.client.add_event_handler(
            self.fetchdata_command,
            telethon.events.NewMessage(
                pattern=rf"{start}(?:get|fetch)data{eoc}(?:\s{data})?"
            ),
        )
        self.client.add_event_handler(
            self.diff_command,
            telethon.events.NewMessage(
                pattern=rf"{start}tdiff{eoc}(?:\s{data}(?:\s{data})?)?"
            ),
        )
        self.client.add_event_handler(
            self.gdiff_command,
            telethon.events.NewMessage(
                pattern=rf"{start}gdiff{eoc}(?:\s{data}(?:\s{data})?)?(?:\s\.(\w+))?"
            ),
        )
        self.client.add_event_handler(
            self.link_command,
            telethon.events.NewMessage(
                pattern=rf"{start}(?:perma)?link{eoc}(?:\s{data})?(?:\s{username})?"
            ),
        )
        self.client.add_event_handler(
            self.start_command,
            telethon.events.NewMessage(pattern=rf"{start}start{eoc}(?:\s(.+))?"),
        )
        self.client.add_event_handler(
            self.logs_command,
            telethon.events.NewMessage(pattern=rf"{start}logs{eoc}(?:\s(\d+))?"),
        )
        self.client.add_event_handler(
            self.log_capacity_command,
            telethon.events.NewMessage(
                pattern=rf"{start}log_capacity{eoc}(?:\s(\d+))?"
            ),
        )
        self.client.add_event_handler(
            self.user_joined_admission,
            telethon.events.ChatAction(
                func=lambda event: event.user_joined or event.user_added,
                chats=self.admissions_group,
            ),
        )
        self.client.add_event_handler(
            self.user_joined_main,
            telethon.events.ChatAction(
                func=lambda event: event.user_joined or event.user_added,
                chats=self.main_group,
            ),
        )
        self.client.add_event_handler(
            self.user_joined_main,
            ChatActionJoinedByRequest(chats=self.main_group),
        )
        self.client.add_event_handler(
            self.callback_query, telethon.events.CallbackQuery()
        )
        self.client.add_event_handler(
            self.join_request,
            telethon.events.Raw(
                telethon.tl.types.UpdateBotChatInviteRequester,
                func=lambda event: telethon.utils.get_peer_id(event.peer, True)
                == self.main_group,
            ),
        )

    async def run(self, backend):
        self.backend = backend
        await self.client.send_message(self.bot_group, "🆙 and 🏃ing!")
        logger.info("Up and running!")
        await self.client.run_until_disconnected()

    @error_handler
    async def ping_command(self, event):
        await send(event, await tr(event, "pong"))

    @error_handler
    async def help_command(self, event):
        await send(event, await tr(event, "help"))

    @error_handler
    @protected
    async def locate_command(self, event):
        name = event.pattern_match[2]
        if not name:
            await send(event, await tr(event, "invalid_username"))
            return
        new = await send(event, await tr(event, "please_wait"))
        backend, _ = await self._select_backend(event, error=new)
        if not backend:
            return
        graph, chain = await core.get_chain(self.target, backend)
        data = await self._store_data(graph)
        filterfunc = get_user_filter(name)
        ret = filter(filterfunc, chain)
        try:
            ret = next(ret)
        except StopIteration:
            await send(new, (await tr(event, "user_not_found")).format(data))
            return
        i = chain.index(ret)
        segment = chain[max(0, i - 3) : i + 4]
        await send(
            new,
            (await tr(event, "chain_segment_format")).format(
                len(chain) - i,
                data,
                (await tr(event, "chain_delim")).join(
                    await format_user(segment, False)
                ),
            ),
        )

    @error_handler
    @protected
    async def chain_command(self, event):
        await self.get_chain(event)

    async def get_chain(self, event):
        new = await send(event, await tr(event, "please_wait"))
        backend, _ = await self._select_backend(event, error=new)
        if not backend:
            return
        graph, chain = await core.get_chain(self.target, backend)
        data = await self._store_data(graph)
        await send(
            new,
            (await tr(event, "chain_format")).format(
                f"#chain_{len(chain)} {data}",
                (await tr(event, "chain_delim")).join(
                    user for user in await format_user(chain, False)
                ),
            ),
            split_on=((" ", "\n"),),
        )
        return chain

    @error_handler
    @protected
    async def notinchain_command(self, event):
        new = await send(event, await tr(event, "please_wait"))
        backend, _ = await self._select_backend(event, error=new)
        if not backend:
            return
        graph, antichain = await core.get_notinchain(self.target, backend)
        data = await self._store_data(graph)
        await send(
            new,
            data
            + "\n"
            + "\n".join(
                await format_user(
                    (
                        user
                        for user in antichain
                        if user.id is not None and not user.deleted and user.usernames
                    ),
                    True,
                )
            ),
        )

    @error_handler
    @protected
    async def allchains_command(self, event):
        new = await send(event, await tr(event, "please_wait"))
        backend, _ = await self._select_backend(event, error=new)
        if not backend:
            return
        graph, chains = await core.get_chains(backend)
        data = await self._store_data(graph)
        out = [
            " ⇒ ".join(await format_user(chain, False))
            for chain in chains
            if len(chain) > 1
        ]
        await send(new, data + " " + "\n\n".join(out))

    @error_handler
    @protected
    async def fetchdata_command(self, event):
        data = event.pattern_match[1]
        if not data:
            await send(event, await tr(event, "invalid_id"))
            return
        data = await self._fetch_data(int(data))
        if not data:
            await send(event, await tr(event, "invalid_id"))
            return
        await event.reply(file=data)

    @error_handler
    @protected
    async def diff_command(self, event):
        new = await send(event, await tr(event, "please_wait"))
        old_backend, old_backend_id = await self._select_backend(
            event, default_backend=False, error=new
        )
        if old_backend is False:
            await send(new, await tr(event, "invalid_id"))
        if not old_backend:
            return
        new_backend, _ = await self._select_backend(event, 1, error=new)
        if not new_backend:
            return
        graph, diff = await core.get_diff(
            old_backend, new_backend, await tr(event, "diff_username_delim"), "\n"
        )
        data = await self._store_data(graph)
        (
            old_only_edges,
            new_only_edges,
            uid_edges,
            username_edges,
            old_only_names,
            new_only_names,
        ) = diff
        await send(
            new,
            (await tr(event, "diff_format")).format(
                await format_backend(event, old_backend_id),
                data,
                new_only_names,
                old_only_names,
                username_edges,
                uid_edges,
                new_only_edges,
                old_only_edges,
            ),
        )

    @error_handler
    @protected
    async def gdiff_command(self, event):
        new = await send(event, await tr(event, "please_wait"))
        old_backend, old_backend_id = await self._select_backend(
            event, default_backend=False, error=new
        )
        if old_backend is False:
            await send(new, await tr(event, "invalid_id"))
        if not old_backend:
            return
        new_backend, _ = await self._select_backend(event, 1, error=new)
        if not new_backend:
            return
        format = event.pattern_match[3]
        if format not in ALLOWED_FORMATS:
            format = "svgz"
        graph, diff = await core.get_gdiff(
            old_backend, new_backend, self.target, format
        )
        data = await self._store_data(graph)
        caption = (await tr(event, "gdiff_format")).format(
            await format_backend(event, old_backend_id), data
        )
        await event.reply(caption, file=diff, force_document=True)
        await new.delete()

    @error_handler
    @protected
    async def link_command(self, event):
        name = event.pattern_match[2]
        if not name:
            await send(event, await tr(event, "invalid_username"))
            return
        new = await send(event, await tr(event, "please_wait"))
        backend, _ = await self._select_backend(event, error=new)
        graph = await core.get_bios(backend)
        data = await self._store_data(graph)
        filterfunc = get_user_filter(name)
        ret = filter(filterfunc, map(node_to_user, graph.nodes.values()))
        try:
            ret = next(ret)
        except StopIteration:
            await send(new, (await tr(event, "user_not_found")).format(data))
            return
        await send(
            new,
            (await tr(event, "link_format")).format(await format_user(ret, True), data),
        )

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
                unescaped = "https://" + base64.urlsafe_b64decode(
                    encoded.encode("utf-8")
                ).decode("utf-8")
                await event.respond(
                    (await tr(event, "invite_format")).format(unescaped),
                    link_preview=False,
                )
                await self.client.delete_messages(
                    self.admissions_entity.id, int(msg[4:12], 16)
                )
                return
            if msg.startswith("help"):
                buttons = [
                    Button.url(
                        await tr(event, "return_to_group"),
                        "https://t.me/c/{}/{}".format(
                            self.admissions_entity.id, int(msg[5:13], 16)
                        ),
                    )
                ]
                if msg[4] == "s":
                    await event.respond(
                        (await tr(event, "start_help")).format(self.rules_username),
                        buttons=buttons,
                    )
                    return
                if msg[4] == "j":
                    await event.respond(
                        (await tr(event, "join_help")).format(msg[13:]), buttons=buttons
                    )
                    return
                if msg[4] == "u":
                    await event.respond(
                        await tr(event, "username_help"), buttons=buttons
                    )
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
                    # adapted from https://stackoverflow.com/a/41309213/5509575, CC BY-SA 4.0 by Rounin
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
                        "width: 100%;"
                        "}"
                        "code::before {"
                        'content: counter(listing) ". ";'
                        "display: block;"
                        "float: left;"
                        "text-align: right;"
                        "width: 4em;"
                        "margin-left: -4em;"
                        "}"
                        "code>br {"
                        "display: none;"
                        "}"
                        # end of CC BY-SA 4.0 code
                        # effectively adding a 1em margin below the element, but without affecting selections
                        "code::after {"
                        "height: 1em;"
                        "display: block;"
                        'content: "";'
                        "}"
                    )
                    .replace(": ", ":")
                    .replace(" {", "{")
                    .replace(";}", "}")
                    + "</style>"
                    "</head>"
                    "<body>"
                    '<pre class="code">\n' + "".join(entries) + "\n</pre>"
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
            capacity = event.pattern_match[1]
            if not capacity:
                await send(event, await tr(event, "invalid_log_capacity"))
                return
            capacity = int(capacity)
            log.getMemoryHandler().setCapacity(capacity)
            resp = "logs_capacity_updated"
        else:
            resp = "logs_forbidden"
        await send(event, await tr(event, resp))

    @error_handler
    async def user_joined_admission(self, event):
        cb = None
        if isinstance(event, telethon.events.ChatAction.Event) and (
            event.user_joined or event.user_added
        ):
            cb = event.user_id
        if isinstance(event, telethon.events.NewMessage.Event):
            if isinstance(event.from_id, telethon.tl.types.PeerUser):
                cb = event.from_id.user_id
            else:
                cb = None
        if cb is None:
            await send(event, await tr(event, "fix_anonymous"))
        else:
            cb = cb.to_bytes(8, "big")
            await send(
                event,
                await tr(event, "welcome_admission"),
                buttons=[Button.inline(await tr(event, "click_me"), b"s" + cb)],
            )

    async def join_request(self, event):
        await self.client(
            telethon.tl.functions.messages.EditExportedChatInviteRequest(
                self.main_group, event.invite.link, revoked=True
            )
        )
        try:
            await self.client(
                telethon.functions.messages.HideChatJoinRequestRequest(
                    self.main_group, event.user_id, True
                )
            )
        except telethon.errors.rpcerrorlist.UserAlreadyParticipantError:
            pass

    @error_handler
    async def user_joined_main(self, event):
        chain = await self.get_chain(event)
        if not any(event.user_id == user.id for user in chain):
            await self.client.kick_participant(self.main_group, event.user_id)

    @error_handler
    async def callback_query(self, event):
        for_user = int.from_bytes(event.data[1:9], "big")
        if for_user != event.sender_id and event.sender_id not in self.sudo_users:
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
            await message.edit(
                await tr(event, "please_click"),
                buttons=[
                    [
                        Button.url(
                            await tr(event, "rules_link"),
                            "https://t.me/" + self.rules_username,
                        )
                    ],
                    [
                        Button.inline(
                            await tr(event, "rules_accept"), b"j" + event.data[1:9]
                        )
                    ],
                    [
                        Button.inline(
                            await tr(event, "rules_reject"), b"c" + event.data[1:9]
                        )
                    ],
                    [
                        Button.inline(
                            await tr(event, "get_help"), b"h" + event.data[1:9] + b"s"
                        )
                    ],
                ],
            )
        except telethon.errors.rpcerrorlist.MessageNotModifiedError:
            pass
        await event.answer(
            (await tr(event, "read_rules")).format(self.rules_username), alert=True
        )

    async def callback_query_join(self, event, message):
        try:
            await message.edit(await tr(event, "loading_1m"), buttons=None)
        except telethon.errors.rpcerrorlist.MessageNotModifiedError:
            await event.answer(await tr(event, "button_loading"))
            return
        input_entity = await event.get_input_sender()
        if not input_entity:
            # testmode support
            await event.answer(await tr(event, "start_bot"), alert=True)
            await message.edit(
                await tr(event, "please_click"),
                buttons=[
                    [Button.inline(await tr(event, "continue"), event.data)],
                    [Button.inline(await tr(event, "cancel"), b"c" + event.data[1:9])],
                    [
                        Button.inline(
                            await tr(event, "get_help"), b"h" + event.data[1:9] + b"s"
                        )
                    ],
                ],
            )
            return
        graph, chain = await core.get_chain(self.target, self.backend)
        if input_entity.user_id in {user.id for user in chain}:
            try:
                await event.answer(await tr(event, "already_in_chain"), alert=True)
            except telethon.errors.rpcerrorlist.QueryIdInvalidError:
                pass
            await message.edit(await tr(event, "already_in_chain"), buttons=None)
            return
        await self.callback_query_done(
            event,
            message,
            b"d"
            + event.data[1:9]
            + int(time.time()).to_bytes(8, "big")
            + chain[0].usernames[0].encode("ascii"),
        )

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
            bio = [
                username.casefold()
                for username in get_bio_links(
                    await self.bot_backend.get_bio_text(
                        self.bot_backend.get_user(entity)
                    )
                )
            ]
        if skip or data[17:].decode("ascii").casefold() not in bio:
            await message.edit(
                await tr(event, "please_click"),
                buttons=[
                    [Button.inline(await tr(event, "continue"), data)],
                    [Button.inline(await tr(event, "cancel"), b"c" + data[1:9])],
                    [
                        Button.inline(
                            await tr(event, "get_help"),
                            b"h" + data[1:9] + b"j" + data[17:],
                        )
                    ],
                ],
            )
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
            await message.edit(
                await tr(message, "please_click"),
                buttons=[
                    [Button.inline(await tr(message, "continue"), data)],
                    [Button.inline(await tr(message, "cancel"), b"c" + data[1:9])],
                    [
                        Button.inline(
                            await tr(message, "get_help"), b"h" + data[1:9] + b"u"
                        )
                    ],
                ],
            )
            return
        invite = await self.client(
            telethon.tl.functions.messages.ExportChatInviteRequest(
                self.main_group,
                expire_date=datetime.timedelta(hours=1),
                request_needed=True,
            )
        )
        escaped = (
            base64.urlsafe_b64encode(
                invite.link.removeprefix("https://").encode("utf-8")
            )
            .decode("utf-8")
            .replace("=", "")
        )
        try:
            await event.answer(
                url="t.me/{}?start=invt{:08X}{}".format(
                    self.username, message.id, escaped
                )
            )
        except telethon.errors.rpcerrorlist.QueryIdInvalidError:
            pass
        await message.edit(
            await tr(message, "please_click"),
            buttons=[
                [Button.inline(await tr(message, "continue"), data)],
                [Button.inline(await tr(message, "cancel"), b"c" + data[1:9])],
                [
                    Button.inline(
                        await tr(message, "get_help"),
                        b"h" + data[1:9] + b"j" + data[17:],
                    )
                ],
            ],
        )

    async def callback_query_help(self, event, message):
        await event.answer(
            url="t.me/{}?start=help{}{:08X}{}".format(
                self.username,
                event.data[9:10].decode("ascii"),
                message.id,
                event.data[10:].decode("ascii"),
            )
        )

    async def callback_query_cancel(self, event, message):
        await event.answer(await tr(message, "cancelled"), alert=True)
        await message.delete()

    async def _select_backend(
        self, event, match_id=0, *, error=None, default_backend=None
    ):
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
            return None, None
        except IndexError:
            pass
        if data_id is None and getattr(event, "is_reply", False) and not match_id:
            reply = await event.get_reply_message()
            if getattr(getattr(reply, "file", None), "name", None) in FILE_NAMES:
                if event.sender_id in self.sudo_users:
                    return (await reply.download_media(bytes), reply.file.name), "file"
                else:
                    await send(error, await tr(error, "untrusted_forbidden"))
                    return None, None
            if data_id is None:
                try:
                    data_id = int(re.search(r"\s#data_?(\d+)\s", reply.text)[0])
                except (ValueError, TypeError, IndexError):
                    pass
        if data_id is None:
            return default_backend, "default"
        data = await self._fetch_data(data_id)
        if data is None:
            await send(error, await tr(event, "invalid_id"))
            return None, None
        return (await data.download_media(bytes), data.file.name), data_id

    async def _fetch_data(self, data_id):
        ret = await self.client.get_messages(self.data_group, ids=data_id)
        logger.debug("Data file %r", ret)
        if getattr(getattr(ret, "file", None), "name", None) not in FILE_NAMES:
            return None
        return ret

    async def _store_data(self, graph):
        graph = graph.copy()
        await self.client.get_participants(self.main_group)
        for node, data in graph.nodes.items():
            if data["uid"] and not data.get("access_hash", None):
                try:
                    entity = await self.client.get_input_entity(
                        telethon.tl.types.PeerUser(data["uid"])
                    )
                except (ValueError, TypeError):
                    entity = None
                if isinstance(entity, telethon.tl.types.InputPeerUser):
                    data["access_hash"] = entity.access_hash
        data = io.BytesIO()
        data.name = "chain.gml"
        core.write(graph, data)
        data.seek(0)
        message = await self.client.send_message(self.data_group, file=data)
        return "#data_{}".format(message.id)
