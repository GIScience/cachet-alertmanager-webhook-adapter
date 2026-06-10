from ics import Calendar
from responses import matchers

from cachet_adapter.scripts.load_schedules import load_schedules
from test.conftest import TEST_RESOURCES


def test_load_schedules(responses):
    responses.post(
        'http://test-adapter/adapter/schedule',
        match=[
            matchers.json_params_matcher(
                [
                    {
                        'id': '3371b318-23a6-4621-b157-201e428c6e47',
                        'name': 'Update',
                        'message': 'A scheduled downtime',
                        'scheduled_at': '2020-09-10T22:00:00+02:00',
                        'completed_at': '2020-09-10T22:00:00+02:00',
                        'components': {'': ['a']},
                    },
                    {
                        'id': '8906ea5d-d770-4b62-956a-5c73f4e654f1',
                        'name': 'Update',
                        'message': 'A scheduled downtime',
                        'scheduled_at': '2020-09-10T22:00:00+02:00',
                        'completed_at': '3020-09-10T22:00:00+01:00',
                        'components': {'': ['a']},
                    },
                ]
            )
        ],
    )

    with open(TEST_RESOURCES / 'schedules.ics', 'r') as f:
        calendar = Calendar(f.read())

    load_schedules(calendar=calendar, adapter_url='http://test-adapter/adapter', target_event_titles=['Update'])
