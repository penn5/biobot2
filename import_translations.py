#!/usr/bin/env python3

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

json.dump(data, open("translations.json", "w"))

if needs_write:
    with open("poeditor_api_token.txt", "w") as token_file:
        token_file.write(token + "\n" + str(project))
