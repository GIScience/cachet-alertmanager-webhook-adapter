from datetime import datetime

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
    components: dict[str, list[str]]


class ScheduleResponse(BaseModel):
    schedule_ids: list[int]


class ComponentGraphResponse(ComponentGraph):
    transitive: bool = False


type FlatComponentGraph = ComponentGraph | ComponentGraphResponse

type NestedComponentGraph = dict[str, dict[str, list[FlatComponentGraph]]]
