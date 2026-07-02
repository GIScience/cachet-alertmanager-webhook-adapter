from datetime import datetime
from typing import Optional, Sequence

from fastapi import HTTPException
from sqlalchemy import delete
from sqlmodel import Session, and_, not_, select

from cachet_adapter.models.api import ComponentGraphResponse, FlatComponentGraph, NestedComponentGraph
from cachet_adapter.models.cachet import ComponentStatus, IncidentComponent
from cachet_adapter.models.database import ComponentGraph, ComponentRelationship, IncidentResolver, ScheduleResolver
from cachet_adapter.utils.cachet_api import CachetApi


def upsert_mapping(db_session: Session, mappings: list[ComponentGraph]) -> NestedComponentGraph:
    result = dict()
    for mapping in mappings:
        chain_down = subset_graph(
            group=mapping.to_group,
            component=mapping.to_component,
            db_session=db_session,
            recursive=True,
        )
        for link in chain_down:
            if link.to_component == mapping.from_component:
                raise HTTPException(
                    status_code=400,
                    detail=f'The requested mapping would introduce a circular dependency from {link.to_component} to {mapping.from_component}',
                )

        db_session.merge(mapping)
        db_session.commit()

        linked_components = subset_graph(
            group=mapping.from_group, component=mapping.from_component, db_session=db_session
        )
        group_graph = result.get(mapping.from_group, dict())
        group_graph[mapping.from_component] = linked_components
        result[mapping.from_group] = group_graph
    return result


def delete_mapping(
    db_session: Session,
    from_group: str,
    from_component: str,
    to_group: str,
    to_component: str,
) -> list[FlatComponentGraph]:
    select_desired_mapping = select(ComponentGraph).where(
        ComponentGraph.from_group == from_group,
        ComponentGraph.from_component == from_component,
        ComponentGraph.to_group == to_group,
        ComponentGraph.to_component == to_component,
    )
    mapping = db_session.scalar(select_desired_mapping)
    if mapping:
        db_session.delete(mapping)
        db_session.commit()

    linked_components = subset_graph(group=from_group, component=from_component, db_session=db_session)
    return linked_components


def subset_graph(
    group: Optional[str],
    component: Optional[str],
    db_session: Session,
    recursive: bool = False,
    upward: bool = False,
) -> list[FlatComponentGraph]:
    result = []
    stmt = select(ComponentGraph)
    if upward:
        if group:
            stmt = stmt.where(ComponentGraph.to_group == group)
        if component:
            stmt = stmt.where(ComponentGraph.to_component == component)
    else:
        if group:
            stmt = stmt.where(ComponentGraph.from_group == group)
        if component:
            stmt = stmt.where(ComponentGraph.from_component == component)

    linked_components = db_session.exec(stmt).fetchall()
    result.extend(linked_components)

    if group is not None and component and recursive:
        for linked_component in linked_components:
            if upward:
                query_group = linked_component.from_group
                query_component = linked_component.from_component
            else:
                query_group = linked_component.to_group
                query_component = linked_component.to_component

            recursive_components = subset_graph(
                group=query_group,
                component=query_component,
                recursive=recursive,
                upward=upward,
                db_session=db_session,
            )
            for recursive_component in recursive_components:
                if upward:
                    recursive_component_from_group = recursive_component.from_group
                    recursive_component_from_component = recursive_component.from_component
                    recursive_component_to_group = group
                    recursive_component_to_component = component
                else:
                    recursive_component_from_group = group
                    recursive_component_from_component = component
                    recursive_component_to_group = recursive_component.to_group
                    recursive_component_to_component = recursive_component.to_component

                if linked_component.relationship == ComponentRelationship.REQUIRES:
                    recursive_component_relationship = recursive_component.relationship
                else:
                    recursive_component_relationship = ComponentRelationship.OPTIONAL

                result.append(
                    ComponentGraphResponse(
                        from_group=recursive_component_from_group,
                        from_component=recursive_component_from_component,
                        to_group=recursive_component_to_group,
                        to_component=recursive_component_to_component,
                        relationship=recursive_component_relationship,
                        transitive=True,
                    )
                )
    elif recursive:
        raise ValueError('Recursive listing is only available for exact component definitions (group + component).')

    return result


def unique_dependent_components(
    db_session: Session, group: str, component: str
) -> dict[str, dict[str, ComponentRelationship]]:
    dependent_components = subset_graph(
        group=group,
        component=component,
        db_session=db_session,
        recursive=True,
        upward=True,
    )
    dependent_component_dict = dict()
    for dependent_component in dependent_components:
        dependent_components_in_group = dependent_component_dict.get(dependent_component.from_group, {})
        dependent_component_relationship = dependent_components_in_group.get(dependent_component.from_component)
        if not dependent_component_relationship or dependent_component_relationship != ComponentRelationship.REQUIRES:
            dependent_components_in_group[dependent_component.from_component] = dependent_component.relationship
            dependent_component_dict[dependent_component.from_group] = dependent_components_in_group
    return dependent_component_dict


def save_incident_id(db_session: Session, starts_at: datetime, fingerprint: str, incident_id: int) -> None:
    db_session.add(
        IncidentResolver(
            starts_at=starts_at,
            alertmanager_fingerprint=fingerprint,
            cachet_id=incident_id,
        )
    )
    db_session.commit()


def save_schedule_id(db_session: Session, schedule_id: int, event_uid: str):
    db_session.add(
        ScheduleResolver(
            ics_uid=event_uid,
            cachet_id=schedule_id,
        )
    )
    db_session.commit()


def get_incident_id(db_session: Session, starts_at: datetime, fingerprint: str) -> Optional[int]:
    cachet_id_stmt = select(IncidentResolver.cachet_id).where(
        and_(IncidentResolver.starts_at == starts_at, IncidentResolver.alertmanager_fingerprint == fingerprint)
    )
    incident_id = db_session.scalar(cachet_id_stmt)
    return incident_id


def get_schedule_id(db_session: Session, schedule_id: str) -> Optional[int]:
    cachet_id_stmt = select(ScheduleResolver.cachet_id).where(ScheduleResolver.ics_uid == schedule_id)
    schedule_id = db_session.scalar(cachet_id_stmt)
    return schedule_id


def delete_incident(db_session: Session, incident_id: int) -> None:
    stmt = delete(IncidentResolver).where(IncidentResolver.cachet_id == incident_id)
    db_session.exec(stmt)
    db_session.commit()


def delete_schedule_ids(db_session: Session, schedule_ids: Sequence[int]) -> None:
    stmt = delete(ScheduleResolver).where(ScheduleResolver.cachet_id.in_(schedule_ids))
    db_session.exec(stmt)
    db_session.commit()


def get_additional_known_incidents(db_session: Session, incident_ids: Sequence[int]) -> set[int]:
    cachet_id_stmt = select(IncidentResolver.cachet_id).where(not_(IncidentResolver.cachet_id.in_(incident_ids)))
    incident_ids = db_session.scalars(cachet_id_stmt)
    return incident_ids


def get_dependent_components(
    group: str, name: str, status: ComponentStatus, cachet_api: CachetApi, db_session: Session
) -> tuple[set[IncidentComponent], bool]:
    alert_component_id = cachet_api.get_component_id(component_group=group, component_name=name)

    direct_incident = alert_component_id is not None

    linked_components = set()
    if direct_incident:
        linked_components.add(IncidentComponent(id=alert_component_id, status=status))

    dependent_components = unique_dependent_components(group=group, component=name, db_session=db_session)

    for dependent_component_group, dependent_components_in_group in dependent_components.items():
        for dependent_component_name, dependent_component_relationship in dependent_components_in_group.items():
            dependent_component_id = cachet_api.get_component_id(
                component_group=dependent_component_group, component_name=dependent_component_name
            )
            if dependent_component_id:
                dependent_component_status = extract_dependent_component_status(
                    alert_component_status=status,
                    dependent_component_relationship=dependent_component_relationship,
                )
                component = IncidentComponent(id=dependent_component_id, status=dependent_component_status)
                linked_components.add(component)
    return linked_components, direct_incident


def extract_dependent_component_status(
    alert_component_status: ComponentStatus, dependent_component_relationship: ComponentRelationship
) -> ComponentStatus:
    if (
        alert_component_status == ComponentStatus.MAJOR_OUTAGE
        and dependent_component_relationship == ComponentRelationship.REQUIRES
    ):
        return ComponentStatus.MAJOR_OUTAGE
    return ComponentStatus.PARTIAL_OUTAGE
