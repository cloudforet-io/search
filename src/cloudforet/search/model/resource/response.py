from typing import Union, List
from pydantic import BaseModel


class ResourceResponse(BaseModel):
    resource_id: Union[str, None] = None
    name: Union[str, None] = None
    domain_id: str
    workspace_id: Union[str, None] = None
    project_id: Union[str, None] = None


class ResourcesResponse(BaseModel):
    results: List[ResourceResponse] = None
    next_token: Union[str, None] = None
