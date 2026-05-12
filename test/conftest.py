import pytest
from pydantic import HttpUrl
from sqlalchemy import Engine, StaticPool
from sqlmodel import Session, SQLModel, create_engine
from starlette.testclient import TestClient

from cachet_adapter.api import app
from cachet_adapter.models.database import ComponentGraph, ComponentRelationship
from cachet_adapter.utils.cachetapi import CachetApi


@pytest.fixture
def database() -> Engine:
    sqlite_url = 'sqlite://'  # in memory
    engine = create_engine(
        sqlite_url,
        echo=True,
        connect_args={'check_same_thread': False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    return engine


@pytest.fixture
def mocked_api() -> CachetApi:
    return CachetApi(base_url=HttpUrl('http://test-cachet/api'), token='my-token')


@pytest.fixture
def mocked_client(database, mocked_api) -> TestClient:
    app.state.cachet_api = mocked_api

    app.state.db_engine = database

    client = TestClient(app)

    return client


@pytest.fixture
def load_component_chain(database) -> None:
    a_to_b = ComponentGraph(
        from_component='a',
        to_component='b',
        relationship=ComponentRelationship.REQUIRES,
    )
    b_to_c = ComponentGraph(
        from_component='b',
        to_component='c',
        relationship=ComponentRelationship.OPTIONAL,
    )
    chain = [a_to_b, b_to_c]

    with Session(database) as session:
        session.add_all(chain)
        session.commit()


@pytest.fixture
def load_component_triangle(database, load_component_chain) -> None:
    a_to_c = ComponentGraph(
        from_component='a',
        to_component='c',
        relationship=ComponentRelationship.REQUIRES,
    )

    with Session(database) as session:
        session.add(a_to_c)
        session.commit()
