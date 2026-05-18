from responses import matchers
from sqlmodel import Session

from cachet_adapter.models.database import ComponentGraph, ComponentRelationship


def test_adapt_creates_incident(mocked_client, responses):
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
    cachet_response = {'data': {'id': '30'}}
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
    cachet_response = {'data': {'id': '30'}}
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
    cachet_response = {'data': {'id': '30'}}
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
    cachet_response = {'data': {'id': '30'}}
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
    cachet_response = {'data': {'id': '30'}}
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
    cachet_response = {'data': {'id': '30'}}
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
    cachet_response = {'data': {'id': '30'}}
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
    cachet_response = {'data': {'id': '30'}}
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
        'name': 'Component b down',
        'status': 0,
        'message': 'Component b is down.',
        'visible': False,
        'occurred_at': '2025-11-20T15:54:41.898000Z',
        'components': [{'id': 1, 'status': 4}],
    }
    cachet_response = {'data': {'id': '30'}}
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
    cachet_response = {'data': {'id': '30'}}
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
        'name': 'Component b down',
        'status': 0,
        'message': 'Component b is down.',
        'visible': False,
        'occurred_at': '2025-11-20T15:54:41.898000Z',
        'components': [{'id': 1, 'status': 4}],
    }
    cachet_response = {'data': {'id': '30'}}
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


def test_adapt_no_dependent_component(mocked_client, responses):
    responses.get(
        'http://test-cachet/api/components',
        match=[matchers.query_param_matcher({'filter[name]': 'a', 'include': 'group'})],
        json={'data': []},
    )

    cachet_request = {
        'name': 'Component a down',
        'status': 0,
        'message': 'Component a is down.',
        'visible': False,
        'occurred_at': '2025-11-20T15:54:41.898000Z',
        'components': [],
    }
    cachet_response = {'data': {'id': '30'}}
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
    cachet_response = {'data': {'id': '30'}}
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
    cachet_response = {'data': {'id': '30'}}
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
    responses.get(
        'http://test-cachet/api/components',
        match=[matchers.query_param_matcher({'filter[name]': 'a', 'include': 'group'})],
        json={
            'data': [{'id': '1', 'attributes': {'name': 'a'}, 'relationships': {'group': {'data': None}}}],
        },
    )

    cachet_header = {
        'Authorization': 'Bearer my-token',
        'Content-Type': 'application/json',
        'Accept': 'application/json',
    }
    post = responses.post(
        'http://test-cachet/api/incidents',
        json={'data': {'id': '30'}},
    )
    responses.put(
        'http://test-cachet/api/incidents/30',
        match=[
            matchers.header_matcher(cachet_header),
            matchers.json_params_matcher(
                {
                    'name': 'Instance down',
                    'status': 0,
                    'message': 'Service is down.',
                    'visible': True,
                    'occurred_at': '2025-11-20T15:54:41.898000Z',
                    'components': [{'id': 1, 'status': 4}],
                }
            ),
        ],
        json={'data': {'id': '30'}},
    )

    alert = {
        'status': 'firing',
        'labels': {
            'job': 'a',
        },
        'annotations': {
            'description': 'Service is down.',
            'title': 'Instance down',
        },
        'startsAt': '2025-11-20T15:54:41.898Z',
        'fingerprint': 'same-fingerprint',
    }
    alertmanager_request = {'alerts': [alert]}

    response = mocked_client.post('/adapt', json=alertmanager_request)
    assert response.status_code == 200
    assert response.json() == {'incident_ids': [30]}

    response = mocked_client.post('/adapt', json=alertmanager_request)
    assert response.status_code == 200
    assert response.json() == {'incident_ids': [30]}

    assert post.call_count == 1


def test_adapt_marks_incident_fixed_on_resolved_alert(mocked_client, responses):
    responses.get(
        'http://test-cachet/api/components',
        match=[matchers.query_param_matcher({'filter[name]': 'a', 'include': 'group'})],
        json={
            'data': [{'id': '1', 'attributes': {'name': 'a'}, 'relationships': {'group': {'data': None}}}],
        },
    )

    responses.post(
        'http://test-cachet/api/incidents',
        json={'data': {'id': '30'}},
    )
    responses.put(
        'http://test-cachet/api/incidents/30',
        match=[
            matchers.json_params_matcher(
                {
                    'name': 'Instance down',
                    'status': 4,
                    'message': 'Service is down.',
                    'visible': True,
                    'occurred_at': '2025-11-20T15:54:41.898000Z',
                    'components': [{'id': 1, 'status': 4}],
                }
            ),
        ],
        json={'data': {'id': '30'}},
    )

    firing_alert = {
        'status': 'firing',
        'labels': {'job': 'a'},
        'annotations': {
            'description': 'Service is down.',
            'title': 'Instance down',
        },
        'startsAt': '2025-11-20T15:54:41.898Z',
        'fingerprint': 'alert-fingerprint',
    }

    response = mocked_client.post('/adapt', json={'alerts': [firing_alert]})
    assert response.status_code == 200
    assert response.json() == {'incident_ids': [30]}

    resolved_alert = {
        'status': 'resolved',
        'labels': {'job': 'a'},
        'annotations': {
            'description': 'Service is down.',
            'title': 'Instance down',
        },
        'startsAt': '2025-11-20T15:54:41.898Z',
        'fingerprint': 'alert-fingerprint',
    }

    response = mocked_client.post('/adapt', json={'alerts': [resolved_alert]})
    assert response.status_code == 200
    assert response.json() == {'incident_ids': [30]}


def test_adapt_marks_required_dependents_as_major_outage(mocked_client, load_component_chain, responses):
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
        json={'data': {'id': '30'}},
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


def test_adapt_marks_optional_dependents_as_partial_outage(mocked_client, load_component_chain, responses):
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
        json={'data': {'id': '30'}},
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
