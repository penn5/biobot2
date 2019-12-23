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

from .. import backends
import aiohttp
from lxml import html


class ScraperBackend(backends.Backend):
    def __init__(self):
        self.session = aiohttp.ClientSession(raise_for_status=True)

    @classmethod
    def get_instances(cls, common_config, configs):
        return [cls()]

    async def get_bio_links(self, uid, username):
        if username is None:
            raise backends.Unavailable("A username is required to scrape.")
        async with self.session.get("https://t.me/"+username) as resp:
            text = await resp.text()
        tree = html.fromstring(text)
        if tree.xpath("//div[@class='tgme_page_description']/a[@class='tgme_username_link']"):
            # This happens if the username doesnt exist, OR we"re being rate-limited.
            raise backends.Unavailable("Might be rate limited.")
        ret = tree.xpath("//div[@class='tgme_page_description ']/a[starts-with(@href, 'https://t.me/')]/text()")
        return [x[1:] for x in ret]

    async def close(self):
        await self.session.close()
        del self.session
