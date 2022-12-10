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

import aiohttp
from lxml import html

from ..backend import BioTextGetterBackend, Unavailable


class ScraperBackend(BioTextGetterBackend):
    def __init__(self):
        self._setup_logging()
        self.session = aiohttp.ClientSession(raise_for_status=True)

    @classmethod
    def get_instances(cls, bot, common_config, configs):
        return [cls() for _ in configs]

    async def get_bio_text(self, user):
        if not user.usernames:
            raise Unavailable("A username is required to scrape.", retry_elsewhere=True)
        async with self.session.get("https://t.me/" + user.usernames[0]) as resp:
            text = await resp.text()
        tree = html.fromstring(text)
        if tree.xpath(
            "//div[contains(concat(' ',normalize-space(@class),' '),' tgme_page_description ')]/a[contains(concat(' ',normalize-space(@class),' '),' tgme_username_link ')]"
        ):
            # This happens if the username doesn't exist or if we're being rate-limited.
            # Since the user should always exit, we must be rate limited
            raise Unavailable("Rate limited.", 1, True)
        desc = tree.xpath(
            "//div[contains(concat(' ',normalize-space(@class),' '),' tgme_page_description ')]//node()",
            smart_strings=False,
        )
        return "".join(
            (isinstance(e, str) and e) or (e.tag == "br" and "\n") or "" for e in desc
        )

    async def close(self):
        if self.session is not None:
            await self.session.close()
            self.session = None
