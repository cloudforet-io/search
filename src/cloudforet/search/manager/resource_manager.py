import logging
from typing import Tuple, Union

from spaceone.core.manager import BaseManager

from cloudforet.search.lib.pymongo_client import SpaceONEPymongoClient

_LOGGER = logging.getLogger(__name__)


class ResourceManager(BaseManager):
    client = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.client = SpaceONEPymongoClient()

    def search_resource(
        self, query_filter: dict, resource_type: str, limit: int
    ) -> list:
        collection_name = self._get_collection_name(resource_type)
        result = list(
            self.client[collection_name].service_account.find(
                filter=query_filter, limit=limit
            )
        )
        _LOGGER.debug(f"[search] query_filter: {query_filter}")

        return result

    @staticmethod
    def _get_collection_name(resource_type: str) -> str:
        service = resource_type.split(".")[0].lower()

        if prefix := SpaceONEPymongoClient.prefix:
            return f"{prefix}{service}"
        else:
            return service
