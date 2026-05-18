from datetime import datetime
from enum import StrEnum
from typing import Optional

from pydantic import BaseModel


class AlertmanagerStatus(StrEnum):
    FIRING = 'firing'
    RESOLVED = 'resolved'


class AlertmanagerSeverity(StrEnum):
    CRITICAL = 'critical'
    ERROR = 'error'
    WARNING = 'warning'
    INFO = 'info'


class AlertmanagerLabel(BaseModel):
    job: str
    cachet_group: Optional[str] = None
    cachet_component: Optional[str] = None
    severity: AlertmanagerSeverity | str = AlertmanagerSeverity.CRITICAL
    org: Optional[str] = None


class AlertmanagerAnnotation(BaseModel):
    description: str
    title: str


class Alert(BaseModel):
    status: AlertmanagerStatus
    labels: AlertmanagerLabel
    annotations: AlertmanagerAnnotation
    startsAt: datetime  # noqa: N815
    fingerprint: str


class AlertmanagerWebhook(BaseModel):
    # https://prometheus.io/docs/alerting/latest/configuration/#webhook_config
    alerts: list[Alert]
