from enum import IntEnum
from typing import Annotated, Optional

from pydantic import AfterValidator, BaseModel, Field, HttpUrl, PlainSerializer, StringConstraints

from cachet_adapter.models import UtcDateTime

type CachetStr = Annotated[str, StringConstraints(min_length=1, max_length=255)]
type CachetDateTime = Annotated[
    UtcDateTime,
    PlainSerializer(lambda _datetime: _datetime.strftime('%Y-%m-%d %H:%M:%S'), return_type=str),
]
type CachetId = Annotated[int, Field(ge=1)]


class ComponentStatus(IntEnum):
    OPERATIONAL = 1
    PERFORMANCE_ISSUES = 2
    PARTIAL_OUTAGE = 3
    MAJOR_OUTAGE = 4
    UNKNOWN = 5
    UNDER_MAINTENANCE = 6


COMPONENT_STATUS_SEVERITY = {
    ComponentStatus.OPERATIONAL: 0,
    ComponentStatus.UNKNOWN: 1,
    ComponentStatus.UNDER_MAINTENANCE: 3,
    ComponentStatus.PERFORMANCE_ISSUES: 4,
    ComponentStatus.PARTIAL_OUTAGE: 5,
    ComponentStatus.MAJOR_OUTAGE: 6,
}


class IncidentStatus(IntEnum):
    REPORTED = 0
    INVESTIGATING = 1
    IDENTIFIED = 2
    WATCHING = 3
    FIXED = 4


class CollapseStates(IntEnum):
    ALWAYS_EXPANDED = 0
    ALWAYS_COLLAPSED = 1
    COLLAPSED_UNLESS_INCIDENT = 2


class CachetIdObject(BaseModel):
    id: CachetId


class BaseComponent(BaseModel):
    name: CachetStr  # Required by the Cachet API
    description: Optional[str] = None
    link: Optional[HttpUrl] = None
    status: ComponentStatus = ComponentStatus.OPERATIONAL


class Component(BaseComponent):
    id: CachetId


class IncidentComponent(BaseModel, frozen=True):
    id: CachetId
    status: ComponentStatus

    @staticmethod
    def deduplicate_list(value: Optional[list['IncidentComponent']]) -> Optional[list['IncidentComponent']]:
        if value is None:
            return None

        # by iterating in order and by highest-status-first we can only keep the first occurrence of duplicates
        value.sort(key=lambda incident: (incident.id, COMPONENT_STATUS_SEVERITY[incident.status]), reverse=True)
        seen = set()
        deduped = []
        for component in value:
            if component.id not in seen:
                deduped.append(component)
                seen.add(component.id)
        return deduped


type LinkedComponents = Annotated[Optional[list[IncidentComponent]], AfterValidator(IncidentComponent.deduplicate_list)]


class Incident(BaseModel):
    name: CachetStr  # Required by the Cachet API
    status: IncidentStatus = IncidentStatus.REPORTED  # Required by the Cachet API
    message: CachetStr  # Required by the Cachet API
    visible: bool = False
    occurred_at: Optional[CachetDateTime] = None
    components: LinkedComponents = None


class IncidentUpdate(BaseModel):
    status: IncidentStatus  # Required by the Cachet API
    message: CachetStr  # Required by the Cachet API


class CachetStatusValue(BaseModel):
    value: IncidentStatus


class CachetIncidentAttributes(BaseModel):
    status: CachetStatusValue


class CachetIncidentData(CachetIdObject):
    attributes: CachetIncidentAttributes


class CachetIncidentResponse(BaseModel):
    data: CachetIncidentData


class CachetIncidentUpdateResponse(BaseModel):
    data: CachetIdObject


class CachetScheduleResponse(BaseModel):
    data: CachetIdObject


class CachetRelationshipGroup(BaseModel):
    data: Optional[CachetIdObject] = None


class CachetRelationshipComponent(BaseModel):
    data: list[CachetIdObject]


class CachetComponentRelationships(BaseModel):
    group: CachetRelationshipGroup


class CachetGroupRelationships(BaseModel):
    components: CachetRelationshipComponent


class CachetComponentAttributes(BaseModel):
    name: str


class CachetComponentResponseData(BaseModel):
    id: int
    attributes: CachetComponentAttributes
    relationships: CachetComponentRelationships


class CachetGroupAttributes(BaseModel):
    name: CachetStr  # Required by the Cachet API
    visible: bool = True
    collapsed: int = CollapseStates.COLLAPSED_UNLESS_INCIDENT


class CachetGroup(BaseModel):
    id: int
    attributes: CachetGroupAttributes
    relationships: Optional[CachetGroupRelationships] = None


class CachetComponentQueryResponse(BaseModel):
    data: list[CachetComponentResponseData]
    included: list[CachetGroup] = []


class CachetGroupQueryResponse(BaseModel):
    data: list[CachetGroup]


class CachetComponentCreateResponse(BaseModel):
    data: CachetIdObject


class CachetGroupCreateResponse(BaseModel):
    data: CachetGroup


class CachetSchedule(BaseModel):
    name: CachetStr  # Required by the Cachet API
    message: CachetStr  # Required by the Cachet API
    scheduled_at: CachetDateTime  # Required by the Cachet API
    completed_at: CachetDateTime
    components: LinkedComponents = None
