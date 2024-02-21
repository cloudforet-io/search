import logging
import re

from spaceone.core.error import *
from spaceone.core.service import *
from spaceone.core.service.utils import *

from cloudforet.search.manager.resource_manager import ResourceManager
from cloudforet.search.model.resource.response import *
from cloudforet.search.model.resource.request import *

_LOGGER = logging.getLogger(__name__)


@authentication_handler
@authorization_handler
@mutation_handler
@event_handler
class ResourceService(BaseService):
    resource = "Resource"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.resource_manager = ResourceManager()

    @transaction(
        permission="search:Resource.read",
        role_types=["DOMAIN_ADMIN", "WORKSPACE_OWNER", "WORKSPACE_MEMBER"],
    )
    @convert_model
    def search(self, params: ResourceSearchRequest) -> Union[ResourcesResponse, dict]:
        """Search resources
        Args:
            params (ResourceSearchRequest): {
                'resource_type': 'str',     # required
                'keyword': 'str',
                'limit': 'int',
                'all_workspaces': 'bool',
                'next_token': 'str'
                'workspace_id': 'str'       # injected from auth
                'domain_id': 'str'          # injected from auth
                'user_projects': 'list'     # injected from auth
            }
        Returns:
            ResourcesResponse:
        """

        permissions = self.transaction.meta.get("authorization.permissions", [])
        regex_pattern = re.compile(f".*{params.keyword}.*", re.IGNORECASE | re.DOTALL)
        query_filter = {}

        if params.all_workspaces:
            pass

        if params.resource_type == "identity.ServiceAccount":
            query_filter = {
                "domain_id": params.domain_id,
                "$or": [
                    {"name": {"$regex": regex_pattern}},
                    {"provider": {"$regex": regex_pattern}},
                ],
            }

            if params.workspace_id:
                query_filter["workspace_id"] = params.workspace_id
            if params.user_projects:
                query_filter["project_id"] = {"$in": params.user_projects}

        result = self.resource_manager.search_resource(
            query_filter, params.resource_type, params.limit
        )

        response = {
            "results": result,
            "next_token": None,
        }

        return ResourcesResponse(**response)
