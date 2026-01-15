from enum import StrEnum

from sqlmodel import Field, SQLModel

DEFAULT_GROUP = 'general'


class ComponentRelationship(StrEnum):
    REQUIRES = 'requires'
    OPTIONAL = 'optional'


class ComponentGraph(SQLModel, table=True):
    from_group: str = Field(default=DEFAULT_GROUP, primary_key=True, index=True)
    from_component: str = Field(primary_key=True, index=True)
    to_group: str = Field(default=DEFAULT_GROUP, primary_key=True, index=True)
    to_component: str = Field(primary_key=True, index=True)
    relationship: ComponentRelationship


class IncidentResolver(SQLModel, table=True):
    alertmanager_fingerprint: str = Field(primary_key=True, index=True, unique=True)
    cachet_id: int = Field(primary_key=True, index=True, unique=True)
