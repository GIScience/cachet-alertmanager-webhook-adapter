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
    IncidentComponent,
    IncidentStatus,
)
from cachet_adapter.models.database import (
    NONE_GROUP_STR,
    ComponentRelationship,
)
from cachet_adapter.utils.cachetapi import CachetApi
from cachet_adapter.utils.storage import get_incident_id, save_incident_id, unique_dependent_components

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
            incident_ids.append(incident_id)

    return AdaptResponse(incident_ids=incident_ids)


def process_alert(db_session: Session, cachet_api: CachetApi, alert: Alert) -> int:
    alert_component_group = alert.labels.cachet_group or alert.labels.org or NONE_GROUP_STR
    alert_component_status = extract_alert_component_status(severity=alert.labels.severity)
    alert_component_name = alert.labels.cachet_component or alert.labels.job
    alert_component_id = cachet_api.get_component_id(
        component_group=alert_component_group, component_name=alert_component_name
    )

    incident_visible = alert_component_id is not None
    incident_status = IncidentStatus.REPORTED if alert.status == AlertmanagerStatus.FIRING else IncidentStatus.FIXED

    linked_components = set()

    incident_description = 'Experiencing issues'
    if alert_component_id:
        incident_name = alert.annotations.title or f'Component {alert_component_name} experiences issues'
        incident_description = alert.annotations.summary or alert.annotations.description or incident_description

        linked_components.add(IncidentComponent(id=alert_component_id, status=alert_component_status))
    else:
        incident_name = 'A required downstream component experiences issues'

    dependent_components = unique_dependent_components(
        group=alert_component_group, component=alert_component_name, db_session=db_session
    )

    for dependent_component_group, dependent_components_in_group in dependent_components.items():
        for dependent_component_name, dependent_component_relationship in dependent_components_in_group.items():
            dependent_component_id = cachet_api.get_component_id(
                component_group=dependent_component_group, component_name=dependent_component_name
            )
            if dependent_component_id:
                dependent_component_status = extract_dependent_component_status(
                    alert_component_status=alert_component_status,
                    dependent_component_relationship=dependent_component_relationship,
                )
                component = IncidentComponent(id=dependent_component_id, status=dependent_component_status)
                linked_components.add(component)

    # TODO: should we create an incident if the linked-components are not there?

    incident = Incident(
        name=incident_name,
        status=incident_status,
        message=incident_description,
        occurred_at=alert.startsAt,
        visible=incident_visible,
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


def extract_alert_component_status(severity: AlertmanagerSeverity | str) -> ComponentStatus:
    match severity:
        case AlertmanagerSeverity.CRITICAL:
            component_status = ComponentStatus.MAJOR_OUTAGE
        case AlertmanagerSeverity.ERROR:
            component_status = ComponentStatus.MAJOR_OUTAGE
        case _:
            component_status = ComponentStatus.PARTIAL_OUTAGE
    return component_status


def extract_dependent_component_status(
    alert_component_status: ComponentStatus, dependent_component_relationship: ComponentRelationship
) -> ComponentStatus:
    if (
        alert_component_status == ComponentStatus.MAJOR_OUTAGE
        and dependent_component_relationship == ComponentRelationship.REQUIRES
    ):
        return ComponentStatus.MAJOR_OUTAGE
    return ComponentStatus.PARTIAL_OUTAGE
