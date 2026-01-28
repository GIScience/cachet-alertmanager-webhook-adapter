from typing import Optional

from fastapi import HTTPException
from sqlmodel import Session, select

from cachet_adapter.models.api import ComponentGraphResponse
from cachet_adapter.models.database import ComponentGraph, ComponentRelationship, IncidentResolver


def upsert_mapping(db_session: Session, mapping: ComponentGraph) -> list[ComponentGraph | ComponentGraphResponse]:
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

    linked_components = subset_graph(group=mapping.from_group, component=mapping.from_component, db_session=db_session)
    return linked_components


def delete_mapping(
    db_session: Session,
    from_group: str,
    from_component: str,
    to_group: str,
    to_component: str,
) -> list[ComponentGraph | ComponentGraphResponse]:
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
) -> list[ComponentGraph | ComponentGraphResponse]:
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
                    rectursive_component_from_group = recursive_component.from_group
                    recursive_component_from_component = recursive_component.from_component
                    recutrsive_component_to_group = group
                    recursive_component_to_component = component
                else:
                    rectursive_component_from_group = group
                    recursive_component_from_component = component
                    recutrsive_component_to_group = recursive_component.to_group
                    recursive_component_to_component = recursive_component.to_component

                if linked_component.relationship == ComponentRelationship.REQUIRES:
                    recursive_component_relationship = recursive_component.relationship
                else:
                    recursive_component_relationship = ComponentRelationship.OPTIONAL

                result.append(
                    ComponentGraphResponse(
                        from_group=rectursive_component_from_group,
                        from_component=recursive_component_from_component,
                        to_group=recutrsive_component_to_group,
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


def save_incident_id(db_session: Session, fingerprint: str, incident_id: int) -> None:
    db_session.add(
        IncidentResolver(
            alertmanager_fingerprint=fingerprint,
            cachet_id=incident_id,
        )
    )
    db_session.commit()


def get_incident_id(db_session: Session, fingerprint: str) -> Optional[int]:
    cachet_id_stmt = select(IncidentResolver.cachet_id).where(IncidentResolver.alertmanager_fingerprint == fingerprint)
    incident_id = db_session.scalar(cachet_id_stmt)
    return incident_id
