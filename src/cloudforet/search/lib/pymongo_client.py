import logging
import urllib.parse

from spaceone.core import config
from pymongo import MongoClient

_LOGGER = logging.getLogger(__name__)


class SpaceONEPymongoClient:
    _client = None
    prefix = None
    config = None

    def __new__(cls, *args, **kwargs):
        if not cls._client:
            cls.config = config.get_global("PYMONGO_DATABASES")
            pymongo_config = cls.config.get("common")
            username = pymongo_config.get("username")
            password = pymongo_config.get("password")
            protocol, host = pymongo_config.get("host").split("://")

            cls._client = MongoClient(f"{protocol}://{username}:{password}@{host}")
            if prefix := pymongo_config.get("db_prefix"):
                cls.prefix = prefix

            _LOGGER.debug(f"[__new__] Create pymongo client prefix: {cls.prefix}")
        return cls._client

    # property
    @classmethod
    def get_client(cls):
        return cls._client
