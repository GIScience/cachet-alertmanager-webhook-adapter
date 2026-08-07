import json
import logging
from typing import Optional

from cachet_adapter.models.cachet import (
    BaseComponent,
    CachetComponentCreateResponse,
    CachetComponentQueryResponse,
    CachetGroup,
    CachetGroupAttributes,
    CachetGroupCreateResponse,
    CachetGroupQueryResponse,
    CachetIncidentResponse,
    CachetRelationshipComponent,
    CachetSchedule,
    CachetScheduleResponse,
    Incident,
    IncidentStatus,
)
from cachet_adapter.models.database import NONE_GROUP_STR
from cachet_adapter.utils.http_connection import HttpConnection

log = logging.getLogger(__name__)


class CachetApi(HttpConnection):
    def list_groups(self) -> list[CachetGroup]:
        response = self.session.get(f'{self.base_url}/component-groups')
        response.raise_for_status()
        response_json = response.json()
        cachet_response = CachetGroupQueryResponse.model_validate(response_json)
        return cachet_response.data

    def create_group(self, group: CachetGroupAttributes) -> int:
        group_data = group.model_dump(mode='json')
        log.debug(f'Creating group {json.dumps(group_data, indent=4)}')
        response = self.session.post(f'{self.base_url}/component-groups', json=group_data)
        response.raise_for_status()
        response_json = response.json()
        response_group = CachetGroupCreateResponse.model_validate(response_json)
        group_id = response_group.data.id
        return group_id

    def delete_group(self, group_id: int) -> None:
        self.session.delete(f'{self.base_url}/component-groups/{group_id}')

    def list_components(self, component_name: Optional[str] = None) -> CachetComponentQueryResponse:
        querystring = {'include': 'group'}
        if component_name:
            querystring = querystring | {'filter[name]': component_name}
        response = self.session.get(f'{self.base_url}/components', params=querystring)
        response.raise_for_status()
        response_json = response.json()
        cachet_response = CachetComponentQueryResponse.model_validate(response_json)
        return cachet_response

    def get_component_id(self, component_group: str, component_name: str) -> Optional[int]:
        cachet_response = self.list_components(component_name=component_name)

        group_lookup = dict()
        for cachet_group in cachet_response.included:
            group_lookup[cachet_group.id] = cachet_group.attributes.name

        for component in cachet_response.data:
            if component.relationships.group.data:
                cachet_group_name = group_lookup.get(component.relationships.group.data.id)
            else:
                cachet_group_name = NONE_GROUP_STR

            if component_group == cachet_group_name and component_name == component.attributes.name:
                log.debug(f'Component ID is {component.id}')
                return component.id

        log.debug(f'Component {component_group}.{component_name} unknown.')
        return None

    def create_component(self, component: BaseComponent, group_id: int) -> int:
        component_data = component.model_dump(mode='json', exclude_none=True)
        component_data = component_data | {'component_group_id': group_id}
        log.debug(f'Creating component {json.dumps(component_data, indent=4)}')
        response = self.session.post(f'{self.base_url}/components', json=component_data)
        response.raise_for_status()
        response_json = response.json()
        response_component = CachetComponentCreateResponse.model_validate(response_json)
        component_id = response_component.data.id
        return component_id

    def update_component(self, component: BaseComponent, group_id: int, component_id: int) -> None:
        component_data = component.model_dump(mode='json', exclude_none=True)
        component_data = component_data | {'component_group_id': group_id}
        response = self.session.put(f'{self.base_url}/components/{component_id}', json=component_data)
        response.raise_for_status()

    def delete_component(self, component_id: int) -> None:
        self.session.delete(f'{self.base_url}/components/{component_id}')

    def get_incident(self, incident_id: int) -> CachetIncidentResponse:
        response = self.session.get(f'{self.base_url}/incidents/{incident_id}')
        response.raise_for_status()
        response_json = response.json()
        cachet_response = CachetIncidentResponse.model_validate(response_json)
        return cachet_response

    def create_incident(self, incident: Incident) -> int:
        incident_data = incident.model_dump(exclude_none=True, mode='json')
        log.debug(f'Creating incident {json.dumps(incident_data, indent=4)}')
        response = self.session.post(f'{self.base_url}/incidents', json=incident_data)
        response.raise_for_status()
        response_json = response.json()
        cachet_response = CachetIncidentResponse.model_validate(response_json)
        incident_id = cachet_response.data.id
        return incident_id

    def update_incident(self, incident_id: int, new_status: IncidentStatus) -> None:
        response = self.session.put(f'{self.base_url}/incidents/{incident_id}', json={'status': new_status})
        response.raise_for_status()

    def list_schedule_ids(self) -> set[int]:
        response = self.session.get(f'{self.base_url}/schedules')
        response.raise_for_status()
        response_json = response.json()
        cachet_response = CachetRelationshipComponent.model_validate(response_json)
        ids = {schedule.id for schedule in cachet_response.data}
        return ids

    def create_schedule(self, scheduled_incident: CachetSchedule) -> int:
        schedule_data = scheduled_incident.model_dump(mode='json', exclude_none=True)
        log.debug(f'Creating schedule {json.dumps(schedule_data, indent=4)}')
        response = self.session.post(f'{self.base_url}/schedules', json=schedule_data)
        response.raise_for_status()
        response_json = response.json()
        cachet_response = CachetScheduleResponse.model_validate(response_json)
        schedule_id = cachet_response.data.id
        return schedule_id

    def update_schedule(self, schedule_id: int, scheduled_incident: CachetSchedule) -> None:
        response = self.session.put(
            f'{self.base_url}/schedules/{schedule_id}',
            json=scheduled_incident.model_dump(mode='json', exclude={'name', 'message'}, exclude_none=True),
        )
        response.raise_for_status()

    def delete_schedules(self, schedule_ids: list[int]) -> None:
        log.debug(f'Deleting schedules {schedule_ids}')
        for schedule_id in schedule_ids:
            response = self.session.delete(f'{self.base_url}/schedules/{schedule_id}')
            response.raise_for_status()
