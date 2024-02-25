import base64
import logging
import re

from spaceone.core.error import *
from spaceone.core.service import *
from spaceone.core.service.utils import *

from cloudforet.search.manager.resource_manager import ResourceManager
from cloudforet.search.manager.identity_manager import IdentityManager
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
                'workspaces': 'list',
                'all_workspaces': 'bool',
                'next_token': 'str'
                'workspace_id': 'str'       # injected from auth
                'domain_id': 'str'          # injected from auth
                'user_projects': 'list'     # injected from auth
            }
        Returns:
            ResourcesResponse:
        """

        # permissions = self.transaction.meta.get("authorization.permissions", [])
        user_id = self.transaction.meta.get("authorization.user_id")
        owner_type = self.transaction.meta.get("authorization.owner_type")
        role_type = self.transaction.meta.get("authorization.role_type")

        domain_id = params.domain_id
        workspaces = [params.workspace_id] if params.workspace_id else []
        resource_type = params.resource_type
        next_token = params.next_token
        page = 0

        workspace_project_map = {}
        query_filter = {"domain_id": domain_id, "$or": []}

        if next_token:
            next_token = self._decode_next_token(resource_type, next_token)
            params.limit = next_token.get("limit")
            query_filter = next_token.get("query_filter")
            page = next_token.get("page")

        elif owner_type == "USER":
            identity_mgr: IdentityManager = self.locator.get_manager("IdentityManager")
            if role_type != "DOMAIN_ADMIN":
                workspaces_info = identity_mgr.get_workspaces(domain_id, user_id)
                workspace_ids = [
                    info["workspace_id"] for info in workspaces_info.get("results", [])
                ]

                if params.all_workspaces:
                    workspaces = workspace_ids
                elif workspaces:
                    # check is accessible workspace with params.workspaces
                    workspaces = list(set(workspaces) & set(workspace_ids))
                    for workspace_id in workspaces:
                        user_projects = self._get_all_projects(
                            domain_id, workspace_id, user_id
                        )
                        workspace_project_map[workspace_id] = user_projects

            if workspace_project_map:
                for workspace_id, user_projects in workspace_project_map.items():
                    query_filter["$or"].append(
                        {
                            "workspace_id": workspace_id,
                            "project_id": {"$in": user_projects},
                        }
                    )
            elif workspaces:
                query_filter["workspace_id"] = {"$in": workspaces}

            if params.user_projects:
                query_filter["project_id]"] = {"$in": params.user_projects}

        regex_pattern = re.compile(params.keyword, re.IGNORECASE)

        if params.resource_type == "identity.ServiceAccount":
            query_filter["$or"].append({"name": {"$regex": regex_pattern}})
            query_filter["$or"].append({"provider": {"$regex": regex_pattern}})

        result = self.resource_manager.search_resource(
            query_filter, resource_type, params.limit, page
        )

        next_token = self._encode_next_token_base64(
            result, resource_type, query_filter, params.limit, page
        )

        response = {
            "results": result,
            "next_token": next_token,
        }

        return ResourcesResponse(**response)

    def _get_all_projects(
        self, domain_id: str, workspace_id: str, user_id: str = None
    ) -> list:
        user_projects = []

        public_projects_info = self.resource_manager.list_public_project(
            domain_id, workspace_id
        )
        user_projects.extend(
            [project_info["project_id"] for project_info in public_projects_info]
        )

        private_projects_info = self.resource_manager.list_private_project(
            domain_id,
            workspace_id,
            user_id,
        )

        user_projects.extend(
            [project_info["project_id"] for project_info in private_projects_info]
        )

        return user_projects

    @staticmethod
    def _encode_next_token_base64(
        result: list,
        resource_type: str,
        query_filter: dict,
        limit: int,
        page: int,
    ) -> Union[str, None]:
        if limit == 0 or len(result) != limit:
            return None

        next_token = {
            "resource_type": resource_type,
            "query_filter": query_filter,
            "limit": limit,
            "page": page + 1,
        }

        next_token = base64.b64encode(str(next_token).encode()).decode("utf-8")
        return next_token

    @staticmethod
    def _decode_next_token(resource_type: str, next_token: str) -> dict:
        next_token = eval(base64.b64decode(next_token).decode("utf-8"))
        if next_token.get("resource_type") != resource_type:
            raise ERROR_INVALID_PARAMETER(key="resource_type")
        return next_token
