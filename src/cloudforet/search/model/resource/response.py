from typing import Union, List, Dict, Any
from pydantic import BaseModel


class ResourceResponse(BaseModel):
    resource_id: Union[str, None] = None
    name: Union[str, None] = None
    description: Union[str, None] = None
    tags: Union[dict, None] = None
    domain_id: str
    workspace_id: Union[str, None] = None
    project_id: Union[str, None] = None


class ResourcesResponse(BaseModel):
    results: List[ResourceResponse] = None
    next_token: Union[str, None] = None
