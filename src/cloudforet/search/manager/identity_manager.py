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

    @cache.cacheable(
        key="search:workspaces:{domain_id}:{user_id}",
        expire=180,
        alias="local",
    )
    def get_workspaces(self, domain_id: str, user_id: str) -> dict:
        return self.identity_conn.dispatch("UserProfile.get_workspaces")
