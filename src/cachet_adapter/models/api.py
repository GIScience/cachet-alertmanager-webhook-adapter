from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel

from cachet_adapter.models.database import ComponentGraph


class AdaptResponse(BaseModel):
    incident_ids: list[int]


class ScheduledIncident(BaseModel):
    id: str
    name: str
    message: str = 'A scheduled downtime'
    scheduled_at: datetime
    completed_at: datetime
    components: Optional[dict[str, list[str]]] | Literal['all']


class ScheduleResponse(BaseModel):
    schedule_ids: list[int]


class ComponentGraphResponse(ComponentGraph):
    transitive: bool = False


type FlatComponentGraph = ComponentGraph | ComponentGraphResponse

type NestedComponentGraph = dict[str, dict[str, list[FlatComponentGraph]]]
