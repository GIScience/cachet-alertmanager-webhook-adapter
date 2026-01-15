from datetime import datetime
from enum import IntEnum
from typing import Annotated, Optional

from pydantic import BaseModel, Field


class ComponentStatus(IntEnum):
    OPERATIONAL = 1
    PERFORMANCE_ISSUES = 2
    PARTIAL_OUTAGE = 3
    MAJOR_OUTAGE = 4


class IncidentStatus(IntEnum):
    REPORTED = 0
    FIXED = 4


class Component(BaseModel, frozen=True):
    id: Annotated[int, Field(ge=1)]
    status: ComponentStatus


class Incident(BaseModel):
    name: Annotated[str, Field(max_length=255)]
    status: Optional[IncidentStatus] = None
    message: Optional[str] = None
    visible: bool = False
    occurred_at: Optional[datetime] = None
    components: Optional[list[Component]] = None


class CachetIncidentResponseData(BaseModel):
    id: int


class CachetIncidentResponse(BaseModel):
    data: CachetIncidentResponseData


class CachetRelationshipGroupData(BaseModel):
    id: int


class CachetRelationshipGroup(BaseModel):
    data: Optional[CachetRelationshipGroupData] = None


class CachetRelationships(BaseModel):
    group: CachetRelationshipGroup


class CachetComponentAttributes(BaseModel):
    name: str


class CachetComponentResponseData(BaseModel):
    id: int
    attributes: CachetComponentAttributes
    relationships: CachetRelationships


class CachetGroupAttributes(BaseModel):
    name: str


class CachetGroup(BaseModel):
    id: int
    attributes: CachetGroupAttributes


class CachetComponentResponse(BaseModel):
    data: list[CachetComponentResponseData]
    included: list[CachetGroup] = []
