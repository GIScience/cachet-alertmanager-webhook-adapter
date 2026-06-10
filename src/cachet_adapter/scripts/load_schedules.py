import argparse
import json
import logging
from json import JSONDecodeError

import requests
from ics import Calendar

from cachet_adapter.models.api import ScheduledIncident

log = logging.getLogger(__name__)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog='Load Schedules', description='Load a ICS calendar as scheduled maintenance messages'
    )
    parser.add_argument('adapter_url')
    parser.add_argument('--event-title', nargs='*', type=str)
    parser.add_argument(
        '--prune',
        action='store_true',
        dest='prune',
        default=False,
        help='!Attention: danger zone! This will delete any schedule known to the adapter and not specified in the '
        'calendar.'
        'The Cachet will then be in-synch with the file (except manually created schedules).',
    )

    exclusive_group = parser.add_mutually_exclusive_group()
    exclusive_group.add_argument('--file', type=argparse.FileType('r'), dest='file', default='data/schedules.ics')
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
        data = args.file.read()
    calendar = Calendar(data)

    load_schedules(
        calendar=calendar, adapter_url=args.adapter_url, target_event_titles=args.event_title, prune=args.prune
    )


def load_schedules(calendar: Calendar, adapter_url: str, target_event_titles: list[str], prune: bool = False) -> None:
    schedules = list()
    for event in calendar.events:
        if len(target_event_titles) > 0 and event.name not in target_event_titles:
            log.debug(f'Event {event.uid} is skipped.')
            continue

        try:
            components = json.loads(event.description)
        except JSONDecodeError as e:
            log.error(
                f'Event description "{event.description}" for event {event.uid} does not contain a valid '
                'component-set in JSON format.'
                'Creating a scheduled downtime without linked components.',
                exc_info=e,
            )
            components = {}

        schedule_name = event.name or 'Scheduled Downtime'
        scheduled_incident = ScheduledIncident(
            id=event.uid,
            name=schedule_name,
            scheduled_at=event.begin.datetime,
            completed_at=event.end.datetime,
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
