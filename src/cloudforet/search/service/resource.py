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

        self.check_resource_type(params.resource_type)

        domain_id = params.domain_id
        workspaces = self._get_accessible_workspaces(
            domain_id, user_id, params.workspaces, params.all_workspaces
        )
        resource_type = params.resource_type
        next_token = params.next_token
        limit = params.limit
        page = 0

        workspace_owner_workspaces = []
        workspace_member_project_map = {}
        find_filter: dict = {"$and": [{"domain_id": domain_id}]}

        if next_token:
            decoded_next_token = self._decode_next_token(resource_type, next_token)
            limit = decoded_next_token.get("limit")
            find_filter = decoded_next_token.get("find_filter")
            page = decoded_next_token.get("page")
        else:
            if owner_type == "USER":
                if role_type != "DOMAIN_ADMIN":
                    if params.all_workspaces:
                        workspaces = self._get_all_workspace_ids(domain_id, user_id)

                    if workspaces:
                        (
                            workspace_owner_workspaces,
                            workspace_member_workspaces,
                        ) = self.resource_manager.get_workspace_owner_and_member_workspaces(
                            domain_id, user_id, workspaces
                        )
                        for workspace_id in workspace_member_workspaces:
                            user_projects = self._get_all_projects(
                                domain_id, workspace_id, user_id
                            )
                            workspace_member_project_map[workspace_id] = user_projects

            if workspace_owner_workspaces or workspace_member_project_map:
                find_filter = self._make_filter_by_workspaces(
                    find_filter,
                    workspace_owner_workspaces,
                    workspace_member_project_map,
                )
            elif workspaces:
                find_filter["$and"].append({"workspace_id": {"$in": workspaces}})
            elif params.workspace_id:
                find_filter["$and"].append({"workspace_id": params.workspace_id})
                if params.user_projects and resource_type != "identity.Workspace":
                    find_filter["$and"].append(
                        {"project_id": {"$in": params.user_projects}}
                    )

            regex_pattern = self._get_regex_pattern(params.keyword)

            find_filter = self._make_find_filter_by_resource_type(
                find_filter, resource_type, regex_pattern
            )

        results = self.resource_manager.search_resource(
            domain_id, find_filter, resource_type, limit, page
        )

        next_token = self._encode_next_token_base64(
            results, resource_type, find_filter, limit, page
        )

        response_conf = self.search_conf.get(resource_type).get("response")
        response = self._make_response(results, next_token, response_conf)

        return ResourcesResponse(**response)

    def check_resource_type(self, resource_type: str):
        if resource_type not in self.search_conf:
            raise ERROR_INVALID_PARAMETER(
                key=f"resource_type",
                reason=f"Supported resource types: {list(self.search_conf.keys())}",
            )

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
        if all_workspaces or not workspaces:
            workspaces = []
        elif user_id is None:
            identity_mgr: IdentityManager = self.locator.get_manager("IdentityManager")
            identity_mgr.list_workspace(
                {"filter": [{"k": "workspace_id", "v": workspaces, "o": "in"}]}
            )
        else:
            # check is accessible workspace with params.workspaces
            workspace_ids = self._get_all_workspace_ids(domain_id, user_id)
            workspaces = list(set(workspaces) & set(workspace_ids))

        return workspaces

    def _make_find_filter_by_resource_type(
        self,
        find_filter: dict,
        resource_type: str,
        regex_pattern: Optional[re.Pattern],
    ) -> dict:
        if search_target := self.search_conf.get(resource_type):
            or_filter = {"$or": []}
            for keyword in search_target["request"]["search"]:
                or_filter["$or"].append({keyword: {"$regex": regex_pattern}})

            if request_filters := search_target["request"].get("filter"):
                for request_filter in request_filters:
                    find_filter["$and"].append(request_filter)

            find_filter["$and"].append(or_filter)

        return find_filter

    @staticmethod
    def _get_regex_pattern(keyword: str) -> re.Pattern:
        if keyword:
            regex_pattern = re.compile(f".*{keyword}.*", re.IGNORECASE)
        else:
            regex_pattern = re.compile(".*")

        return regex_pattern

    @staticmethod
    def _make_filter_by_workspaces(
        find_filter: dict,
        workspace_owner_workspaces: list,
        workspace_member_project_map: dict,
    ):
        or_filter = {"$or": []}
        if workspace_owner_workspaces:
            find_filter["$and"].append(
                {"$or": {"workspace_id": {"$in": workspace_owner_workspaces}}}
            )

        for workspace_id, user_projects in workspace_member_project_map.items():
            or_filter["$or"].append(
                {
                    "workspace_id": workspace_id,
                    "project_id": {"$in": user_projects},
                }
            )
            find_filter["$and"].append(or_filter)
        return find_filter

    @staticmethod
    def _make_response(results: list, next_token: str, response_conf: dict) -> dict:
        response_name_format = response_conf["name"]
        response_description_format = response_conf.get("description")
        for result in results:
            result["name"] = response_name_format.format(**result)
            result["resource_id"] = result[response_conf["resource_id"]]
            if response_description_format:
                result["description"] = response_description_format.format(**result)

        return {
            "results": results,
            "next_token": next_token,
        }

    @staticmethod
    def _encode_next_token_base64(
        results: list,
        resource_type: str,
        find_filter: dict,
        limit: int,
        page: int,
    ) -> Union[str, None]:
        if limit == 0 or len(results) != limit:
            return None

        next_token = {
            "resource_type": resource_type,
            "find_filter": find_filter,
            "limit": limit,
            "page": page + 1,
        }

        next_token = base64.b64encode(str(next_token).encode()).decode("utf-8")
        return next_token

    @staticmethod
    def _decode_next_token(resource_type: str, next_token: str) -> dict:
        next_token = eval(base64.b64decode(next_token).decode("utf-8"))
        if next_token.get("resource_type") != resource_type:
            raise ERROR_INVALID_PARAMETER(
                key="resource_type",
                reason="Resource type is different from next_token.",
            )
        return next_token

    @staticmethod
    def _get_search_conf() -> dict:
        package = config.get_package()
        search_conf_module = __import__(
            f"{package}.conf.search_conf", fromlist=["search_conf"]
        )
        return getattr(search_conf_module, "RESOURCE_TYPES", [])
