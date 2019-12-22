from .. import backends
import aiohttp
from lxml import html
import asyncio


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
