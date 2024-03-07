import logging

from spaceone.core import config
from pymongo import MongoClient

_LOGGER = logging.getLogger("spaceone")


class SpaceONEPymongoClient:
    config = None
    prefix = None
    _client = None

    # todo: need to apply service config
    def __new__(cls, *args, **kwargs):
        if not cls._client:
            cls.config = config.get_global(
                "PYMONGO_DATABASES", config.get_global("DATABASES")
            )

            if _db_prefix := cls.config.get("default").get("db_prefix"):
                cls.prefix = cls.config.get("db_prefix")
            elif _db_prefix := config.get_global("DATABASE_NAME_PREFIX"):
                cls.prefix = _db_prefix

            default_db_conf = cls.config.get("default")
            username = default_db_conf.get("username")
            password = default_db_conf.get("password")
            protocol, host = default_db_conf.get("host").split("://")

            cls._client = MongoClient(f"{protocol}://{username}:{password}@{host}")

            _LOGGER.debug(f"[__new__] Create pymongo client prefix: {cls.prefix}")
        return cls._client

    @classmethod
    def get_client(cls):
        return cls._client
