from abc import abstractmethod

class Backend:
    @classmethod
    @abstractmethod
    def get_instances(cls, common_config, configs):
        """Return an iterable of instances that implement Backend"""

    async def init(self):
        """Initialise the class"""

    @abstractmethod
    async def get_joined_users(self):
        """Fetch the users in the group, returning an iterable"""
        raise Unavailable("Not implemented.")

    @abstractmethod
    async def get_bio_links(self, uid, username):
        """Return an iterable of usernames present in the bio, excluding the @"""

    async def close(self):
        """Prepare for destruction"""


class Unavailable(RuntimeError):
    def __init__(self, *args, **kwargs):
        if "until" in kwargs.keys():
            self.until = until
            del kwargs["until"]
        super().__init__(*args, **kwargs)
