import logging

from spaceone.core import cache
from spaceone.core import config
from spaceone.core.auth.jwt.jwt_util import JWTUtil
from spaceone.core.error import *
from spaceone.core.service import *
from spaceone.core.service.utils import *
from spaceone.core.utils import *

from cloudforet.search.lib.utils import *
from cloudforet.search.manager.resource_manager import ResourceManager
from cloudforet.search.manager.identity_manager import IdentityManager
from cloudforet.search.model.resource.response import *
from cloudforet.search.model.resource.request import *

_LOGGER = logging.getLogger("spaceone")

DISABLED_PROJECT_RESOURCE_TYPES = ["identity.Workspace", "inventory.CloudServiceType"]


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

        self.check_resource_type(params.resource_type)

        # permissions = self.transaction.meta.get("authorization.permissions", [])
        user_id = self.transaction.meta.get("authorization.user_id")
        role_type = self.transaction.meta.get("authorization.role_type")

        domain_id = params.domain_id
        all_workspaces = params.all_workspaces
        workspaces = [] if params.all_workspaces else params.workspaces
        resource_type = params.resource_type
        next_token = params.next_token
        limit = params.limit
        page = 0

        workspace_owner_workspaces = []
        workspace_project_map = {}
        find_filter: dict = {"$and": [{"domain_id": domain_id}]}

        if next_token:
            decoded_next_token = self._decode_next_token(resource_type, next_token)
            limit = decoded_next_token.get("limit")
            find_filter = decoded_next_token.get("find_filter")
            page = decoded_next_token.get("page")
        else:
            user_role_type = self._get_user_role_type(domain_id, user_id)

            if role_type == "DOMAIN_ADMIN" or user_role_type == "DOMAIN_ADMIN":
                if workspaces:
                    workspaces = self._get_accessible_workspaces(
                        domain_id, role_type, workspaces, user_id
                    )
                else:
                    params.workspace_id = None
                    not_enabled_workspaces = self._get_not_enabled_workspaces(domain_id)
                    find_filter["$and"].append(
                        {"workspace_id": {"$nin": not_enabled_workspaces}}
                    )
            else:
                if all_workspaces or workspaces:
                    workspaces = self._get_accessible_workspaces(
                        domain_id, role_type, workspaces, user_id
                    )

                if workspaces:
                    if resource_type not in DISABLED_PROJECT_RESOURCE_TYPES:
                        role_bindings_info = self.resource_manager.get_role_bindings(
                            domain_id, user_id, workspaces
                        )
                        workspace_owner_workspaces = (
                            self.resource_manager.get_workspace_owner_workspaces(
                                role_bindings_info
                            )
                        )

                        workspace_member_workspaces = (
                            self.resource_manager.get_workspace_member_workspaces(
                                role_bindings_info
                            )
                        )

                        workspace_project_map = self._get_workspace_project_map(
                            domain_id, workspace_member_workspaces, user_id
                        )

            if workspace_owner_workspaces or workspace_project_map:
                find_filter = self._make_filter_by_workspaces(
                    find_filter,
                    workspace_owner_workspaces,
                )

                find_filter = self._make_filter_by_workspace_project_map(
                    find_filter,
                    workspace_project_map,
                )
            elif workspaces:
                find_filter["$and"].append({"workspace_id": {"$in": workspaces}})
            elif params.workspace_id:
                find_filter["$and"].append({"workspace_id": params.workspace_id})
                if (
                    params.user_projects
                    and resource_type not in DISABLED_PROJECT_RESOURCE_TYPES
                ):
                    find_filter["$and"].append(
                        {"project_id": {"$in": params.user_projects}}
                    )

            regex_pattern = self._get_regex_pattern(params.keyword)

            find_filter = self._make_find_filter_by_resource_type(
                find_filter, resource_type, regex_pattern
            )

        # search resources
        projection = self.search_conf[resource_type]["request"].get("projection", {})
        results = self.resource_manager.search_resource(
            domain_id, find_filter, projection, resource_type, limit, page
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

    def _get_all_workspaces(
        self,
        domain_id: str,
        role_type: str,
        user_id: str = None,
    ) -> list:
        identity_mgr: IdentityManager = self.locator.get_manager("IdentityManager")

        if role_type == "DOMAIN_ADMIN":
            results = identity_mgr.list_workspace(query={}).get("results", [])
        elif user_id:
            # In case of USER who has WORKSPACE_OWNER or WORKSPACE_MEMBER role
            results = identity_mgr.get_workspaces(domain_id, user_id).get("results", [])
        else:
            # In case of WORKSPACE_OWNER App
            results = []

        workspaces = [result["workspace_id"] for result in results]
        return workspaces

    def _get_all_projects(
        self, domain_id: str, workspace_id: str, user_id: str = None
    ) -> list:
        user_projects = []

        public_projects_info = self.resource_manager.list_public_projects(
            domain_id, workspace_id
        )
        user_projects.extend(
            [project_info["project_id"] for project_info in public_projects_info]
        )

        private_projects_info = self.resource_manager.list_private_projects(
            domain_id,
            workspace_id,
            user_id,
        )

        user_projects.extend(
            [project_info["project_id"] for project_info in private_projects_info]
        )

        return user_projects

    def _get_workspace_project_map(
        self,
        domain_id: str,
        workspaces: list,
        user_id: str,
    ) -> dict:
        workspace_project_map = {}
        for workspace_id in workspaces:
            workspace_projects = self._get_all_projects(
                domain_id, workspace_id, user_id
            )
            workspace_project_map[workspace_id] = workspace_projects
        return workspace_project_map

    def _get_accessible_workspaces(
        self,
        domain_id: str,
        role_type: str,
        workspaces: list = None,
        user_id: str = None,
    ) -> list:
        # check is accessible workspace with params.workspaces
        workspace_ids = self._get_all_workspaces(domain_id, role_type, user_id)
        if workspaces:
            workspaces = list(set(workspaces) & set(workspace_ids))
        else:
            workspaces = workspace_ids

        return workspaces

    def _get_not_enabled_workspaces(self, domain_id: str) -> list:
        # get disabled and deleted workspaces
        find_filter = {
            "$and": [{"domain_id": domain_id}, {"state": {"$ne": "ENABLED"}}]
        }
        workspaces_info = self.resource_manager.list_workspaces(find_filter)
        not_enabled_workspaces = [
            workspace_info["workspace_id"] for workspace_info in workspaces_info
        ]
        return not_enabled_workspaces

    def _make_find_filter_by_resource_type(
        self, find_filter: dict, resource_type: str, regex_pattern: str
    ) -> dict:
        if search_target := self.search_conf.get(resource_type):
            or_filter = {"$or": []}
            for keyword in search_target["request"]["search"]:
                or_filter["$or"].append(
                    {keyword: {"$regex": regex_pattern, "$options": "i"}}
                )

            if request_filters := search_target["request"].get("filter"):
                for request_filter in request_filters:
                    find_filter["$and"].append(request_filter)

            find_filter["$and"].append(or_filter)

        return find_filter

    def _make_response(
        self, results: list, next_token: str, response_conf: dict
    ) -> dict:
        name_format = response_conf["name"]
        description_format = response_conf.get("description")
        tags: dict = response_conf.get("tags")
        for result in results:
            # Make description at response
            if description_format:
                result["description"] = description_format.format(**result)
            if tags:
                result = self._add_additional_info_to_tags(result, tags)
            else:
                result["tags"] = {}

            result["name"] = name_format.format(**result)
            result["resource_id"] = result[response_conf["resource_id"]]

        return {
            "results": results,
            "next_token": next_token,
        }

    def _encode_next_token_base64(
        self,
        results: list,
        resource_type: str,
        find_filter: dict,
        limit: int,
        page: int,
    ) -> Union[str, None]:
        if limit == 0 or len(results) != limit:
            return None

        next_token_payload = {
            "resource_type": resource_type,
            "find_filter": find_filter,
            "limit": limit,
            "page": page + 1,
        }
        secret_key = self.transaction.meta.get("token")
        next_token = JWTUtil.encode(next_token_payload, secret_key, algorithm="HS256")
        return next_token

    def _decode_next_token(self, resource_type: str, next_token: str) -> dict:
        secret_key = self.transaction.meta.get("token")

        try:
            next_token = JWTUtil.decode(
                token=next_token, public_jwk=secret_key, algorithm="HS256"
            )
            if next_token.get("resource_type") != resource_type:
                raise ERROR_INVALID_PARAMETER(
                    key="resource_type",
                    reason="Resource type is different from next_token.",
                )
        except Exception:
            raise ERROR_PERMISSION_DENIED(reason="Invalid next_token.")

        return next_token

    @cache.cacheable(key="search:user-role-type:{domain_id}:{user_id}", expire=10)
    def _get_user_role_type(
        self, domain_id: str, user_id: str = None
    ) -> Union[str, None]:
        user_role_type = None

        if user_id:
            role_bindings_info = self.resource_manager.get_role_bindings(
                domain_id, user_id, role_type="DOMAIN_ADMIN"
            )

            if role_bindings_info:
                user_role_type = role_bindings_info[0].get("role_type", "USER")

        return user_role_type

    @staticmethod
    def _make_filter_by_workspaces(
        find_filter: dict,
        workspaces: list,
    ):
        if workspaces:
            find_filter["$and"].append({"$or": [{"workspace_id": {"$in": workspaces}}]})

        _LOGGER.debug(f"[_make_filter_by_workspaces] find_filter: {find_filter}")
        return find_filter

    @staticmethod
    def _make_filter_by_workspace_project_map(
        find_filter: dict, workspace_project_map: dict
    ):
        or_filter = {"$or": []}
        for workspace_id, user_projects in workspace_project_map.items():
            or_filter["$or"].append(
                {
                    "workspace_id": workspace_id,
                    "project_id": {"$in": user_projects},
                }
            )
            find_filter["$and"].append(or_filter)
        _LOGGER.debug(
            f"[_make_filer_by_workspace_project_map] find_filter: {find_filter}"
        )
        return find_filter

    @staticmethod
    def _get_regex_pattern(keyword: str) -> str:
        regex_pattern = ".*"
        if keyword:
            regex_pattern = f".*{keyword}.*"

        return regex_pattern

    @staticmethod
    def _get_search_conf() -> dict:
        package = config.get_package()
        search_conf_module = __import__(
            f"{package}.conf.search_conf", fromlist=["search_conf"]
        )
        return getattr(search_conf_module, "RESOURCE_TYPES", [])

    @staticmethod
    def _convert_result_by_alias(result: dict, aliases: list) -> dict:
        for alias in aliases:
            for target_field, alias_name in alias.items():
                if value := get_dict_value(result, target_field):
                    if not result.get(alias_name):
                        result[alias_name] = value.format(**result)
                        # result = save_to_dict_value(result, alias_name, value)
        return result

    @staticmethod
    def _add_additional_info_to_tags(result: dict, tags: dict) -> dict:
        response_tags = {}
        for key, value in tags.items():
            if target_value := get_dict_value(result, value):
                response_tags[key] = target_value
        result["tags"] = response_tags
        return result
