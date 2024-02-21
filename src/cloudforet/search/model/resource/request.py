from typing import Union
from pydantic import BaseModel, Field


class ResourceSearchRequest(BaseModel):
    resource_type: str
    keyword: Union[str, None] = None
    limit: Union[int, None] = Field(default=10, ge=1, le=100)
    all_workspaces: Union[bool, None] = None
    next_token: Union[str, None] = None
    domain_id: str
    workspace_id: Union[str, None] = None
    user_projects: Union[list, None] = None
