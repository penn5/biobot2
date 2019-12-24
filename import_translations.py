#!/usr/bin/env python3

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

import poeditor
import json
import io


try:
    token = open("poeditor_api_token.txt")
except FileNotFoundError:
    token = input("Enter your POEditor API token: ")
    project = input("Enter your POEditor project ID: ")
    needs_write = True
else:
    token, project = token.readlines()
    needs_write = False

int(token, 16)
project = int(project)

api = poeditor.POEditorAPI(api_token=token)
langs = api.list_project_languages(project)
print(langs)
data = {}
for lang in langs:
    with io.BytesIO() as out:
        api.export(project, lang["code"], "json", filters=["translated", "not_fuzzy"], local_file=out)
        out.seek(0)
        exported = json.load(out)
    data.setdefault(lang["code"][:2], {}).update({term["term"]: term["definition"] for term in exported})

json.dump(data, open("translations.json", "w"), indent=2, sort_keys=True)

if needs_write:
    with open("poeditor_api_token.txt", "w") as token_file:
        token_file.write(token + "\n" + str(project))
