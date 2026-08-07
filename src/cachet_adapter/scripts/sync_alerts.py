import argparse
import json
import logging

import requests

from cachet_adapter.utils.alertmanager_api import AlertmanagerApi

log = logging.getLogger(__name__)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog='Synchronise Alerts',
        description='Make sure the alerts in the Alertmanager and the ones in CAWA are in synch',
    )
    parser.add_argument('adapter_url')
    parser.add_argument('--alertmanager-url', dest='alertmanager_url', required=True)
    parser.add_argument('--alertmanager-user', dest='alertmanager_user')
    parser.add_argument('--alertmanager-pass', dest='alertmanager_pass')
    parser.add_argument(
        '--prune',
        action='store_true',
        dest='prune',
        default=False,
        help='This will mark any Cachet incident linked to a resolved alert (i.e. not present in the Alertmanager API) '
        'as fixed (except manually created incidents).'
        'The Cachet will then be in-synch with the Alertmanager.',
    )
    args = parser.parse_args()
    return args


def main():
    args = parse_args()
    alertmanager = AlertmanagerApi(
        base_url=args.alertmanager_url, username=args.alertmanager_user, password=args.alertmanager_pass
    )
    sync_alerts(alertmanager_api=alertmanager, adapter_url=args.adapter_url, prune=args.prune)


def sync_alerts(
    alertmanager_api: AlertmanagerApi,
    adapter_url: str,
    prune: bool = False,
) -> None:
    alerts = alertmanager_api.get_alerts()

    log.info(f'Synching {len(alerts)} alerts')
    log.debug(f'Synching {json.dumps(alerts, indent=4)}')
    response = requests.post(f'{adapter_url}/adapt', json=alerts, params={'prune': prune})
    response.raise_for_status()


if __name__ == '__main__':
    main()
