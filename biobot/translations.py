import json


with open("translations.json") as file:
    translations = json.load(file)

async def translate(message, key):
    sender = getattr(message, "get_sender", getattr(message, "get_user", None))
    ret = translations.get((await sender()).lang_code, {}).get(key, None)
    if ret is None:
        ret = translations["en"].get(key, "missing translation for {}".format(key))
    return ret

tr = translate
