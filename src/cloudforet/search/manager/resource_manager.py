import logging
import re
from typing import Tuple

from spaceone.core.manager import BaseManager

from cloudforet.search.lib.pymongo_client import SpaceONEPymongoClient

_LOGGER = logging.getLogger(__name__)


class ResourceManager(BaseManager):
    client = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.client = SpaceONEPymongoClient()

    def search_resource(
        self, query_filter: dict, resource_type: str, limit: int, page: int
    ) -> list:
        db_name, collection_name = self._get_collection_and_db_name(resource_type)
        skip_count = page * limit

        result = list(
            self.client[db_name][collection_name].find(
                filter=query_filter, limit=limit, skip=skip_count
            )
        )
        _LOGGER.debug(f"[search] query_filter: {query_filter}")

        return result

    def list_public_project(self, domain_id: str, workspace_id: str) -> list:
        db_name, collection_name = self._get_collection_and_db_name("identity.Project")
        print(db_name, collection_name)
        response = list(
            self.client["dev2-identity"].project.find(
                {
                    "domain_id": domain_id,
                    "project_type": "PUBLIC",
                    "workspace_id": workspace_id,
                }
            )
        )
        print(response)
        return response

    def list_private_project(
        self,
        domain_id: str,
        workspace_id: str,
        user_id: str,
    ) -> list:
        db_name, collection_name = self._get_collection_and_db_name("identity.Project")
        response = list(
            self.client[db_name][collection_name].find(
                {
                    "domain_id": domain_id,
                    "users": {"$in": [user_id]},
                    "project_type": "PRIVATE",
                    "workspace_id": workspace_id,
                }
            )
        )
        print("list_private_project")
        print(response)
        return response

    def _get_collection_and_db_name(self, resource_type: str) -> Tuple[str, str]:
        service, resource = resource_type.split(".")
        db_info = SpaceONEPymongoClient.config.get(service.lower())

        collection_name = self._pascal_to_snake_case(resource)
        if prefix := SpaceONEPymongoClient.prefix:
            db_name = f"{prefix}{db_info['db']}"
        else:
            db_name = service

        return db_name, collection_name

    @staticmethod
    def _pascal_to_snake_case(pascal_case: str):
        snake_case = re.sub("([a-z0-9])([A-Z])", r"\1_\2", pascal_case)
        return snake_case.lower()
