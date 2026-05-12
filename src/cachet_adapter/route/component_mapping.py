from typing import Optional, Sequence

from fastapi import APIRouter, HTTPException
from sqlalchemy import delete
from sqlmodel import Session
from starlette.requests import Request

from cachet_adapter.models.api import ComponentGraphResponse, FlatComponentGraph, NestedComponentGraph
from cachet_adapter.models.database import (
    NONE_GROUP_STR,
    ComponentGraph,
)
from cachet_adapter.utils.storage import delete_mapping, subset_graph, upsert_mapping

router = APIRouter(prefix='/component-mapping')


@router.get(path='', status_code=200, summary='Get the component mapping graph')
def get_component_mapping(
    request: Request,
    group: Optional[str] = None,
    component: Optional[str] = None,
    recursive: bool = False,
    upward: bool = False,
) -> Sequence[ComponentGraphResponse | ComponentGraph]:
    if component:
        group = group or NONE_GROUP_STR

    with Session(request.app.state.db_engine) as db_session:
        try:
            linked_components = subset_graph(
                group=group,
                component=component,
                recursive=recursive,
                db_session=db_session,
                upward=upward,
            )
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
    return linked_components


@router.put(path='', status_code=201, summary='Alter the component mapping graph')
def alter_component_mapping(
    mapping: ComponentGraph,
    request: Request,
) -> list[FlatComponentGraph]:
    with Session(request.app.state.db_engine) as db_session:
        linked_components = upsert_mapping(db_session=db_session, mappings=[mapping])
    return linked_components.popitem()[1].popitem()[1]


@router.post(path='', status_code=200, summary='Alter the component mapping graph with multiple dependencies')
def alter_component_mappings(
    mappings: list[ComponentGraph],
    request: Request,
    prune: bool = False,
) -> NestedComponentGraph:
    with Session(request.app.state.db_engine) as db_session:
        if prune:
            stmt = delete(ComponentGraph)
            db_session.exec(stmt)
            db_session.commit()

        linked_components = upsert_mapping(db_session=db_session, mappings=mappings)

    return linked_components


@router.delete(path='', status_code=200, summary='Delete part of the component mapping graph')
def delete_component_mapping(
    from_group: str,
    from_component: str,
    to_group: str,
    to_component: str,
    request: Request,
) -> Sequence[ComponentGraph]:
    with Session(request.app.state.db_engine) as db_session:
        linked_components = delete_mapping(
            db_session=db_session,
            from_group=from_group,
            from_component=from_component,
            to_group=to_group,
            to_component=to_component,
        )
    return linked_components
