from responses import matchers

from cachet_adapter.scripts.sync_alerts import AlertmanagerApi, sync_alerts


def test_sync_alerts(responses):
    responses.get(
        'http://test-alertmanager/api/v2/alerts',
        match=[
            matchers.header_matcher(
                {
                    'Authorization': 'Basic dGVzdC11c2VyOnRlc3QtcHc=',
                    'Content-Type': 'application/json',
                    'Accept': 'application/json',
                }
            )
        ],
        json=[
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
        ],
    )

    responses.post(
        'http://test-adapter/adapter/adapt',
        match=[
            matchers.query_param_matcher({'prune': True}),
            matchers.json_params_matcher(
                [
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
            ),
        ],
    )

    alertmanager_api = AlertmanagerApi(
        base_url='http://test-alertmanager/api/v2', username='test-user', password='test-pw'
    )
    sync_alerts(alertmanager_api=alertmanager_api, adapter_url='http://test-adapter/adapter', prune=True)
