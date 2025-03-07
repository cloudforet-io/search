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

            cls.prefix = cls.config.get("default").get(
                "db_prefix"
            ) or config.get_global("DATABASE_NAME_PREFIX")

            default_db_conf = cls.config.get("default")
            username = default_db_conf.get("username")
            password = default_db_conf.get("password")
            host = default_db_conf.get("host")
            port = default_db_conf.get("port")

            if not host.startswith("mongodb://") and not host.startswith(
                "mongodb+srv://"
            ):
                protocol = "mongodb"
            else:
                protocol, host = host.split("://")

            cls._client = MongoClient(
                f"{protocol}://{username}:{password}@{host}", port=port
            )

            _LOGGER.debug(
                f"[__new__] Create pymongo client prefix: {cls.prefix}, protocol: {protocol})"
            )
        return cls._client

    @classmethod
    def get_client(cls):
        return cls._client
