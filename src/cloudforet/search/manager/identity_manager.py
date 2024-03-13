import logging

from spaceone.core import cache
from spaceone.core.manager import BaseManager
from spaceone.core.connector.space_connector import SpaceConnector

_LOGGER = logging.getLogger("spaceone")


class IdentityManager(BaseManager):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.identity_conn: SpaceConnector = self.locator.get_connector(
            SpaceConnector, service="identity"
        )

    @cache.cacheable(
        key="search:workspaces:{domain_id}:{user_id}",
        expire=180,
    )
    def get_workspaces(self, domain_id: str, user_id: str) -> dict:
        return self.identity_conn.dispatch("UserProfile.get_workspaces")

    def list_workspace(self, query: dict) -> dict:
        return self.identity_conn.dispatch("Workspace.list", {"query": query})
