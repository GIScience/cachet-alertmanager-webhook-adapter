from datetime import datetime
from enum import IntEnum
from typing import Annotated, Literal, Optional

from pydantic import BaseModel, Field, HttpUrl


class ComponentStatus(IntEnum):
    OPERATIONAL = 1
    PERFORMANCE_ISSUES = 2
    PARTIAL_OUTAGE = 3
    MAJOR_OUTAGE = 4


class IncidentStatus(IntEnum):
    REPORTED = 0
    FIXED = 4


class CachetIdObject(BaseModel):
    id: Annotated[int, Field(ge=1)]


class BaseComponent(BaseModel):
    name: str
    description: Optional[str] = '-'
    link: Optional[HttpUrl | Literal['-']] = '-'
    status: ComponentStatus = ComponentStatus.OPERATIONAL


class Component(BaseComponent):
    id: Annotated[int, Field(ge=1)]


class IncidentComponent(BaseModel, frozen=True):
    id: Annotated[int, Field(ge=1)]
    status: ComponentStatus


class Incident(BaseModel):
    name: Annotated[str, Field(max_length=255)]
    status: Optional[IncidentStatus] = None
    message: Optional[str] = None
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
