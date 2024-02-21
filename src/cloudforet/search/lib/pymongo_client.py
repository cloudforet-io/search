import logging
import urllib.parse

from spaceone.core import config
from pymongo import MongoClient

_LOGGER = logging.getLogger(__name__)


class SpaceONEPymongoClient(object):
    _client = None
    prefix = None

    def __new__(cls, *args, **kwargs):
        if not cls._client:
            search_database = config.get_global("SEARCH_DATABASE").get("default")
            username = urllib.parse.quote_plus(search_database.get("username"))
            password = urllib.parse.quote_plus(search_database.get("password"))
            protocol, host = search_database.get("host").split("://")

            cls._client = MongoClient(f"{protocol}://{username}:{password}@{host}")
            if prefix := search_database.get("prefix"):
                cls.prefix = prefix

            _LOGGER.debug(f"[__new__] Create pymongo client prefix: {cls.prefix}")
        return cls._client

    @classmethod
    def get_client(cls):
        return cls._client
