import logging
from typing import Optional

from fastapi import APIRouter
from sqlmodel import Session
from starlette.requests import Request

from cachet_adapter.models.alertmanager import (
    Alert,
    AlertmanagerSeverity,
    AlertmanagerStatus,
    AlertmanagerWebhook,
)
from cachet_adapter.models.api import AdaptResponse
from cachet_adapter.models.cachet import (
    ComponentStatus,
    Incident,
    IncidentStatus,
)
from cachet_adapter.models.database import NONE_GROUP_STR
from cachet_adapter.utils.cachetapi import CachetApi
from cachet_adapter.utils.storage import get_dependent_components, get_incident_id, save_incident_id

log = logging.getLogger(__name__)

ADAPT_ROUTE = '/adapt'
router = APIRouter(prefix=ADAPT_ROUTE)


@router.post(
    path='',
    status_code=200,
    summary='Translate an Alertmanager alert to a Cachet incident',
)
async def adapt(alertmanager: AlertmanagerWebhook, request: Request) -> AdaptResponse:
    cachet_api = request.app.state.cachet_api

    incident_ids = []
    with Session(request.app.state.db_engine) as db_session:
        for alert in alertmanager.alerts:
            incident_id = process_alert(db_session=db_session, cachet_api=cachet_api, alert=alert)
            if incident_id:
                incident_ids.append(incident_id)

    return AdaptResponse(incident_ids=incident_ids)


def process_alert(db_session: Session, cachet_api: CachetApi, alert: Alert) -> Optional[int]:
    log.debug(f'Adapting {alert.model_dump_json(indent=4)}')
    alert_component_group = alert.labels.cachet_group or alert.labels.org or NONE_GROUP_STR
    alert_component_name = alert.labels.cachet_component or alert.labels.job
    alert_component_status = extract_alert_component_status(severity=alert.labels.severity)

    linked_components, top_level_component_incident = get_dependent_components(
        group=alert_component_group,
        name=alert_component_name,
        status=alert_component_status,
        cachet_api=cachet_api,
        db_session=db_session,
    )

    incident_status = IncidentStatus.REPORTED if alert.status == AlertmanagerStatus.FIRING else IncidentStatus.FIXED

    incident_description = 'Experiencing issues'
    if top_level_component_incident:
        incident_name = alert.annotations.title or f'Component {alert_component_name} experiences issues'
        incident_description = alert.annotations.summary or alert.annotations.description or incident_description
    else:
        incident_name = 'A required downstream component experiences issues'

    if len(linked_components) > 0 or alert.labels.cachet_incident_force:
        incident = Incident(
            name=incident_name,
            status=incident_status,
            message=incident_description,
            occurred_at=alert.startsAt,
            visible=top_level_component_incident,
            components=list(linked_components),
        )
        incident_json = incident.model_dump(exclude_none=True, mode='json')

        incident_id = get_incident_id(db_session=db_session, fingerprint=alert.fingerprint)

        if incident_id:
            cachet_api.update_incident(incident_id=incident_id, incident_json=incident_json)
        else:
            incident_id = cachet_api.create_incident(incident_json=incident_json)
            save_incident_id(db_session=db_session, fingerprint=alert.fingerprint, incident_id=incident_id)

        return incident_id
    else:
        log.debug('Not creating incident because there are no linked components and no force-flag')
        return None


def extract_alert_component_status(severity: AlertmanagerSeverity | str) -> ComponentStatus:
    match severity:
        case AlertmanagerSeverity.CRITICAL:
            component_status = ComponentStatus.MAJOR_OUTAGE
        case AlertmanagerSeverity.ERROR:
            component_status = ComponentStatus.MAJOR_OUTAGE
        case _:
            component_status = ComponentStatus.PARTIAL_OUTAGE
    return component_status
