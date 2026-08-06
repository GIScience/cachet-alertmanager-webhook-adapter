import logging
from typing import Optional

from fastapi import APIRouter
from sqlmodel import Session
from starlette.requests import Request

from cachet_adapter.models.alertmanager import (
    AlertmanagerApiStatus,
    AlertmanagerSeverity,
    AlertmanagerStatusObject,
    AlertmanagerWebhookContent,
    AlertmanagerWebhookStatus,
    ApiAlert,
    WebhookAlert,
)
from cachet_adapter.models.api import AdaptResponse
from cachet_adapter.models.cachet import (
    ComponentStatus,
    Incident,
    IncidentComponent,
    IncidentStatus,
)
from cachet_adapter.models.database import NONE_GROUP_STR
from cachet_adapter.settings import OverrideMode
from cachet_adapter.utils.cachet_api import CachetApi
from cachet_adapter.utils.storage import (
    delete_incident,
    get_additional_known_incidents,
    get_dependent_components,
    get_incident_id,
    save_incident_id,
)

log = logging.getLogger(__name__)

ADAPT_ROUTE = '/adapt'
router = APIRouter(prefix=ADAPT_ROUTE)


@router.post(
    path='',
    status_code=200,
    summary='Translate Alertmanager alerts to a Cachet incidents',
)
async def adapt(
    alertmanager: AlertmanagerWebhookContent | list[ApiAlert], request: Request, prune: bool = False
) -> AdaptResponse:
    cachet_api = request.app.state.cachet_api

    if isinstance(alertmanager, list):
        alerts = alertmanager
    else:
        alerts = alertmanager.alerts

    incident_ids = []
    with Session(request.app.state.db_engine) as db_session:
        for alert in alerts:
            incident_id = process_alert(
                db_session=db_session,
                cachet_api=cachet_api,
                alert=alert,
                message_override=request.app.state.override_mode,
            )
            if incident_id:
                incident_ids.append(incident_id)

        if prune:
            resolved_incidents = get_additional_known_incidents(db_session=db_session, incident_ids=incident_ids)
            for incident_id in resolved_incidents:
                cachet_api.update_incident(incident_id=incident_id, new_status=IncidentStatus.FIXED)
                delete_incident(db_session=db_session, incident_id=incident_id)
                incident_ids.append(incident_id)

    return AdaptResponse(incident_ids=incident_ids)


def process_alert(
    db_session: Session,
    cachet_api: CachetApi,
    alert: WebhookAlert | ApiAlert,
    message_override: OverrideMode,
    secondary_component_incident_visible: bool = True,
) -> Optional[int]:
    log.debug(f'Adapting {alert.model_dump_json(indent=4)}')

    incident_id = get_incident_id(db_session=db_session, starts_at=alert.startsAt, fingerprint=alert.fingerprint)
    incident_status = extract_incident_status(status=alert.status)

    if incident_id:
        handle_known_incident(
            db_session=db_session, cachet_api=cachet_api, incident_id=incident_id, incident_status=incident_status
        )
    else:
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

        if len(linked_components) > 0 or alert.labels.cachet_incident_force:
            incident_id = create_new_incident(
                db_session=db_session,
                cachet_api=cachet_api,
                alert=alert,
                alert_component_name=alert_component_name,
                incident_status=incident_status,
                linked_components=linked_components,
                top_level_component_incident=top_level_component_incident,
                secondary_component_incident_visible=secondary_component_incident_visible,
                message_override=message_override,
            )
        else:
            log.debug('Not creating incident because there are no linked components and no force-flag')

    return incident_id


def create_new_incident(
    db_session: Session,
    cachet_api: CachetApi,
    alert: WebhookAlert | ApiAlert,
    alert_component_name: str,
    incident_status: IncidentStatus,
    linked_components: set[IncidentComponent],
    top_level_component_incident: bool,
    secondary_component_incident_visible: bool,
    message_override: OverrideMode,
) -> int:
    incident_name, incident_description = extract_name_and_description(
        alert=alert,
        alert_component_name=alert_component_name,
        top_level_component_incident=top_level_component_incident,
        message_override=message_override,
    )

    visible = top_level_component_incident or secondary_component_incident_visible
    incident = Incident(
        name=incident_name,
        status=incident_status,
        message=incident_description,
        occurred_at=alert.startsAt,
        visible=visible,
        components=list(linked_components),
    )

    incident_id = cachet_api.create_incident(incident=incident)
    save_incident_id(
        db_session=db_session, starts_at=alert.startsAt, fingerprint=alert.fingerprint, incident_id=incident_id
    )
    return incident_id


def extract_name_and_description(
    alert: WebhookAlert | ApiAlert,
    alert_component_name: str,
    message_override: OverrideMode,
    top_level_component_incident: bool,
) -> tuple[str, str]:
    if top_level_component_incident:
        incident_name = f'Component {alert_component_name} experiences issues'
    else:
        incident_name = 'A required downstream component experiences issues'
    incident_description = 'Experiencing issues'

    match message_override:
        case OverrideMode.ALL:
            pass
        case OverrideMode.SUPPLIER:
            if top_level_component_incident:
                incident_name = alert.annotations.title or f'Component {alert_component_name} experiences issues'
                incident_description = (
                    alert.annotations.summary or alert.annotations.description or incident_description
                )
        case OverrideMode.NONE:
            incident_name = alert.annotations.title or f'Component {alert_component_name} experiences issues'
            incident_description = alert.annotations.summary or alert.annotations.description or incident_description
        case _:
            raise NotImplementedError(f'Mode {message_override} not implemented.')
    return incident_name, incident_description


def handle_known_incident(
    db_session: Session, cachet_api: CachetApi, incident_id: int, incident_status: IncidentStatus
):
    existing_incident = cachet_api.get_incident(incident_id=incident_id)
    existing_status = existing_incident.data.attributes.status.value
    if existing_status < incident_status:
        cachet_api.update_incident(incident_id=incident_id, new_status=incident_status)
    elif existing_status == IncidentStatus.FIXED and incident_status != IncidentStatus.FIXED:
        log.warning(f'The incident {incident_id} was marked as fixed in cachet but is still firing!')

    if incident_status == IncidentStatus.FIXED:
        delete_incident(db_session=db_session, incident_id=incident_id)


def extract_incident_status(status: AlertmanagerWebhookStatus | AlertmanagerStatusObject) -> IncidentStatus:
    state = status
    if isinstance(status, AlertmanagerStatusObject):
        state = status.state

    match state:
        case AlertmanagerWebhookStatus.FIRING | AlertmanagerApiStatus.ACTIVE:
            incident_status = IncidentStatus.REPORTED
        case AlertmanagerApiStatus.SUPPRESSED:
            incident_status = IncidentStatus.INVESTIGATING
        case AlertmanagerWebhookStatus.RESOLVED:
            incident_status = IncidentStatus.FIXED
        case _:
            raise NotImplementedError(f'Status {state} unknown.')

    return incident_status


def extract_alert_component_status(severity: AlertmanagerSeverity | str) -> ComponentStatus:
    match severity:
        case AlertmanagerSeverity.CRITICAL | AlertmanagerSeverity.ERROR:
            component_status = ComponentStatus.MAJOR_OUTAGE
        case _:
            component_status = ComponentStatus.PARTIAL_OUTAGE
    return component_status
