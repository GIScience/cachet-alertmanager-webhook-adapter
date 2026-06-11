from requests import Response
from responses import matchers


def create_default_schedule(responses, mocked_client) -> Response:
    responses.get(
        'http://test-cachet/api/components',
        match=[matchers.query_param_matcher({'filter[name]': 'a', 'include': 'group'})],
        json={
            'data': [{'id': '1', 'attributes': {'name': 'a'}, 'relationships': {'group': {'data': None}}}],
        },
    )

    responses.get(
        'http://test-cachet/api/schedules',
        json={'data': []},
    )

    responses.post(
        'http://test-cachet/api/schedules',
        match=[
            matchers.json_params_matcher(
                {
                    'name': 'Schedule one',
                    'message': 'Updates',
                    'scheduled_at': '2025-11-07 05:31:56',
                    'completed_at': '3026-11-07 06:31:56',
                    'components': [{'id': 1, 'status': 4}],
                }
            )
        ],
        json={
            'data': {'id': '1'},
        },
    )

    schedule_request = [
        {
            'id': 'event-1',
            'name': 'Schedule one',
            'message': 'Updates',
            'scheduled_at': '2025-11-07T05:31:56Z',
            'completed_at': '3026-11-07T06:31:56Z',
            'components': {'': ['a']},
        }
    ]
    response = mocked_client.post('/schedule', json=schedule_request)

    return response


def test_create_future_ending_schedule(mocked_client, responses):
    response = create_default_schedule(responses, mocked_client)

    assert response.status_code == 200
    assert response.json() == {'schedule_ids': [1]}


def test_create_schedule_with_none_component(mocked_client, responses):
    responses.get(
        'http://test-cachet/api/schedules',
        json={'data': []},
    )

    responses.post(
        'http://test-cachet/api/schedules',
        match=[
            matchers.json_params_matcher(
                {
                    'name': 'Schedule one',
                    'message': 'Updates',
                    'scheduled_at': '2025-11-07 05:31:56',
                    'completed_at': '3026-11-07 06:31:56',
                }
            )
        ],
        json={
            'data': {'id': '1'},
        },
    )

    schedule_request = [
        {
            'id': 'event-1',
            'name': 'Schedule one',
            'message': 'Updates',
            'scheduled_at': '2025-11-07T05:31:56Z',
            'completed_at': '3026-11-07T06:31:56Z',
            'components': None,
        }
    ]
    response = mocked_client.post('/schedule', json=schedule_request)
    assert response.status_code == 200
    assert response.json() == {'schedule_ids': [1]}


def test_update_known_schedule(mocked_client, responses):
    create_default_schedule(responses, mocked_client)

    responses.get(
        'http://test-cachet/api/schedules',
        json={'data': [{'id': 1}]},
    )

    responses.put(
        'http://test-cachet/api/schedules/1',
        match=[
            matchers.json_params_matcher(
                {
                    'scheduled_at': '2026-11-07 05:31:56',
                    'completed_at': '2027-11-07 06:31:56',
                    'components': [{'id': 1, 'status': 4}],
                }
            )
        ],
        json={
            'data': {'id': '1'},
        },
    )

    updated_schedule_request = [
        {
            'id': 'event-1',
            'name': 'Schedule one',
            'message': 'Updates',
            'scheduled_at': '2026-11-07T05:31:56Z',
            'completed_at': '2027-11-07T06:31:56Z',
            'components': {'': ['a']},
        }
    ]

    response = mocked_client.post('/schedule', json=updated_schedule_request)

    assert response.status_code == 200
    assert response.json() == {'schedule_ids': [1]}


def test_update_schedule_with_none_component(mocked_client, responses):
    create_default_schedule(responses, mocked_client)

    responses.get(
        'http://test-cachet/api/schedules',
        json={'data': [{'id': 1}]},
    )

    responses.put(
        'http://test-cachet/api/schedules/1',
        match=[
            matchers.json_params_matcher(
                {
                    'scheduled_at': '2026-11-07 05:31:56',
                    'completed_at': '2027-11-07 06:31:56',
                }
            )
        ],
        json={
            'data': {'id': '1'},
        },
    )

    updated_schedule_request = [
        {
            'id': 'event-1',
            'name': 'Schedule one',
            'message': 'Updates',
            'scheduled_at': '2026-11-07T05:31:56Z',
            'completed_at': '2027-11-07T06:31:56Z',
            'components': None,
        }
    ]

    response = mocked_client.post('/schedule', json=updated_schedule_request)

    assert response.status_code == 200
    assert response.json() == {'schedule_ids': [1]}


def test_ignore_unknown_past_schedule(mocked_client, responses):
    responses.get(
        'http://test-cachet/api/components',
        match=[matchers.query_param_matcher({'filter[name]': 'a', 'include': 'group'})],
        json={
            'data': [{'id': '1', 'attributes': {'name': 'a'}, 'relationships': {'group': {'data': None}}}],
        },
    )

    responses.get(
        'http://test-cachet/api/schedules',
        json={'data': []},
    )

    schedule_request = [
        {
            'id': 'event-1',
            'name': 'Schedule one',
            'message': 'Updates',
            'scheduled_at': '1026-11-07T05:31:56Z',
            'completed_at': '1026-11-07T06:31:56Z',
            'components': {'': ['a']},
        }
    ]
    response = mocked_client.post('/schedule', json=schedule_request)

    assert response.status_code == 200
    assert response.json() == {'schedule_ids': []}


def test_sync_deleted_schedule(mocked_client, responses):
    create_default_schedule(responses, mocked_client)

    responses.get(
        'http://test-cachet/api/schedules',
        json={'data': [{'id': '1'}]},
    )
    responses.delete('http://test-cachet/api/schedules/1')
    pruned_schedule_request = []
    response = mocked_client.post('/schedule', params={'prune': True}, json=pruned_schedule_request)

    assert response.status_code == 200

    # If we send the same schedule again, it gets recrated

    responses.post(
        'http://test-cachet/api/schedules',
        match=[
            matchers.json_params_matcher(
                {
                    'name': 'Schedule one',
                    'message': 'Updates',
                    'scheduled_at': '2025-11-07 05:31:56',
                    'completed_at': '3026-11-07 06:31:56',
                    'components': [{'id': 1, 'status': 4}],
                }
            )
        ],
        json={
            'data': {'id': '2'},
        },
    )

    schedule_request = [
        {
            'id': 'event-1',
            'name': 'Schedule one',
            'message': 'Updates',
            'scheduled_at': '2025-11-07T05:31:56Z',
            'completed_at': '3026-11-07T06:31:56Z',
            'components': {'': ['a']},
        }
    ]
    response = mocked_client.post('/schedule', json=schedule_request)
    assert response.status_code == 200
    assert response.json() == {'schedule_ids': [2]}


def test_ignore_manually_added_schedule(mocked_client, responses):
    responses.get(
        'http://test-cachet/api/schedules',
        json={'data': [{'id': '1'}]},
    )
    schedule_request = []
    response = mocked_client.post('/schedule', params={'prune': True}, json=schedule_request)

    assert response.status_code == 200
