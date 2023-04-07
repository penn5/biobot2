# biobot2

This Telegram bot is for managing the [bio chain](https://t.me/bio_chain_2).

## Architecture

### Backends

Each backend is able to provide either group member listing or bio text retrieval. They are managed by the backend manager, which distributes tasks, handles errors and backoffs, and generally coordinates that kind of stuff. It can remove broken backends from the pool but will not currently recreate them. If there are no working backends left, the process dies.

#### UserbotBackend

This backend logs in as a Telegram user (which must be a member of the chain's group) and fetches both members and bios.

#### BotBackend

This is a subclass of the userbot backend which uses a bot rather than a user.

#### ScraperBackend

This backend scrapes t.me using XPath to get bio texts. It can't get the member listings.

### Frontend

The entire frontend of the bot is in one big `bot.py` file. It's quite ugly but it works well.

### Data processing and algorithms

All the other data processing is in `chain.py` and `diff.py`. There is lots of complicated stuff there.

The algorithm used to find the longest chain is a BFS that searches for the longest path. Paths that use the same edge multiple times are pruned.

Diffs are calculated with set operations which in themselves are not very complicated, but there are many quirks. A user may have 0--many usernames and 0--1 IDs, and the correspondences may change between the data being compared. For clarity some data is excluded in some diff modes.

## Usage

### Configuration

Unfortunately the configuration files are written in JSON. Oops. However, they are structured quite elegantly. Be careful, an untrusted config file may lead to code execution. Here is an example (there is another in `config.sample.json`):

```json
{
  "common": {
    "group_id": -100123456789
  },
  "frontend": {
    "api_id": 12345,
    "api_hash": "0123456789ABCDEF",
    "bot_token": "123456789:ABCDEF",
    "admissions_group": -100223456789,
    "bot_group": -100323456789,
    "data_group": -100423456789,
    "rules_username": "username"
  },
  "backend": {
    "BotBackend": [
      {
        "bot": null,
        "api_id": 12345,
        "api_hash": "0123456789ABCDEF"
      }, {
        "bot": "223456789:ABCDEF",
        "api_id": 12345,
        "api_hash": "0123456789ABCDEF"
      }
    ],
    "ScraperBackend": [
      {}
    ],
    "UserbotBackend": [
      {
        "phone": "+888123456789",
        "api_id": 12345,
        "api_hash": "0123456789ABCDEF"
      }
    ]
  }
}
```

### Running

Install the `requirements.txt` and run the program with `python3 -m biobot2`. Alternatively, use podman.
