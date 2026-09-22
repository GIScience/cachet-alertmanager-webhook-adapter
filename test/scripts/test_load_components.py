import json
from typing import Optional

from responses import RequestsMock, Response, matchers

from cachet_adapter.models.scripts import ComponentData
from cachet_adapter.scripts.load_components import load_components
from test.conftest import TEST_RESOURCES

CACHET_URL = 'http://test-cachet/api'


def as_group_response(group_id: str, name: str) -> dict:
    return {'id': group_id, 'attributes': {'name': name}}


def as_component_response(component_id: str, name: str, group_id: str) -> dict:
    return {'id': component_id, 'attributes': {'name': name}, 'relationships': {'group': {'data': {'id': group_id}}}}


def as_component_payload(name: str, group_id: int) -> dict:
    return {'name': name, 'status': 1, 'component_group_id': group_id}


def add_group_listing_response(responses: RequestsMock, *groups: list[dict]) -> None:
    responses.get(f'{CACHET_URL}/component-groups', json={'data': list(groups)})


def add_component_listing_response(
    responses: RequestsMock,
    *components: dict,
    query_params: Optional[dict] = None,
    links: Optional[dict] = None,
) -> None:
    cachet_response = {'data': list(components)}
    if links:
        cachet_response['links'] = links
    responses.get(
        f'{CACHET_URL}/components',
        match=[matchers.query_param_matcher(query_params or {'include': 'group'})],
        json=cachet_response,
    )


def create_group(responses: RequestsMock, group_id: str, name: str) -> Response:
    return responses.post(
        f'{CACHET_URL}/component-groups',
        match=[matchers.json_params_matcher({'name': name, 'visible': True, 'collapsed': 2})],
        json={'data': as_group_response(group_id, name)},
    )


def create_component(responses: RequestsMock, component_id: str, name: str, group_id: int) -> Response:
    return responses.post(
        f'{CACHET_URL}/components',
        match=[matchers.json_params_matcher(as_component_payload(name, group_id))],
        json={'data': {'id': component_id, 'name': name}},
    )


def update_component(responses: RequestsMock, component_id: int, name: str, group_id: int) -> Response:
    return responses.put(
        f'{CACHET_URL}/components/{component_id}',
        match=[matchers.json_params_matcher(as_component_payload(name, group_id))],
    )


def component_a_creation_responses(responses: RequestsMock) -> tuple[Response, Response]:
    add_group_listing_response(responses)
    group_create_request = create_group(responses, group_id='1', name='general')
    add_component_listing_response(responses)
    component_create_request = create_component(responses, component_id='1', name='a', group_id=1)
    return group_create_request, component_create_request


def test_load_components(mocked_api, responses):
    component_a_creation_responses(responses=responses)

    with open(TEST_RESOURCES / 'components.json', 'r') as f:
        raw_data = json.load(f)
    data = ComponentData(raw_data)

    result_ids = load_components(api=mocked_api, data=data)
    assert result_ids == {1: [1]}


def test_update_components_that_exist(mocked_api, responses):
    group_create_request, component_create_request = component_a_creation_responses(responses=responses)

    add_group_listing_response(responses, as_group_response('1', 'general'))
    add_component_listing_response(responses, as_component_response('1', 'a', '1'))

    data = ComponentData({'general': [{'name': 'a'}]})
    load_components(api=mocked_api, data=data)

    update_component(responses, component_id=1, name='a', group_id=1)
    load_components(api=mocked_api, data=data)

    assert group_create_request.call_count == 1
    assert component_create_request.call_count == 1


def test_sync_components(mocked_api, responses):
    component_a_creation_responses(responses=responses)

    add_group_listing_response(responses, as_group_response('1', 'general'))
    create_group(responses, group_id='2', name='special')
    add_component_listing_response(responses, as_component_response('1', 'a', '1'))
    create_component(responses, component_id='2', name='b', group_id=2)
    responses.delete(f'{CACHET_URL}/components/1')
    responses.delete(f'{CACHET_URL}/component-groups/1')

    data = ComponentData({'general': [{'name': 'a'}]})
    load_components(api=mocked_api, data=data)
    data = ComponentData({'special': [{'name': 'b'}]})
    load_components(api=mocked_api, data=data, prune=True)


def test_sync_components_component_change(mocked_api, responses):
    component_a_creation_responses(responses=responses)

    add_group_listing_response(responses, as_group_response('1', 'general'))
    add_component_listing_response(responses, as_component_response('1', 'a', '1'))
    create_component(responses, component_id='2', name='b', group_id=1)
    responses.delete(f'{CACHET_URL}/components/1')

    data = ComponentData({'general': [{'name': 'a'}]})
    load_components(api=mocked_api, data=data)
    data = ComponentData({'general': [{'name': 'b'}]})
    load_components(api=mocked_api, data=data, prune=True)


def test_sync_components_group_change(mocked_api, responses):
    component_a_creation_responses(responses=responses)

    add_group_listing_response(responses, as_group_response('1', 'general'))
    create_group(responses, group_id='2', name='special')
    add_component_listing_response(responses, as_component_response('1', 'a', '1'))
    create_component(responses, component_id='3', name='a', group_id=2)
    responses.delete(f'{CACHET_URL}/components/1')
    responses.delete(f'{CACHET_URL}/component-groups/1')

    data = ComponentData({'general': [{'name': 'a'}]})
    load_components(api=mocked_api, data=data)
    data = ComponentData({'special': [{'name': 'a'}]})
    load_components(api=mocked_api, data=data, prune=True)
