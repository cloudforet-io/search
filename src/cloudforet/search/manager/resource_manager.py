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
        self,
        domain_id: str,
        query_filter: dict,
        resource_type: str,
        limit: int,
        page: int,
    ) -> list:
        db_name, collection_name = self._get_collection_and_db_name(resource_type)
        skip_count = page * limit

        results = list(
            self.client[db_name][collection_name].find(
                filter=query_filter, limit=limit, skip=skip_count
            )
        )

        if resource_type == "identity.Project":
            project_group_ids = [result.get("project_group_id") for result in results]
            project_group_map = self.get_project_group_map(domain_id, project_group_ids)
            for result in results:
                if pg_id := result.get("project_group_id"):
                    _name = result.get("name")
                    result["name"] = f"{project_group_map.get(pg_id)} > {_name}"

        _LOGGER.debug(f"[search] query_filter: {query_filter}")

        return results

    def list_public_project(self, domain_id: str, workspace_id: str) -> list:
        db_name, collection_name = self._get_collection_and_db_name("identity.Project")
        response = list(
            self.client[db_name][collection_name].find(
                {
                    "domain_id": domain_id,
                    "project_type": "PUBLIC",
                    "workspace_id": workspace_id,
                }
            )
        )
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
        return response

    def _get_collection_and_db_name(self, resource_type: str) -> Tuple[str, str]:
        service, resource = resource_type.split(".")

        collection_name = self._pascal_to_snake_case(resource)
        db_name = service.lower()
        if prefix := SpaceONEPymongoClient.prefix:
            db_name = f"{prefix}{db_name}"
        else:
            db_name = service

        return db_name, collection_name

    def get_project_group_map(self, domain_id: str, project_group_ids: list) -> dict:
        db_name, collection_name = self._get_collection_and_db_name(
            "identity.ProjectGroup"
        )
        response = list(
            self.client[db_name][collection_name].find(
                {
                    "domain_id": domain_id,
                    "project_group_id": {"$in": project_group_ids},
                }
            )
        )
        project_group_map = {pg["project_group_id"]: pg["name"] for pg in response}

        return project_group_map

    @staticmethod
    def _pascal_to_snake_case(pascal_case: str):
        snake_case = re.sub("([a-z0-9])([A-Z])", r"\1_\2", pascal_case)
        return snake_case.lower()
