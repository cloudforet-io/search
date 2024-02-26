import base64
import logging
import re

from spaceone.core import config
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
        self.search_conf = self._get_search_conf()
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
        workspaces = self._get_accessible_workspaces(
            domain_id, user_id, params.workspaces, params.all_workspaces
        )
        resource_type = params.resource_type
        next_token = params.next_token
        page = 0

        workspace_project_map = {}
        query_filter = {"$and": [{"domain_id": domain_id}]}

        if next_token:
            next_token = self._decode_next_token(resource_type, next_token)
            params.limit = next_token.get("limit")
            query_filter = next_token.get("query_filter")
            page = next_token.get("page")

        elif owner_type == "USER":
            if role_type != "DOMAIN_ADMIN":
                if params.all_workspaces:
                    workspaces = self._get_all_workspace_ids(domain_id, user_id)
                elif workspaces:
                    for workspace_id in workspaces:
                        user_projects = self._get_all_projects(
                            domain_id, workspace_id, user_id
                        )
                        workspace_project_map[workspace_id] = user_projects

        if workspace_project_map:
            or_filter = {"$or": []}
            for workspace_id, user_projects in workspace_project_map.items():
                or_filter["$or"].append(
                    {
                        "workspace_id": workspace_id,
                        "project_id": {"$in": user_projects},
                    }
                )
                query_filter["$and"].append(or_filter)
        elif workspaces:
            query_filter["$and"].append({"workspace_id": {"$in": workspaces}})
        elif params.workspace_id:
            query_filter["$and"].append({"workspace_id": params.workspace_id})

        regex_pattern = re.compile(params.keyword, re.IGNORECASE)

        if search_target := self.search_conf.get(resource_type):
            or_filter = {"$or": []}
            for keyword in search_target["request"]["search"]:
                or_filter["$or"].append({keyword: {"$regex": regex_pattern}})
            query_filter["$and"].append(or_filter)
        else:
            raise ERROR_INVALID_PARAMETER(key="resource_type")

        results = self.resource_manager.search_resource(
            domain_id, query_filter, resource_type, params.limit, page
        )

        next_token = self._encode_next_token_base64(
            results, resource_type, query_filter, params.limit, page
        )

        response = self._make_response(results, next_token, search_target["response"])

        return ResourcesResponse(**response)

    def _get_all_workspace_ids(self, domain_id: str, user_id: str) -> list:
        identity_mgr: IdentityManager = self.locator.get_manager("IdentityManager")
        workspaces_info = identity_mgr.get_workspaces(domain_id, user_id)
        workspace_ids = [
            info["workspace_id"] for info in workspaces_info.get("results", [])
        ]
        return workspace_ids

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

    def _get_accessible_workspaces(
        self,
        domain_id: str,
        user_id: str,
        workspaces: Union[list, None],
        all_workspaces: Union[bool, None],
    ) -> list:
        if not all_workspaces or not workspaces:
            return []

        # check is accessible workspace with params.workspaces
        workspace_ids = self._get_all_workspace_ids(domain_id, user_id)
        workspaces = list(set(workspaces) & set(workspace_ids))

        return workspaces

    @staticmethod
    def _make_response(results: list, next_token: str, response_conf) -> dict:
        response_format = response_conf["name"]
        for result in results:
            result["name"] = response_format.format(**result)
            result["resource_id"] = result[response_conf["resource_id"]]

        return {
            "results": results,
            "next_token": next_token,
        }

    @staticmethod
    def _encode_next_token_base64(
        results: list,
        resource_type: str,
        query_filter: dict,
        limit: int,
        page: int,
    ) -> Union[str, None]:
        if limit == 0 or len(results) != limit:
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

    @staticmethod
    def _get_search_conf() -> dict:
        package = config.get_package()
        search_conf_module = __import__(
            f"{package}.conf.search_conf", fromlist=["search_conf"]
        )
        return getattr(search_conf_module, "RESOURCE_TYPES", [])
