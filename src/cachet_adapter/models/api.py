from pydantic import BaseModel

from cachet_adapter.models.database import ComponentGraph


class AdaptResponse(BaseModel):
    incident_ids: list[int]


class ComponentGraphResponse(ComponentGraph):
    transitive: bool = False
