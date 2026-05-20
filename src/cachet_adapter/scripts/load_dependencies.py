import argparse
import csv

import requests

from cachet_adapter.route.component_mapping import COMPONENT_MAPPING_PATH


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog='Load Dependencies', description='Load a CSV file of component dependencies into the Cachet adapter'
    )
    parser.add_argument('adapter_url')
    parser.add_argument(
        '--graph-file', type=argparse.FileType('r'), dest='graph_file', default='data/dependency_graph.csv'
    )
    parser.add_argument(
        '--prune',
        action='store_true',
        dest='prune',
        default=False,
        help='!Attention: danger zone! This will delete any dependencies not specified '
        'in the dependency file. The Cachet Adapter will then be in-synch with the file.',
    )
    args = parser.parse_args()
    return args


def main():
    args = parse_args()
    reader = csv.DictReader(args.graph_file)
    data = list(reader)

    load_dependencies(data=data, prune=args.prune, adapter_url=args.adapter_url)


def load_dependencies(
    data: list[dict[str, str]],
    adapter_url: str,
    prune: bool = False,
) -> None:
    response = requests.post(f'{adapter_url}/{COMPONENT_MAPPING_PATH}', json=data, params={'prune': prune})
    response.raise_for_status()


if __name__ == '__main__':
    main()
