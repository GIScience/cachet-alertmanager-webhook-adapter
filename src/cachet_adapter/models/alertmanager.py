from enum import StrEnum
from typing import Optional

from pydantic import BaseModel

from cachet_adapter.models import UtcDateTime


class AlertmanagerWebhookStatus(StrEnum):
    FIRING = 'firing'
    RESOLVED = 'resolved'


class AlertmanagerApiStatus(StrEnum):
    ACTIVE = 'active'
    SUPPRESSED = 'suppressed'


class AlertmanagerSeverity(StrEnum):
    CRITICAL = 'critical'
    ERROR = 'error'
    WARNING = 'warning'
    INFO = 'info'


class AlertmanagerStatusObject(BaseModel):
    state: AlertmanagerApiStatus


class AlertmanagerLabel(BaseModel):
    job: str
    cachet_group: Optional[str] = None
    cachet_component: Optional[str] = None
    cachet_incident_force: bool = False
    severity: AlertmanagerSeverity | str = AlertmanagerSeverity.CRITICAL
    org: Optional[str] = None


class AlertmanagerAnnotation(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    summary: Optional[str] = None


class WebhookAlert(BaseModel):
    status: AlertmanagerWebhookStatus
    labels: AlertmanagerLabel
    annotations: AlertmanagerAnnotation = AlertmanagerAnnotation()
    startsAt: UtcDateTime  # noqa: N815
    fingerprint: str


class ApiAlert(WebhookAlert):
    status: AlertmanagerStatusObject


class AlertmanagerWebhookContent(BaseModel):
    # https://prometheus.io/docs/alerting/latest/configuration/#webhook_config
    alerts: list[WebhookAlert]
