import argparse
import json
import logging
from datetime import UTC, datetime, timedelta
from json import JSONDecodeError

import recurring_ical_events
import requests
from icalendar import Calendar

from cachet_adapter.models.api import ScheduledIncident

log = logging.getLogger(__name__)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog='Load Schedules', description='Load a ICS calendar as scheduled maintenance messages'
    )
    parser.add_argument('adapter_url')

    exclusive_group = parser.add_mutually_exclusive_group()
    exclusive_group.add_argument(
        '--file',
        dest='file',
        default='data/schedules.ics',
        help='An .ics file to read schedules from, defaults to data/schedules.ics .',
    )
    exclusive_group.add_argument(
        '--url',
        dest='url',
        required=False,
        help='An ICS-URL to load schedules from. This and the file are mutually exclusive.',
    )

    parser.add_argument(
        '--event-titles',
        nargs='*',
        type=str,
        default=[],
        help='Event titles that should be included in the scheduled maintenances. '
        'All events with non-mathing titles, will be ignored.',
    )
    parser.add_argument(
        '--link-all-components-keyword',
        type=str,
        default='[cachet:all]',
        help='A string sequence that tells the script to link all components in cachet to the schedule.'
        'Otherwise the event-message must be a JSON of components equal to the one used in `load-components`.'
        'If both are not there, no component will be linked.',
    )

    parser.add_argument(
        '--prune',
        action='store_true',
        dest='prune',
        default=False,
        help='!Attention: danger zone! This will delete any schedule known to the adapter and not specified in the '
        'calendar.'
        'The Cachet will then be in-synch with the file (except manually created schedules).',
    )

    args = parser.parse_args()

    return args


def main():
    args = parse_args()
    if args.url:
        response = requests.get(args.url)
        response.raise_for_status()
        data = response.text
    else:
        with open(args.file, 'r') as f:
            data = f.read()
    calendar = Calendar.from_ical(data)

    load_schedules(
        calendar=calendar,
        adapter_url=args.adapter_url,
        target_event_titles=args.event_titles,
        prune=args.prune,
        all_components_keyword=args.link_all_components_keyword,
    )


def load_schedules(
    calendar: Calendar,
    adapter_url: str,
    target_event_titles: list[str],
    all_components_keyword: str = '[cachet:all]',
    calendar_monitoring_time_range: timedelta = timedelta(weeks=4),
    prune: bool = False,
) -> None:
    from_ts = datetime.now(tz=UTC) - calendar_monitoring_time_range
    to_ts = datetime.now(tz=UTC) + calendar_monitoring_time_range
    recurring_events = recurring_ical_events.of(calendar)
    # protected function will be published in next release of library:
    events = recurring_events._occurrences_between(start=from_ts, end=to_ts)

    schedules = list()
    for event in events:
        parent_event = event.as_component(keep_recurrence_attributes=True)

        if len(target_event_titles) > 0 and parent_event.get('summary') not in target_event_titles:
            log.debug(
                f'Event {event.id} is skipped because its title {parent_event.get("summary")} is not in the '
                f'specified target set {target_event_titles}.'
            )
            continue

        schedule_id = event.id.to_string()
        schedule_name = parent_event.get('summary', 'Scheduled Downtime')
        schedule_description = parent_event.get('description', '')

        try:
            components = json.loads(schedule_description)
        except JSONDecodeError:
            if all_components_keyword in schedule_description:
                components = 'all'
            else:
                log.warning(
                    f'Event description '
                    f''
                    f'{schedule_description}'
                    f''
                    f'for event {event.id.to_string()} does not contain a valid '
                    f'component-set in JSON format or the keyword to link all components: {all_components_keyword}.'
                    'Creating a scheduled downtime without linked components.'
                )
                components = None

        scheduled_incident = ScheduledIncident(
            id=schedule_id,
            name=schedule_name,
            scheduled_at=event.start,
            completed_at=event.end,
            components=components,
        )
        schedules.append(scheduled_incident.model_dump(mode='json'))

    if schedules:
        log.info(f'Uploading {len(schedules)} events')
        log.debug(f'Uploading {json.dumps(schedules, indent=4)}')
        response = requests.post(f'{adapter_url}/schedule', json=schedules, params={'prune': prune})
        response.raise_for_status()
    else:
        log.info('No events scheduled')


if __name__ == '__main__':
    main()
