import argparse
import json
import logging
from datetime import datetime, timedelta
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
    parser.add_argument('--event-titles', nargs='*', type=str, default=[])
    parser.add_argument(
        '--prune',
        action='store_true',
        dest='prune',
        default=False,
        help='!Attention: danger zone! This will delete any schedule known to the adapter and not specified in the '
        'calendar.'
        'The Cachet will then be in-synch with the file (except manually created schedules).',
    )
    parser.add_argument('--link-all-components-keyword', type=str, default='[cachet:all]')

    exclusive_group = parser.add_mutually_exclusive_group()
    exclusive_group.add_argument('--file', dest='file', default='data/schedules.ics')
    exclusive_group.add_argument('--url', dest='url', required=False)

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
    events = recurring_ical_events.of(calendar)._occurrences_between(
        datetime.now() - calendar_monitoring_time_range, datetime.now() + calendar_monitoring_time_range
    )

    schedules = list()
    for event in events:
        parent_event = event.as_component(keep_recurrence_attributes=True)

        schedule_id = event.id.to_string()
        schedule_name = parent_event.summary or 'Scheduled Downtime'
        schedule_description = parent_event.description or ''

        if len(target_event_titles) > 0 and parent_event.summary not in target_event_titles:
            log.debug(f'Event {event.id} is skipped.')
            continue

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
        response = requests.post(f'{adapter_url}/schedule', json=schedules, params={'prune': prune})
        response.raise_for_status()
    else:
        log.info('No events scheduled')


if __name__ == '__main__':
    main()
