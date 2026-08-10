import logging
from datetime import UTC, datetime
from typing import Literal, Optional

from fastapi import APIRouter
from sqlmodel import Session, select
from starlette.requests import Request

from cachet_adapter.models.api import ScheduledIncident, ScheduleResponse
from cachet_adapter.models.cachet import CachetSchedule, ComponentStatus, IncidentComponent
from cachet_adapter.models.database import ScheduleResolver
from cachet_adapter.utils.cachet_api import CachetApi
from cachet_adapter.utils.storage import (
    delete_schedule_ids,
    get_dependent_components,
    get_schedule_id,
    save_schedule_id,
)

log = logging.getLogger(__name__)
router = APIRouter(prefix='/schedule')


@router.post(
    path='',
    status_code=200,
    summary='Schedule a set of maintenance notifications',
)
async def schedule(
    scheduled_incidents: list[ScheduledIncident], request: Request, prune: bool = False
) -> ScheduleResponse:
    cachet_api = request.app.state.cachet_api

    schedule_ids = []
    with Session(request.app.state.db_engine) as db_session:
        for scheduled_incident in scheduled_incidents:
            schedule_id = process_schedule(
                db_session=db_session, cachet_api=cachet_api, scheduled_incident=scheduled_incident
            )
            if schedule_id:
                schedule_ids.append(schedule_id)

        clean_schedules(prune=prune, schedule_ids=schedule_ids, cachet_api=cachet_api, db_session=db_session)

    return ScheduleResponse(schedule_ids=schedule_ids)


def process_schedule(
    db_session: Session, cachet_api: CachetApi, scheduled_incident: ScheduledIncident
) -> Optional[int]:
    log.debug(f'Processing {scheduled_incident.model_dump_json(indent=4)}')

    schedule_id = get_schedule_id(db_session=db_session, schedule_id=scheduled_incident.id)

    linked_components = process_linked_components(
        cachet_api=cachet_api, db_session=db_session, components=scheduled_incident.components
    )

    cachet_schedule = CachetSchedule(
        name=scheduled_incident.name,
        message=scheduled_incident.message,
        scheduled_at=scheduled_incident.scheduled_at,
        completed_at=scheduled_incident.completed_at,
        components=linked_components,
    )

    if schedule_id:
        cachet_api.update_schedule(schedule_id=schedule_id, scheduled_incident=cachet_schedule)
    elif scheduled_incident.completed_at > datetime.now(tz=UTC):
        schedule_id = cachet_api.create_schedule(scheduled_incident=cachet_schedule)
        save_schedule_id(db_session=db_session, schedule_id=schedule_id, event_uid=scheduled_incident.id)
    else:
        log.debug(f'Event {scheduled_incident.id} is neither known nor in the future. Skipping.')

    return schedule_id


def clean_schedules(prune: bool, schedule_ids: list[int], cachet_api: CachetApi, db_session: Session):
    schedule_ids_on_server = cachet_api.list_schedule_ids()

    unprocessed_schedule_ids = schedule_ids_on_server.difference(schedule_ids)

    cachet_id_stmt = select(ScheduleResolver.cachet_id).where(ScheduleResolver.cachet_id.in_(unprocessed_schedule_ids))
    known_schedule_ids = list(db_session.scalars(cachet_id_stmt).all())

    if len(known_schedule_ids) > 0:
        if prune:
            cachet_api.delete_schedules(schedule_ids=known_schedule_ids)
            delete_schedule_ids(db_session=db_session, schedule_ids=known_schedule_ids)
        else:
            log.warning(
                f'Schedules with IDs {known_schedule_ids} exist in cachet and the cachet adapter but not among '
                'the provided events.'
            )

    unknown_remaining_schedules = unprocessed_schedule_ids.difference(known_schedule_ids)
    if len(unknown_remaining_schedules) > 0:
        log.warning(
            f'Schedules with IDs {unknown_remaining_schedules} remain on the server but are unknown to the adapter.'
        )


def process_linked_components(
    cachet_api: CachetApi,
    db_session: Session,
    components: Optional[dict[str, list[str]]] | Literal['all'],
    status: ComponentStatus = ComponentStatus.MAJOR_OUTAGE,
) -> Optional[list[IncidentComponent]]:
    linked_components = set()

    if components is None:
        return None
    elif components == 'all':
        all_components = cachet_api.list_components().data
        for component in all_components:
            incident_component = IncidentComponent(id=component.id, status=status)
            linked_components.add(incident_component)
    else:
        for group, components in components.items():
            for component in components:
                sub_linked_components, _ = get_dependent_components(
                    group=group,
                    name=component,
                    status=status,
                    cachet_api=cachet_api,
                    db_session=db_session,
                )
                linked_components.update(sub_linked_components)
    return list(linked_components)
