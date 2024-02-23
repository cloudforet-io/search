import logging

from spaceone.core import cache
from spaceone.core import config
from spaceone.core.manager import BaseManager
from spaceone.core.connector.space_connector import SpaceConnector
from spaceone.core.auth.jwt.jwt_util import JWTUtil

_LOGGER = logging.getLogger(__name__)


class IdentityManager(BaseManager):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.identity_conn: SpaceConnector = self.locator.get_connector(
            SpaceConnector, service="identity"
        )

    @cache.cacheable("search:workspaces:{domain_id}:{user_id}", expire=300)
    def get_workspaces(self, domain_id: str, user_id: str) -> dict:
        return self.identity_conn.dispatch("UserProfile.get_workspaces")

    def check_workspace(self, workspace_id: str, domain_id: str) -> None:
        system_token = config.get_global("TOKEN")

        self.identity_conn.dispatch(
            "Workspace.check",
            {"workspace_id": workspace_id, "domain_id": domain_id},
            token=system_token,
        )

    def grant_token(
        self,
        params: dict,
    ) -> str:
        token_info = self.identity_conn.dispatch("Token.grant", params)
        return token_info["access_token"]
