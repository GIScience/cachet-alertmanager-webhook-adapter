from datetime import UTC, datetime
from enum import IntEnum
from typing import Annotated, Optional

from pydantic import BaseModel, Field, HttpUrl, PlainSerializer, StringConstraints

type CachetStr = Annotated[str, StringConstraints(min_length=1)]
type CachetDateTime = Annotated[
    datetime,
    PlainSerializer(lambda _datetime: _datetime.astimezone(UTC).strftime('%Y-%m-%d %H:%M:%S'), return_type=str),
]
type CachetId = Annotated[int, Field(ge=1)]


class ComponentStatus(IntEnum):
    OPERATIONAL = 1
    PERFORMANCE_ISSUES = 2
    PARTIAL_OUTAGE = 3
    MAJOR_OUTAGE = 4


class IncidentStatus(IntEnum):
    REPORTED = 0
    FIXED = 4


class CollapseStates(IntEnum):
    ALWAYS_EXPANDED = 0
    ALWAYS_COLLAPSED = 1
    COLLAPSED_UNLESS_INCIDENT = 2


class CachetIdObject(BaseModel):
    id: CachetId


class BaseComponent(BaseModel):
    name: str
    description: Optional[str] = None
    link: Optional[HttpUrl] = None
    status: ComponentStatus = ComponentStatus.OPERATIONAL


class Component(BaseComponent):
    id: CachetId


class IncidentComponent(BaseModel, frozen=True):
    id: CachetId
    status: ComponentStatus


class Incident(BaseModel):
    name: Annotated[str, Field(max_length=255)]
    status: Optional[IncidentStatus] = None
    message: CachetStr
    visible: bool = False
    occurred_at: Optional[datetime] = None
    components: Optional[list[IncidentComponent]] = None


class CachetIncidentResponse(BaseModel):
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
    name: str
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
    name: CachetStr
    message: CachetStr
    scheduled_at: CachetDateTime
    completed_at: CachetDateTime
    components: Optional[list[IncidentComponent]]
