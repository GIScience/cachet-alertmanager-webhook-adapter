import pytest
import requests
import responses as responses_lib
from responses import matchers
from sqlmodel import Session
from starlette.testclient import TestClient

from cachet_adapter.api import app
from cachet_adapter.models.database import ComponentGraph, ComponentRelationship
from cachet_adapter.settings import OverrideMode


def create_default_incident(responses, mocked_client) -> tuple[requests.Response, responses_lib.Response]:
    responses.get(
        'http://test-cachet/api/components',
        match=[matchers.query_param_matcher({'filter[name]': 'a', 'include': 'group'})],
        json={
            'data': [{'id': '1', 'attributes': {'name': 'a'}, 'relationships': {'group': {'data': None}}}],
        },
    )

    cachet_request = {
        'name': 'Component a down',
        'status': 0,
        'message': 'Component a is down.',
        'visible': True,
        'occurred_at': '2025-11-20T15:54:41.898000Z',
        'components': [{'id': 1, 'status': 4}],
    }
    cachet_header = {
        'Authorization': 'Bearer my-token',
        'Content-Type': 'application/json',
        'Accept': 'application/json',
    }
    cachet_response = {'data': {'id': '30', 'attributes': {'status': {'value': 0}}}}
    post = responses.post(
        'http://test-cachet/api/incidents',
        match=[
            matchers.json_params_matcher(cachet_request, strict_match=False),
            matchers.header_matcher(cachet_header),
        ],
        json=cachet_response,
    )

    alertmanager_request = {
        'alerts': [
            {
                'status': 'firing',
                'labels': {'job': 'a'},
                'annotations': {
                    'description': 'Component a is down.',
                    'title': 'Component a down',
                },
                'startsAt': '2025-11-20T15:54:41.898000Z',
                'fingerprint': 'fingerprint',
            }
        ]
    }
    response = mocked_client.post('/adapt', json=alertmanager_request)

    return response, post


def test_adapt_creates_incident(mocked_client, responses):
    response, _ = create_default_incident(responses=responses, mocked_client=mocked_client)

    assert response.status_code == 200
    assert response.json() == {'incident_ids': [30]}


def test_adapt_request_without_annotations(mocked_client, responses):
    responses.get(
        'http://test-cachet/api/components',
        match=[matchers.query_param_matcher({'filter[name]': 'a', 'include': 'group'})],
        json={
            'data': [{'id': '1', 'attributes': {'name': 'a'}, 'relationships': {'group': {'data': None}}}],
        },
    )

    cachet_request = {
        'name': 'Component a experiences issues',
        'status': 0,
        'message': 'Experiencing issues',
        'visible': True,
        'occurred_at': '2025-11-20T15:54:41.898000Z',
        'components': [{'id': 1, 'status': 4}],
    }
    cachet_header = {
        'Authorization': 'Bearer my-token',
        'Content-Type': 'application/json',
        'Accept': 'application/json',
    }
    cachet_response = {'data': {'id': '30', 'attributes': {'status': {'value': 0}}}}
    responses.post(
        'http://test-cachet/api/incidents',
        match=[
            matchers.json_params_matcher(cachet_request, strict_match=False),
            matchers.header_matcher(cachet_header),
        ],
        json=cachet_response,
    )

    alertmanager_request = {
        'alerts': [
            {
                'status': 'firing',
                'labels': {'job': 'a'},
                'annotations': {},
                'startsAt': '2025-11-20T15:54:41.898000Z',
                'fingerprint': 'fingerprint',
            }
        ]
    }

    response = mocked_client.post('/adapt', json=alertmanager_request)

    assert response.status_code == 200
    assert response.json() == {'incident_ids': [30]}


def test_adapt_creates_incident_matching_component_name(mocked_client, responses):
    responses.get(
        'http://test-cachet/api/components',
        match=[matchers.query_param_matcher({'filter[name]': 'a', 'include': 'group'})],
        json={
            'data': [
                {'id': '5', 'attributes': {'name': 'aa'}, 'relationships': {'group': {'data': None}}},
                {'id': '1', 'attributes': {'name': 'a'}, 'relationships': {'group': {'data': None}}},
            ],
        },
    )

    cachet_request = {
        'name': 'Component a down',
        'status': 0,
        'message': 'Component a is down.',
        'visible': True,
        'occurred_at': '2025-11-20T15:54:41.898000Z',
        'components': [{'id': 1, 'status': 4}],
    }
    cachet_response = {'data': {'id': '30', 'attributes': {'status': {'value': 0}}}}
    responses.post(
        'http://test-cachet/api/incidents',
        match=[matchers.json_params_matcher(cachet_request, strict_match=False)],
        json=cachet_response,
    )

    alertmanager_request = {
        'alerts': [
            {
                'status': 'firing',
                'labels': {'job': 'a'},
                'annotations': {
                    'description': 'Component a is down.',
                    'title': 'Component a down',
                },
                'startsAt': '2025-11-20T15:54:41.898000Z',
                'fingerprint': 'fingerprint',
            }
        ]
    }

    response = mocked_client.post('/adapt', json=alertmanager_request)

    assert response.status_code == 200
    assert response.json() == {'incident_ids': [30]}


def test_adapt_creates_incident_matching_group(mocked_client, responses):
    responses.get(
        'http://test-cachet/api/components',
        match=[matchers.query_param_matcher({'filter[name]': 'a', 'include': 'group'})],
        json={
            'data': [
                {'id': '1', 'attributes': {'name': 'a'}, 'relationships': {'group': {'data': {'id': '1'}}}},
                {'id': '2', 'attributes': {'name': 'a'}, 'relationships': {'group': {'data': {'id': '2'}}}},
            ],
            'included': [
                {'id': '1', 'attributes': {'name': 'general'}},
                {'id': '2', 'attributes': {'name': 'special'}},
            ],
        },
    )

    cachet_request = {
        'name': 'Component a down',
        'status': 0,
        'message': 'Component a is down.',
        'visible': True,
        'occurred_at': '2025-11-20T15:54:41.898000Z',
        'components': [{'id': 2, 'status': 4}],
    }
    cachet_response = {'data': {'id': '30', 'attributes': {'status': {'value': 0}}}}
    responses.post(
        'http://test-cachet/api/incidents',
        match=[matchers.json_params_matcher(cachet_request, strict_match=False)],
        json=cachet_response,
    )

    alertmanager_request = {
        'alerts': [
            {
                'status': 'firing',
                'labels': {'job': 'a', 'cachet_group': 'special'},
                'annotations': {
                    'description': 'Component a is down.',
                    'title': 'Component a down',
                },
                'startsAt': '2025-11-20T15:54:41.898000Z',
                'fingerprint': 'fingerprint',
            }
        ]
    }

    response = mocked_client.post('/adapt', json=alertmanager_request)

    assert response.status_code == 200
    assert response.json() == {'incident_ids': [30]}


def test_adapt_creates_incident_matching_org(mocked_client, responses):
    responses.get(
        'http://test-cachet/api/components',
        match=[matchers.query_param_matcher({'filter[name]': 'a', 'include': 'group'})],
        json={
            'data': [
                {'id': '1', 'attributes': {'name': 'a'}, 'relationships': {'group': {'data': {'id': '1'}}}},
                {'id': '2', 'attributes': {'name': 'a'}, 'relationships': {'group': {'data': {'id': '2'}}}},
            ],
            'included': [
                {'id': '1', 'attributes': {'name': 'general'}},
                {'id': '2', 'attributes': {'name': 'special'}},
            ],
        },
    )

    cachet_request = {
        'name': 'Component a down',
        'status': 0,
        'message': 'Component a is down.',
        'visible': True,
        'occurred_at': '2025-11-20T15:54:41.898000Z',
        'components': [{'id': 2, 'status': 4}],
    }
    cachet_response = {'data': {'id': '30', 'attributes': {'status': {'value': 0}}}}
    responses.post(
        'http://test-cachet/api/incidents',
        match=[matchers.json_params_matcher(cachet_request, strict_match=False)],
        json=cachet_response,
    )

    alertmanager_request = {
        'alerts': [
            {
                'status': 'firing',
                'labels': {'job': 'a', 'org': 'special'},
                'annotations': {
                    'description': 'Component a is down.',
                    'title': 'Component a down',
                },
                'startsAt': '2025-11-20T15:54:41.898000Z',
                'fingerprint': 'fingerprint',
            }
        ]
    }

    response = mocked_client.post('/adapt', json=alertmanager_request)

    assert response.status_code == 200
    assert response.json() == {'incident_ids': [30]}


def test_adapt_custom_tag_overwrites_job_name(mocked_client, responses):
    responses.get(
        'http://test-cachet/api/components',
        match=[matchers.query_param_matcher({'filter[name]': 'custom component name', 'include': 'group'})],
        json={
            'data': [
                {
                    'id': '2',
                    'attributes': {'name': 'custom component name'},
                    'relationships': {'group': {'data': None}},
                }
            ],
        },
    )

    cachet_request = {
        'name': 'Component b down',
        'status': 0,
        'message': 'Component b is down.',
        'visible': True,
        'occurred_at': '2025-11-20T15:54:41.898000Z',
        'components': [{'id': 2, 'status': 4}],
    }
    cachet_response = {'data': {'id': '30', 'attributes': {'status': {'value': 0}}}}
    responses.post(
        'http://test-cachet/api/incidents',
        match=[matchers.json_params_matcher(cachet_request, strict_match=False)],
        json=cachet_response,
    )

    alertmanager_request = {
        'alerts': [
            {
                'status': 'firing',
                'labels': {
                    'job': 'job name',
                    'cachet_component': 'custom component name',
                },
                'annotations': {
                    'description': 'Component b is down.',
                    'title': 'Component b down',
                },
                'startsAt': '2025-11-20T15:54:41.898000Z',
                'fingerprint': 'fingerprint',
            }
        ]
    }

    response = mocked_client.post('/adapt', json=alertmanager_request)

    assert response.status_code == 200
    assert response.json() == {'incident_ids': [30]}


@pytest.mark.parametrize(
    'mode,dependent_name,dependent_message,supplier_name,supplier_message',
    [
        (
            OverrideMode.NONE,
            'title that might be forwarded',
            'summary that might be forwarded',
            'title that might be forwarded',
            'summary that might be forwarded',
        ),
        (
            OverrideMode.SUPPLIER,
            'title that might be forwarded',
            'summary that might be forwarded',
            'A required downstream component experiences issues',
            'Experiencing issues',
        ),
        (
            OverrideMode.ALL,
            'Component a experiences issues',
            'Experiencing issues',
            'A required downstream component experiences issues',
            'Experiencing issues',
        ),
    ],
)
def test_adapt_override(
    database,
    mocked_api,
    responses,
    load_component_chain,
    mode,
    dependent_name,
    dependent_message,
    supplier_name,
    supplier_message,
):
    app.state.cachet_api = mocked_api
    app.state.db_engine = database
    app.state.override_mode = mode
    client = TestClient(app)

    responses.get(
        'http://test-cachet/api/components',
        match=[matchers.query_param_matcher({'filter[name]': 'a', 'include': 'group'})],
        json={
            'data': [{'id': '1', 'attributes': {'name': 'a'}, 'relationships': {'group': {'data': None}}}],
        },
    )
    responses.get(
        'http://test-cachet/api/components',
        match=[matchers.query_param_matcher({'filter[name]': 'b', 'include': 'group'})],
        json={'data': []},
    )

    cachet_request_dependent = {'name': dependent_name, 'message': dependent_message}
    cachet_response_dependent = {'data': {'id': '30', 'attributes': {'status': {'value': 0}}}}
    responses.post(
        'http://test-cachet/api/incidents',
        match=[matchers.json_params_matcher(cachet_request_dependent, strict_match=False)],
        json=cachet_response_dependent,
    )

    cachet_request_supplier = {'name': supplier_name, 'message': supplier_message}
    cachet_response_supplier = {'data': {'id': '31', 'attributes': {'status': {'value': 0}}}}
    responses.post(
        'http://test-cachet/api/incidents',
        match=[matchers.json_params_matcher(cachet_request_supplier, strict_match=False)],
        json=cachet_response_supplier,
    )

    alertmanager_request = {
        'alerts': [
            {
                'status': 'firing',
                'labels': {'job': 'a'},
                'annotations': {
                    'summary': 'summary that might be forwarded',
                    'title': 'title that might be forwarded',
                },
                'startsAt': '2025-11-20T15:54:41.898000Z',
                'fingerprint': 'fingerprint-a',
            },
            {
                'status': 'firing',
                'labels': {'job': 'b'},
                'annotations': {
                    'summary': 'summary that might be forwarded',
                    'title': 'title that might be forwarded',
                },
                'startsAt': '2025-11-20T15:54:41.898000Z',
                'fingerprint': 'fingerprint-b',
            },
        ]
    }

    response = client.post('/adapt', json=alertmanager_request)

    assert response.status_code == 200
    assert response.json() == {'incident_ids': [30, 31]}


def test_adapt_links_incidents_to_dependent_components(mocked_client, responses, load_component_chain):
    responses.get(
        'http://test-cachet/api/components',
        match=[matchers.query_param_matcher({'filter[name]': 'a', 'include': 'group'})],
        json={
            'data': [{'id': '1', 'attributes': {'name': 'a'}, 'relationships': {'group': {'data': None}}}],
        },
    )
    responses.get(
        'http://test-cachet/api/components',
        match=[matchers.query_param_matcher({'filter[name]': 'b', 'include': 'group'})],
        json={
            'data': [{'id': '2', 'attributes': {'name': 'b'}, 'relationships': {'group': {'data': None}}}],
        },
    )

    cachet_request = {
        'name': 'Component b down',
        'status': 0,
        'message': 'Component b is down.',
        'visible': True,
        'occurred_at': '2025-11-20T15:54:41.898000Z',
        'components': [{'id': 2, 'status': 4}, {'id': 1, 'status': 4}],
    }
    cachet_response = {'data': {'id': '30', 'attributes': {'status': {'value': 0}}}}
    responses.post(
        'http://test-cachet/api/incidents',
        match=[matchers.json_params_matcher(cachet_request, strict_match=False)],
        json=cachet_response,
    )

    alertmanager_request = {
        'alerts': [
            {
                'status': 'firing',
                'labels': {'job': 'b'},
                'annotations': {
                    'description': 'Component b is down.',
                    'title': 'Component b down',
                },
                'startsAt': '2025-11-20T15:54:41.898000Z',
                'fingerprint': 'fingerprint',
            }
        ]
    }

    response = mocked_client.post('/adapt', json=alertmanager_request)

    assert response.status_code == 200
    assert response.json() == {'incident_ids': [30]}


def test_adapt_links_incidents_to_dependent_components_respects_group(database, mocked_client, responses):
    c_to_d = ComponentGraph(
        from_group='special',
        from_component='d',
        to_component='a',
        relationship=ComponentRelationship.REQUIRES,
    )
    with Session(database) as session:
        session.add(c_to_d)
        session.commit()

    responses.get(
        'http://test-cachet/api/components',
        match=[matchers.query_param_matcher({'filter[name]': 'a', 'include': 'group'})],
        json={
            'data': [{'id': '1', 'attributes': {'name': 'a'}, 'relationships': {'group': {'data': None}}}],
        },
    )
    responses.get(
        'http://test-cachet/api/components',
        match=[matchers.query_param_matcher({'filter[name]': 'd', 'include': 'group'})],
        json={
            'data': [
                {'id': '5', 'attributes': {'name': 'd'}, 'relationships': {'group': {'data': {'id': '2'}}}},
                {'id': '6', 'attributes': {'name': 'd'}, 'relationships': {'group': {'data': {'id': '1'}}}},
            ],
            'included': [
                {'id': '1', 'attributes': {'name': 'general'}},
                {'id': '2', 'attributes': {'name': 'special'}},
            ],
        },
    )

    cachet_request = {
        'name': 'Component a down',
        'status': 0,
        'message': 'Component a is down.',
        'visible': True,
        'occurred_at': '2025-11-20T15:54:41.898000Z',
        'components': [{'id': 5, 'status': 4}, {'id': 1, 'status': 4}],
    }
    cachet_response = {'data': {'id': '30', 'attributes': {'status': {'value': 0}}}}
    responses.post(
        'http://test-cachet/api/incidents',
        match=[matchers.json_params_matcher(cachet_request, strict_match=False)],
        json=cachet_response,
    )

    alertmanager_request = {
        'alerts': [
            {
                'status': 'firing',
                'labels': {'job': 'a'},
                'annotations': {
                    'description': 'Component a is down.',
                    'title': 'Component a down',
                },
                'startsAt': '2025-11-20T15:54:41.898000Z',
                'fingerprint': 'fingerprint',
            }
        ]
    }

    response = mocked_client.post('/adapt', json=alertmanager_request)

    assert response.status_code == 200
    assert response.json() == {'incident_ids': [30]}


def test_adapt_dependent_component_respect_relationship(mocked_client, responses, load_component_triangle):
    responses.get(
        'http://test-cachet/api/components',
        match=[matchers.query_param_matcher({'filter[name]': 'a', 'include': 'group'})],
        json={
            'data': [{'id': '1', 'attributes': {'name': 'a'}, 'relationships': {'group': {'data': None}}}],
        },
    )
    responses.get(
        'http://test-cachet/api/components',
        match=[matchers.query_param_matcher({'filter[name]': 'b', 'include': 'group'})],
        json={
            'data': [{'id': '2', 'attributes': {'name': 'b'}, 'relationships': {'group': {'data': None}}}],
        },
    )
    responses.get(
        'http://test-cachet/api/components',
        match=[matchers.query_param_matcher({'filter[name]': 'c', 'include': 'group'})],
        json={
            'data': [{'id': '3', 'attributes': {'name': 'c'}, 'relationships': {'group': {'data': None}}}],
        },
    )

    cachet_request = {
        'name': 'Component c down',
        'status': 0,
        'message': 'Component c is down.',
        'visible': True,
        'occurred_at': '2025-11-20T15:54:41.898000Z',
        'components': [
            {'id': 2, 'status': 3},
            {'id': 3, 'status': 4},
            {'id': 1, 'status': 4},
        ],
    }
    cachet_response = {'data': {'id': '30', 'attributes': {'status': {'value': 0}}}}
    responses.post(
        'http://test-cachet/api/incidents',
        match=[matchers.json_params_matcher(cachet_request, strict_match=False)],
        json=cachet_response,
    )

    alertmanager_request = {
        'alerts': [
            {
                'status': 'firing',
                'labels': {'job': 'c'},
                'annotations': {
                    'description': 'Component c is down.',
                    'title': 'Component c down',
                },
                'startsAt': '2025-11-20T15:54:41.898000Z',
                'fingerprint': 'fingerprint',
            }
        ]
    }

    response = mocked_client.post('/adapt', json=alertmanager_request)

    assert response.status_code == 200
    assert response.json() == {'incident_ids': [30]}


def test_adapt_links_incidents_to_dependent_components_self_no_component(
    mocked_client, responses, load_component_chain
):
    responses.get(
        'http://test-cachet/api/components',
        match=[matchers.query_param_matcher({'filter[name]': 'a', 'include': 'group'})],
        json={
            'data': [{'id': '1', 'attributes': {'name': 'a'}, 'relationships': {'group': {'data': None}}}],
        },
    )
    responses.get(
        'http://test-cachet/api/components',
        match=[matchers.query_param_matcher({'filter[name]': 'b', 'include': 'group'})],
        json={'data': []},
    )

    cachet_request = {
        'name': 'A required downstream component experiences issues',
        'status': 0,
        'message': 'Experiencing issues',
        'visible': True,
        'occurred_at': '2025-11-20T15:54:41.898000Z',
        'components': [{'id': 1, 'status': 4}],
    }
    cachet_response = {'data': {'id': '30', 'attributes': {'status': {'value': 0}}}}
    responses.post(
        'http://test-cachet/api/incidents',
        match=[matchers.json_params_matcher(cachet_request, strict_match=False)],
        json=cachet_response,
    )

    alertmanager_request = {
        'alerts': [
            {
                'status': 'firing',
                'labels': {'job': 'b'},
                'annotations': {
                    'description': 'Component b is down.',
                    'title': 'Component b down',
                },
                'startsAt': '2025-11-20T15:54:41.898000Z',
                'fingerprint': 'fingerprint',
            }
        ]
    }

    response = mocked_client.post('/adapt', json=alertmanager_request)

    assert response.status_code == 200
    assert response.json() == {'incident_ids': [30]}


def test_adapt_links_incidents_to_dependent_components_dependent_no_compnent(
    mocked_client, responses, load_component_chain
):
    responses.get(
        'http://test-cachet/api/components',
        match=[matchers.query_param_matcher({'filter[name]': 'a', 'include': 'group'})],
        json={'data': []},
    )
    responses.get(
        'http://test-cachet/api/components',
        match=[matchers.query_param_matcher({'filter[name]': 'b', 'include': 'group'})],
        json={
            'data': [{'id': '2', 'attributes': {'name': 'b'}, 'relationships': {'group': {'data': None}}}],
        },
    )

    cachet_request = {
        'name': 'Component b down',
        'status': 0,
        'message': 'Component b is down.',
        'visible': True,
        'occurred_at': '2025-11-20T15:54:41.898000Z',
        'components': [{'id': 2, 'status': 4}],
    }
    cachet_response = {'data': {'id': '30', 'attributes': {'status': {'value': 0}}}}
    responses.post(
        'http://test-cachet/api/incidents',
        match=[matchers.json_params_matcher(cachet_request, strict_match=False)],
        json=cachet_response,
    )

    alertmanager_request = {
        'alerts': [
            {
                'status': 'firing',
                'labels': {'job': 'b'},
                'annotations': {
                    'description': 'Component b is down.',
                    'title': 'Component b down',
                },
                'startsAt': '2025-11-20T15:54:41.898000Z',
                'fingerprint': 'fingerprint',
            }
        ]
    }

    response = mocked_client.post('/adapt', json=alertmanager_request)

    assert response.status_code == 200
    assert response.json() == {'incident_ids': [30]}


def test_adapt_links_incidents_to_dependent_components_self_no_component_in_group(
    mocked_client, responses, load_component_chain
):
    responses.get(
        'http://test-cachet/api/components',
        match=[matchers.query_param_matcher({'filter[name]': 'a', 'include': 'group'})],
        json={
            'data': [{'id': '1', 'attributes': {'name': 'a'}, 'relationships': {'group': {'data': None}}}],
        },
    )
    responses.get(
        'http://test-cachet/api/components',
        match=[matchers.query_param_matcher({'filter[name]': 'b', 'include': 'group'})],
        json={
            'data': [{'id': '1', 'attributes': {'name': 'a'}, 'relationships': {'group': {'data': {'id': '2'}}}}],
            'included': [{'id': '2', 'attributes': {'name': 'special'}}],
        },
    )

    cachet_request = {
        'name': 'A required downstream component experiences issues',
        'status': 0,
        'message': 'Experiencing issues',
        'visible': True,
        'occurred_at': '2025-11-20T15:54:41.898000Z',
        'components': [{'id': 1, 'status': 4}],
    }
    cachet_response = {'data': {'id': '30', 'attributes': {'status': {'value': 0}}}}
    responses.post(
        'http://test-cachet/api/incidents',
        match=[matchers.json_params_matcher(cachet_request, strict_match=False)],
        json=cachet_response,
    )

    alertmanager_request = {
        'alerts': [
            {
                'status': 'firing',
                'labels': {'job': 'b'},
                'annotations': {
                    'description': 'Component b is down.',
                    'title': 'Component b down',
                },
                'startsAt': '2025-11-20T15:54:41.898000Z',
                'fingerprint': 'fingerprint',
            }
        ]
    }

    response = mocked_client.post('/adapt', json=alertmanager_request)

    assert response.status_code == 200
    assert response.json() == {'incident_ids': [30]}


def test_adapt_does_create_incident_without_linked_components_if_forced(mocked_client, responses):
    responses.get(
        'http://test-cachet/api/components',
        match=[matchers.query_param_matcher({'filter[name]': 'a', 'include': 'group'})],
        json={
            'data': [],
        },
    )

    cachet_request = {
        'name': 'A required downstream component experiences issues',
        'status': 0,
        'message': 'Experiencing issues',
        'visible': True,
        'occurred_at': '2025-11-20T15:54:41.898000Z',
        'components': [],
    }
    cachet_response = {'data': {'id': '30', 'attributes': {'status': {'value': 0}}}}
    responses.post(
        'http://test-cachet/api/incidents',
        match=[matchers.json_params_matcher(cachet_request, strict_match=False)],
        json=cachet_response,
    )

    alertmanager_request = {
        'alerts': [
            {
                'status': 'firing',
                'labels': {'job': 'a', 'cachet_incident_force': 'true'},
                'annotations': {
                    'description': 'Component a is down.',
                    'title': 'Component a down',
                },
                'startsAt': '2025-11-20T15:54:41.898000Z',
                'fingerprint': 'fingerprint',
            }
        ]
    }

    response = mocked_client.post('/adapt', json=alertmanager_request)

    assert response.status_code == 200
    assert response.json() == {'incident_ids': [30]}


def test_adapt_no_dependent_component(mocked_client, responses):
    responses.get(
        'http://test-cachet/api/components',
        match=[matchers.query_param_matcher({'filter[name]': 'a', 'include': 'group'})],
        json={'data': []},
    )

    alertmanager_request = {
        'alerts': [
            {
                'status': 'firing',
                'labels': {'job': 'a'},
                'annotations': {
                    'description': 'Component a is down.',
                    'title': 'Component a down',
                },
                'startsAt': '2025-11-20T15:54:41.898000Z',
                'fingerprint': 'fingerprint',
            }
        ]
    }
    response = mocked_client.post('/adapt', json=alertmanager_request)

    assert response.status_code == 200
    assert response.json() == {'incident_ids': []}


def test_adapt_respects_severity(mocked_client, responses):
    responses.get(
        'http://test-cachet/api/components',
        match=[matchers.query_param_matcher({'filter[name]': 'a', 'include': 'group'})],
        json={
            'data': [{'id': '1', 'attributes': {'name': 'a'}, 'relationships': {'group': {'data': None}}}],
        },
    )

    cachet_request = {
        'name': 'Component a down',
        'status': 0,
        'message': 'Component a is down.',
        'visible': True,
        'occurred_at': '2025-11-20T15:54:41.898000Z',
        'components': [{'id': 1, 'status': 3}],
    }
    cachet_response = {'data': {'id': '30', 'attributes': {'status': {'value': 0}}}}
    responses.post(
        'http://test-cachet/api/incidents',
        match=[matchers.json_params_matcher(cachet_request, strict_match=False)],
        json=cachet_response,
    )

    alertmanager_request = {
        'alerts': [
            {
                'status': 'firing',
                'labels': {'job': 'a', 'severity': 'warning'},
                'annotations': {
                    'description': 'Component a is down.',
                    'title': 'Component a down',
                },
                'startsAt': '2025-11-20T15:54:41.898000Z',
                'fingerprint': 'fingerprint',
            }
        ]
    }

    response = mocked_client.post('/adapt', json=alertmanager_request)

    assert response.status_code == 200
    assert response.json() == {'incident_ids': [30]}


def test_adapt_respects_severity_for_dependencies(mocked_client, responses, load_component_chain):
    responses.get(
        'http://test-cachet/api/components',
        match=[matchers.query_param_matcher({'filter[name]': 'a', 'include': 'group'})],
        json={
            'data': [{'id': '1', 'attributes': {'name': 'a'}, 'relationships': {'group': {'data': None}}}],
        },
    )
    responses.get(
        'http://test-cachet/api/components',
        match=[matchers.query_param_matcher({'filter[name]': 'b', 'include': 'group'})],
        json={
            'data': [{'id': '2', 'attributes': {'name': 'b'}, 'relationships': {'group': {'data': None}}}],
        },
    )

    cachet_request = {
        'name': 'Component b down',
        'status': 0,
        'message': 'Component b is down.',
        'visible': True,
        'occurred_at': '2025-11-20T15:54:41.898000Z',
        'components': [{'id': 2, 'status': 3}, {'id': 1, 'status': 3}],
    }
    cachet_response = {'data': {'id': '30', 'attributes': {'status': {'value': 0}}}}
    responses.post(
        'http://test-cachet/api/incidents',
        match=[matchers.json_params_matcher(cachet_request, strict_match=False)],
        json=cachet_response,
    )

    alertmanager_request = {
        'alerts': [
            {
                'status': 'firing',
                'labels': {'job': 'b', 'severity': 'warning'},
                'annotations': {
                    'description': 'Component b is down.',
                    'title': 'Component b down',
                },
                'startsAt': '2025-11-20T15:54:41.898000Z',
                'fingerprint': 'fingerprint',
            }
        ]
    }

    response = mocked_client.post('/adapt', json=alertmanager_request)

    assert response.status_code == 200
    assert response.json() == {'incident_ids': [30]}


def test_adapt_updates_existing_incident_on_same_fingerprint(mocked_client, responses):
    response, post = create_default_incident(responses=responses, mocked_client=mocked_client)

    responses.get(
        'http://test-cachet/api/incidents/30',
        json={'data': {'id': '30', 'attributes': {'status': {'value': 0}}}},
    )
    responses.put(
        'http://test-cachet/api/incidents/30',
        match=[
            matchers.header_matcher(
                {
                    'Authorization': 'Bearer my-token',
                    'Content-Type': 'application/json',
                    'Accept': 'application/json',
                }
            ),
            matchers.json_params_matcher({'status': 4}),
        ],
        json={'data': {'id': '30', 'attributes': {'status': {'value': 4}}}},
    )

    alert = {
        'status': 'resolved',
        'labels': {
            'job': 'a',
        },
        'annotations': {
            'description': 'Component a is down.',
            'title': 'Component a down',
        },
        'startsAt': '2025-11-20T15:54:41.898Z',
        'fingerprint': 'fingerprint',
    }
    alertmanager_request = {'alerts': [alert]}

    response = mocked_client.post('/adapt', json=alertmanager_request)
    assert response.status_code == 200
    assert response.json() == {'incident_ids': [30]}

    assert post.call_count == 1


def test_adapt_dont_downgrade_higher_status(mocked_client, responses):
    response, post = create_default_incident(responses=responses, mocked_client=mocked_client)

    responses.get(
        'http://test-cachet/api/incidents/30',
        json={'data': {'id': '30', 'attributes': {'status': {'value': 2}}}},
    )

    alert = {
        'status': 'firing',
        'labels': {
            'job': 'a',
        },
        'annotations': {
            'description': 'Component a is down.',
            'title': 'Component a down',
        },
        'startsAt': '2025-11-20T15:54:41.898Z',
        'fingerprint': 'fingerprint',
    }
    alertmanager_request = {'alerts': [alert]}

    response = mocked_client.post('/adapt', json=alertmanager_request)
    assert response.status_code == 200
    assert response.json() == {'incident_ids': [30]}

    assert post.call_count == 1


def test_adapt_creates_new_incident_if_previous_fixed(mocked_client, responses):
    """
    The Alertmanager fingerprint is not unique, it is only a hash of the labels.
    Yet the same alert should create two incidents if it was resolved in between, see #20.
    """
    # Preparation
    ## Create first incident
    _, post_a = create_default_incident(responses=responses, mocked_client=mocked_client)

    ## Resolve incident
    responses.get(
        'http://test-cachet/api/incidents/30',
        json={'data': {'id': '30', 'attributes': {'status': {'value': 0}}}},
    )
    cachet_header = {
        'Authorization': 'Bearer my-token',
        'Content-Type': 'application/json',
        'Accept': 'application/json',
    }
    responses.put(
        'http://test-cachet/api/incidents/30',
        match=[
            matchers.header_matcher(cachet_header),
            matchers.json_params_matcher({'status': 4}),
        ],
        json={'data': {'id': '30', 'attributes': {'status': {'value': 4}}}},
    )
    alert = {
        'status': 'resolved',
        'labels': {
            'job': 'a',
        },
        'annotations': {
            'description': 'Component a is down.',
            'title': 'Component a down',
        },
        'startsAt': '2025-11-20T15:54:41.898Z',
        'fingerprint': 'fingerprint',
    }
    alertmanager_request = {'alerts': [alert]}
    response = mocked_client.post('/adapt', json=alertmanager_request)
    assert response.status_code == 200
    assert response.json() == {'incident_ids': [30]}

    # Test
    ## Create new incident although the fingerprint is the same
    cachet_request = {
        'name': 'Component a down',
        'status': 0,
        'message': 'Component a is down.',
        'visible': True,
        'occurred_at': '2025-11-21T15:54:41.898000Z',
        'components': [{'id': 1, 'status': 4}],
    }
    post_b = responses.post(
        'http://test-cachet/api/incidents',
        match=[matchers.json_params_matcher(cachet_request)],
        json={'data': {'id': '31', 'attributes': {'status': {'value': 0}}}},
    )

    alert = {
        'status': 'firing',
        'labels': {
            'job': 'a',
        },
        'annotations': {
            'description': 'Component a is down.',
            'title': 'Component a down',
        },
        'startsAt': '2025-11-21T15:54:41.898Z',
        'fingerprint': 'fingerprint',
    }
    alertmanager_request = {'alerts': [alert]}
    response = mocked_client.post('/adapt', json=alertmanager_request)
    assert response.status_code == 200
    assert response.json() == {'incident_ids': [31]}

    assert post_a.call_count == 1
    assert post_b.call_count == 1


def test_adapt_marks_dependents_requiering_supplier_as_major_outage(mocked_client, load_component_chain, responses):
    responses.get(
        'http://test-cachet/api/components',
        match=[matchers.query_param_matcher({'filter[name]': 'a', 'include': 'group'})],
        json={
            'data': [{'id': '1', 'attributes': {'name': 'a'}, 'relationships': {'group': {'data': None}}}],
        },
    )
    responses.get(
        'http://test-cachet/api/components',
        match=[matchers.query_param_matcher({'filter[name]': 'b', 'include': 'group'})],
        json={
            'data': [{'id': '2', 'attributes': {'name': 'b'}, 'relationships': {'group': {'data': None}}}],
        },
    )

    responses.post(
        'http://test-cachet/api/incidents',
        match=[
            matchers.json_params_matcher(
                {
                    'name': 'Component b down',
                    'status': 0,
                    'message': 'Component b is down.',
                    'visible': True,
                    'occurred_at': '2025-11-20T15:54:41.898000Z',
                    'components': [{'id': 2, 'status': 4}, {'id': 1, 'status': 4}],
                }
            ),
        ],
        json={'data': {'id': '30', 'attributes': {'status': {'value': 0}}}},
    )

    alert = {
        'status': 'firing',
        'labels': {'job': 'b'},
        'annotations': {
            'description': 'Component b is down.',
            'title': 'Component b down',
        },
        'startsAt': '2025-11-20T15:54:41.898Z',
        'fingerprint': 'fingerprint-b',
    }

    response = mocked_client.post('/adapt', json={'alerts': [alert]})
    assert response.status_code == 200
    assert response.json() == {'incident_ids': [30]}


def test_adapt_marks_dependents_optionally_relying_on_supplier_as_partial_outage(
    mocked_client, load_component_chain, responses
):
    responses.get(
        'http://test-cachet/api/components',
        match=[matchers.query_param_matcher({'filter[name]': 'a', 'include': 'group'})],
        json={
            'data': [{'id': '1', 'attributes': {'name': 'a'}, 'relationships': {'group': {'data': None}}}],
        },
    )
    responses.get(
        'http://test-cachet/api/components',
        match=[matchers.query_param_matcher({'filter[name]': 'b', 'include': 'group'})],
        json={
            'data': [{'id': '2', 'attributes': {'name': 'b'}, 'relationships': {'group': {'data': None}}}],
        },
    )
    responses.get(
        'http://test-cachet/api/components',
        match=[matchers.query_param_matcher({'filter[name]': 'c', 'include': 'group'})],
        json={
            'data': [{'id': '3', 'attributes': {'name': 'c'}, 'relationships': {'group': {'data': None}}}],
        },
    )

    responses.post(
        'http://test-cachet/api/incidents',
        match=[
            matchers.json_params_matcher(
                {
                    'name': 'Component c down',
                    'status': 0,
                    'message': 'Component c is down.',
                    'visible': True,
                    'occurred_at': '2025-11-20T15:54:41.898000Z',
                    'components': [
                        {'id': 2, 'status': 3},
                        {'id': 1, 'status': 3},
                        {'id': 3, 'status': 4},
                    ],
                }
            ),
        ],
        json={'data': {'id': '30', 'attributes': {'status': {'value': 0}}}},
    )

    alert = {
        'status': 'firing',
        'labels': {'job': 'c'},
        'annotations': {
            'description': 'Component c is down.',
            'title': 'Component c down',
        },
        'startsAt': '2025-11-20T15:54:41.898Z',
        'fingerprint': 'fingerprint-c',
    }

    response = mocked_client.post('/adapt', json={'alerts': [alert]})
    assert response.status_code == 200
    assert response.json() == {'incident_ids': [30]}


def test_adapt_pulled_incident_unknown_active(mocked_client, responses):
    responses.get(
        'http://test-cachet/api/components',
        match=[matchers.query_param_matcher({'filter[name]': 'a', 'include': 'group'})],
        json={
            'data': [{'id': '1', 'attributes': {'name': 'a'}, 'relationships': {'group': {'data': None}}}],
        },
    )

    cachet_request = {
        'name': 'Component a down',
        'status': 0,
        'message': 'Component a is down.',
        'visible': True,
        'occurred_at': '2025-11-20T15:54:41.898000Z',
        'components': [{'id': 1, 'status': 4}],
    }
    cachet_header = {
        'Authorization': 'Bearer my-token',
        'Content-Type': 'application/json',
        'Accept': 'application/json',
    }
    cachet_response = {'data': {'id': '30', 'attributes': {'status': {'value': 0}}}}
    responses.post(
        'http://test-cachet/api/incidents',
        match=[
            matchers.json_params_matcher(cachet_request, strict_match=False),
            matchers.header_matcher(cachet_header),
        ],
        json=cachet_response,
    )

    alertmanager_request = [
        {
            'annotations': {
                'description': 'Component a is down.',
                'title': 'Component a down',
            },
            'fingerprint': 'alert-fingerprint',
            'startsAt': '2025-11-20T15:54:41.898Z',
            'status': {'inhibitedBy': [], 'silencedBy': [], 'state': 'active'},
            'labels': {'job': 'a'},
        },
    ]
    response = mocked_client.post('/adapt', json=alertmanager_request, params={'prune': True})

    assert response.status_code == 200
    assert response.json() == {'incident_ids': [30]}


def test_adapt_pulled_incident_unknown_suppressed(mocked_client, responses):
    responses.get(
        'http://test-cachet/api/components',
        match=[matchers.query_param_matcher({'filter[name]': 'a', 'include': 'group'})],
        json={
            'data': [{'id': '1', 'attributes': {'name': 'a'}, 'relationships': {'group': {'data': None}}}],
        },
    )

    cachet_request = {
        'name': 'Component a down',
        'status': 1,
        'message': 'Component a is down.',
        'visible': True,
        'occurred_at': '2025-11-20T15:54:41.898000Z',
        'components': [{'id': 1, 'status': 4}],
    }
    cachet_header = {
        'Authorization': 'Bearer my-token',
        'Content-Type': 'application/json',
        'Accept': 'application/json',
    }
    cachet_response = {'data': {'id': '30', 'attributes': {'status': {'value': 1}}}}
    responses.post(
        'http://test-cachet/api/incidents',
        match=[
            matchers.json_params_matcher(cachet_request, strict_match=False),
            matchers.header_matcher(cachet_header),
        ],
        json=cachet_response,
    )

    alertmanager_request = [
        {
            'annotations': {
                'description': 'Component a is down.',
                'title': 'Component a down',
            },
            'fingerprint': 'alert-fingerprint',
            'startsAt': '2025-11-20T15:54:41.898Z',
            'status': {
                'inhibitedBy': [],
                'silencedBy': ['b986455c-9ba9-4059-9e6b-e3bce51105fc'],
                'state': 'suppressed',
            },
            'labels': {'job': 'a'},
        },
    ]
    response = mocked_client.post('/adapt', json=alertmanager_request, params={'prune': True})

    assert response.status_code == 200
    assert response.json() == {'incident_ids': [30]}


def test_adapt_pulled_incident_known_suppressed(mocked_client, responses):
    # Preparation: register an incident
    _, _ = create_default_incident(responses=responses, mocked_client=mocked_client)

    # Now the actual test: update it as it is now suppressed
    responses.get(
        'http://test-cachet/api/incidents/30',
        json={'data': {'id': '30', 'attributes': {'status': {'value': 0}}}},
    )
    responses.put(
        'http://test-cachet/api/incidents/30',
        match=[
            matchers.json_params_matcher({'status': 1}),
        ],
        json={'data': {'id': '30', 'attributes': {'status': {'value': 1}}}},
    )

    alertmanager_request = [
        {
            'annotations': {
                'description': 'Component a is down.',
                'title': 'Component a down',
            },
            'fingerprint': 'fingerprint',
            'startsAt': '2025-11-20T15:54:41.898Z',
            'status': {
                'inhibitedBy': [],
                'silencedBy': ['b986455c-9ba9-4059-9e6b-e3bce51105fc'],
                'state': 'suppressed',
            },
            'labels': {'job': 'a'},
        },
    ]
    response = mocked_client.post('/adapt', json=alertmanager_request, params={'prune': True})

    assert response.status_code == 200
    assert response.json() == {'incident_ids': [30]}


def test_adapt_prune_known_incident_resolved_while_suppressed(mocked_client, responses):
    # Preparation: register an incident
    _, _ = create_default_incident(responses=responses, mocked_client=mocked_client)

    # Now the actual test: update it as fixed as it is no longer present in the Alertmanager API
    responses.put(
        'http://test-cachet/api/incidents/30',
        match=[
            matchers.json_params_matcher({'status': 4}),
        ],
        json={'data': {'id': '30', 'attributes': {'status': {'value': 4}}}},
    )

    alertmanager_request = []
    response = mocked_client.post('/adapt', json=alertmanager_request, params={'prune': True})

    assert response.status_code == 200
    assert response.json() == {'incident_ids': [30]}
