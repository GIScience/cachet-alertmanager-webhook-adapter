from datetime import UTC, datetime
from enum import StrEnum
from typing import Optional

from sqlalchemy import DateTime, Dialect, TypeDecorator
from sqlmodel import Field, SQLModel

from cachet_adapter.models import UtcDateTime

# the current implementation does not allow ungrouped components (i.e. None-group) because primary keys in SQL
# databases need to be Non-NULL
# the current work-around is to use an empty string placeholder until the implementation is made more robust
NONE_GROUP_STR = ''


class DbUtcDateTime(TypeDecorator):
    """We store naive datetimes because some DBs behave a bit complicated when serverd with aware datetimes"""

    impl = DateTime

    cache_ok = True

    def process_bind_param(self, value: Optional[UtcDateTime], dialect: Dialect) -> Optional[datetime]:
        if value is None:
            return value

        naive_datetime = value.replace(tzinfo=None)
        return naive_datetime

    def process_result_value(self, value: Optional[datetime], dialect: Dialect) -> Optional[UtcDateTime]:
        if value is None:
            return value

        aware_datetime: UtcDateTime = value.replace(tzinfo=UTC)
        return aware_datetime


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
    starts_at: UtcDateTime = Field(primary_key=True, index=True, sa_type=DbUtcDateTime)
    alertmanager_fingerprint: str = Field(primary_key=True)
    cachet_id: int = Field(unique=True)


class ScheduleResolver(SQLModel, table=True):
    ics_uid: str = Field(primary_key=True, index=True, unique=True)
    cachet_id: int = Field(primary_key=True, index=True, unique=True)
