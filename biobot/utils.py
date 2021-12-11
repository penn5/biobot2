from telethon._tl import PeerUser, PeerChat, PeerChannel


def config_to_peer(data):
    if data["type"] == "user":
        c = PeerUser
    elif data["type"] == "chat":
        c = PeerChat
    elif data["type"] == "channel":
        c = PeerChannel
    else:
        raise ValueError(f"Unknown {data}")
    return c(data["id"])
