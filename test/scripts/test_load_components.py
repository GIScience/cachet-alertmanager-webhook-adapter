from responses import RequestsMock, Response, matchers

from cachet_adapter.models.scripts import ComponentData
from cachet_adapter.scripts.load_components import load_components


def a_component_creation_responses(responses: RequestsMock) -> tuple[Response, Response]:
    cachet_response = {'data': []}
    responses.get('http://test-cachet/api/component-groups', json=cachet_response)

    cachet_request = {'name': 'general', 'visible': True}
    cachet_response = {'data': {'id': '1', 'attributes': {'name': 'general'}}}
    group_create_request = responses.post(
        'http://test-cachet/api/component-groups',
        match=[matchers.json_params_matcher(cachet_request)],
        json=cachet_response,
    )

    cachet_response = {
        'data': [],
    }
    responses.get(
        'http://test-cachet/api/components',
        match=[matchers.query_param_matcher({'filter[name]': 'a', 'include': 'group'})],
        json=cachet_response,
    )

    cachet_request = {
        'name': 'a',
        'status': 1,
        'link': '-',
        'description': '-',
        'component_group_id': 1,
    }
    cachet_response = {'data': {'id': '1', 'name': 'a'}}
    component_create_request = responses.post(
        'http://test-cachet/api/components',
        match=[matchers.json_params_matcher(cachet_request)],
        json=cachet_response,
    )

    return group_create_request, component_create_request


def test_load_components(mocked_api, responses):
    a_component_creation_responses(responses=responses)

    data = ComponentData({'general': [{'name': 'a'}]})
    result_ids = load_components(api=mocked_api, data=data)
    assert result_ids == {1: [1]}


def test_dont_load_components_that_exist(mocked_api, responses):
    group_create_request, component_create_request = a_component_creation_responses(responses=responses)

    cachet_response = {
        'data': [
            {'id': '1', 'attributes': {'name': 'general'}, 'relationships': {'components': {'data': [{'id': '1'}]}}}
        ]
    }
    responses.get('http://test-cachet/api/component-groups', json=cachet_response)

    cachet_response = {
        'data': [
            {'id': '1', 'attributes': {'name': 'a'}, 'relationships': {'group': {'data': {'id': '1'}}}},
        ],
        'included': [
            {'id': '1', 'attributes': {'name': 'general'}},
        ],
    }
    responses.get(
        'http://test-cachet/api/components',
        match=[matchers.query_param_matcher({'filter[name]': 'a', 'include': 'group'})],
        json=cachet_response,
    )

    data = ComponentData({'general': [{'name': 'a'}]})
    load_components(api=mocked_api, data=data)
    load_components(api=mocked_api, data=data)

    assert group_create_request.call_count == 1
    assert component_create_request.call_count == 1
