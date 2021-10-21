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

import json


with open("translations.json") as file:
    translations = json.load(file)


async def translate(message, key):
    sender = getattr(message, "get_sender", getattr(message, "get_user", lambda: None))
    ret = translations.get(getattr(await sender(), "lang_code", None), {}).get(key, None)
    if ret is None:
        ret = translations.get("en", {}).get(key, "missing translation for {}".format(key))
    return ret


tr = translate
