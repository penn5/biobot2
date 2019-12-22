import json


with open("translations.json") as file:
    translations = json.load(file)

async def translate(message, key):
    ret = translations.get((await message.get_sender()).lang_code, {}).get(key, None)
    if ret is None:
        ret = translations["en"].get(key, "missing translation for {}".format(key))
    return ret

tr = translate
