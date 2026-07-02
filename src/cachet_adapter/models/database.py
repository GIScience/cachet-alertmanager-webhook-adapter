from datetime import datetime
from enum import StrEnum

from sqlmodel import Field, SQLModel

# the current implementation does not allow ungrouped components (i.e. None-group) because primary keys in SQL
# databases need to be Non-NULL
# the current work-around is to use an empty string placeholder until the implementation is made more robust
NONE_GROUP_STR = ''


class ComponentRelationship(StrEnum):
    REQUIRES = 'requires'
    OPTIONAL = 'optional'


class ComponentGraph(SQLModel, table=True):
    from_group: str = Field(default=NONE_GROUP_STR, primary_key=True, index=True)
    from_component: str = Field(primary_key=True, index=True)
    to_group: str = Field(default=NONE_GROUP_STR, primary_key=True, index=True)
    to_component: str = Field(primary_key=True, index=True)
    relationship: ComponentRelationship


class IncidentResolver(SQLModel, table=True):
    starts_at: datetime = Field(primary_key=True, index=True)
    alertmanager_fingerprint: str = Field(primary_key=True)
    cachet_id: int = Field(unique=True)


class ScheduleResolver(SQLModel, table=True):
    ics_uid: str = Field(primary_key=True, index=True, unique=True)
    cachet_id: int = Field(primary_key=True, index=True, unique=True)
