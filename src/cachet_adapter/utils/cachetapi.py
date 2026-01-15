from typing import Any, Optional

import requests
from pydantic import HttpUrl
from requests.adapters import HTTPAdapter
from urllib3 import Retry

from cachet_adapter.models.cachet import CachetComponentResponse, CachetIncidentResponse


class CachetApi:
    def __init__(
        self,
        base_url: HttpUrl,
        token: str,
        max_retries: int = 5,
    ):
        self.base_url = base_url
        self.session = requests.Session()

        self.configure_session(max_retries=max_retries, token=token)

    def configure_session(self, max_retries: int, token: str):
        self.session.headers.update(
            {
                'Authorization': f'Bearer {token}',
                'Content-Type': 'application/json',
                'Accept': 'application/json',
            }
        )

        retries = Retry(total=max_retries, backoff_factor=0.1, status_forcelist=[500, 502, 503, 504])
        # We have to mount http:// to overwrite the default adapters
        # noinspection HttpUrlsUsage
        self.session.mount('http://', HTTPAdapter(max_retries=retries))
        self.session.mount('https://', HTTPAdapter(max_retries=retries))

    def get_potential_components(self, component_name: str) -> CachetComponentResponse:
        querystring = {'filter[name]': component_name, 'include': 'group'}
        response = self.session.get(f'{self.base_url}/components', params=querystring)
        response.raise_for_status()
        response_json = response.json()
        cachet_response = CachetComponentResponse.model_validate(response_json)
        return cachet_response

    def get_component_id(self, component_group: str, component_name: str) -> Optional[int]:
        cachet_response = self.get_potential_components(component_name=component_name)

        group_lookup = dict()
        for cachet_group in cachet_response.included:
            group_lookup[cachet_group.id] = cachet_group.attributes.name

        for component in cachet_response.data:
            if component.relationships.group.data:
                cachet_group_name = group_lookup.get(component.relationships.group.data.id)
                if component_group == cachet_group_name and component_name == component.attributes.name:
                    return component.id
        return None

    def create_incident(self, incident_json: dict[str, Any]) -> int:
        response = self.session.post(f'{self.base_url}/incidents', json=incident_json)
        response.raise_for_status()
        response_json = response.json()
        cachet_response = CachetIncidentResponse.model_validate(response_json)
        incident_id = cachet_response.data.id
        return incident_id

    def update_incident(self, incident_id: int, incident_json: dict[str, Any]) -> None:
        response = self.session.put(f'{self.base_url}/incidents/{incident_id}', json=incident_json)
        response.raise_for_status()
