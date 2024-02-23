from typing import Union, Optional, List
from pydantic import BaseModel, Field


class ResourceSearchRequest(BaseModel):
    resource_type: str
    keyword: Union[str, None] = None
    limit: Union[int, None] = Field(default=15, ge=0, le=100)
    workspaces: List[str] = Field(default=[], max_items=5)
    all_workspaces: Union[bool, None] = Field(default=False)
    next_token: Union[str, None] = None
    domain_id: str
    workspace_id: Union[str, None] = None
    user_projects: Union[list, None] = None
