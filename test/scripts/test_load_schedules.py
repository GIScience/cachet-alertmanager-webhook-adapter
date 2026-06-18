from datetime import timedelta

from icalendar import Calendar
from responses import matchers

from cachet_adapter.scripts.load_schedules import load_schedules
from test.conftest import TEST_RESOURCES


def test_load_schedules(responses, frozen_time):
    responses.post(
        'http://test-adapter/adapter/schedule',
        match=[
            matchers.json_params_matcher(
                [
                    {
                        'id': 'VEVENT##2026-06-01T12:00:00+02:00#8906ea5d-d770-4b62-956a-5c73f4e654f1',
                        'name': 'Update',
                        'message': 'A scheduled downtime',
                        'scheduled_at': '2026-06-01T12:00:00+02:00',
                        'completed_at': '2026-06-01T12:30:00+02:00',
                        'components': {'': ['a']},
                    },
                    {
                        'id': 'VEVENT##2026-06-01T12:00:00+02:00#78d7aefe-f7df-4154-8415-6cabc591d584',
                        'name': 'Update',
                        'message': 'A scheduled downtime',
                        'scheduled_at': '2026-06-01T12:00:00+02:00',
                        'completed_at': '2026-06-01T12:30:00+02:00',
                        'components': None,
                    },
                ]
            )
        ],
    )

    with open(TEST_RESOURCES / 'schedules.ics', 'r') as f:
        calendar = Calendar.from_ical(f.read())

    load_schedules(calendar=calendar, adapter_url='http://test-adapter/adapter', target_event_titles=['Update'])


def test_load_schedules_for_all_components(responses, frozen_time):
    responses.post(
        'http://test-adapter/adapter/schedule',
        match=[
            matchers.json_params_matcher(
                [
                    {
                        'id': 'VEVENT##2026-06-01T12:00:00+02:00#8906ea5d-d770-4b62-956a-5c73f4e654f1',
                        'name': 'Update',
                        'message': 'A scheduled downtime',
                        'scheduled_at': '2026-06-01T12:00:00+02:00',
                        'completed_at': '2026-06-01T12:30:00+02:00',
                        'components': 'all',
                    },
                ]
            )
        ],
    )

    with open(TEST_RESOURCES / 'schedules_all_components.ics', 'r') as f:
        calendar = Calendar.from_ical(f.read())

    load_schedules(
        calendar=calendar,
        adapter_url='http://test-adapter/adapter',
        target_event_titles=['Update'],
        calendar_monitoring_time_range=timedelta(weeks=3),
    )


def test_load_recurring_events(responses, frozen_time):
    responses.post(
        'http://test-adapter/adapter/schedule',
        match=[
            matchers.json_params_matcher(
                [
                    {
                        'id': 'VEVENT##2026-06-01T12:00:00+02:00#040000008200E00074C5B7101A82E008000000001761DBD484F9DC01000000000000000010000000E37C66B00CA51447A386C62D5CEEE1F8',
                        'name': 'Update',
                        'message': 'A scheduled downtime',
                        'scheduled_at': '2026-06-01T12:00:00+02:00',
                        'completed_at': '2026-06-01T12:30:00+02:00',
                        'components': None,
                    },
                    {
                        'id': 'VEVENT##2026-06-08T12:00:00+02:00#040000008200E00074C5B7101A82E008000000001761DBD484F9DC01000000000000000010000000E37C66B00CA51447A386C62D5CEEE1F8',
                        'name': 'Update',
                        'message': 'A scheduled downtime',
                        'scheduled_at': '2026-06-08T12:00:00+02:00',
                        'completed_at': '2026-06-08T12:30:00+02:00',
                        'components': None,
                    },
                    {
                        'id': 'VEVENT##2026-06-15T12:00:00+02:00#040000008200E00074C5B7101A82E008000000001761DBD484F9DC01000000000000000010000000E37C66B00CA51447A386C62D5CEEE1F8',
                        'name': 'Update',
                        'message': 'A scheduled downtime',
                        'scheduled_at': '2026-06-15T12:00:00+02:00',
                        'completed_at': '2026-06-15T12:30:00+02:00',
                        'components': None,
                    },
                ]
            )
        ],
    )

    with open(TEST_RESOURCES / 'recurring.ics', 'r') as f:
        calendar = Calendar.from_ical(f.read())

    load_schedules(
        calendar=calendar,
        adapter_url='http://test-adapter/adapter',
        target_event_titles=['Update'],
        calendar_monitoring_time_range=timedelta(weeks=3),
    )


def test_load_adapted_recurring_events(responses, frozen_time):
    responses.post(
        'http://test-adapter/adapter/schedule',
        match=[
            matchers.json_params_matcher(
                [
                    {
                        'id': 'VEVENT##2026-06-01T12:00:00+02:00#040000008200E00074C5B7101A82E008000000001761DBD484F9DC01000000000000000010000000E37C66B00CA51447A386C62D5CEEE1F8',
                        'name': 'Update',
                        'message': 'A scheduled downtime',
                        'scheduled_at': '2026-06-01T12:00:00+02:00',
                        'completed_at': '2026-06-01T12:30:00+02:00',
                        'components': None,
                    },
                    {
                        'id': 'VEVENT##2026-06-08T12:00:00+02:00#040000008200E00074C5B7101A82E008000000001761DBD484F9DC01000000000000000010000000E37C66B00CA51447A386C62D5CEEE1F8',
                        'name': 'Update',
                        'message': 'A scheduled downtime',
                        'scheduled_at': '2026-06-08T12:00:00+02:00',
                        'completed_at': '2026-06-08T12:30:00+02:00',
                        'components': None,
                    },
                    {
                        'id': 'VEVENT#2026-06-15T10:00:00#2026-06-16T12:00:00+02:00#040000008200E00074C5B7101A82E008000000001761DBD484F9DC01000000000000000010000000E37C66B00CA51447A386C62D5CEEE1F8',
                        'name': 'Update',
                        'message': 'A scheduled downtime',
                        'scheduled_at': '2026-06-16T12:00:00+02:00',
                        'completed_at': '2026-06-16T12:30:00+02:00',
                        'components': None,
                    },
                ]
            )
        ],
    )

    with open(TEST_RESOURCES / 'duplicate_ids.ics', 'r') as f:
        calendar = Calendar.from_ical(f.read())

    load_schedules(
        calendar=calendar,
        adapter_url='http://test-adapter/adapter',
        target_event_titles=['Update'],
        calendar_monitoring_time_range=timedelta(weeks=3),
    )
