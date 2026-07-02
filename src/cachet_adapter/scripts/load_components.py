import argparse
import json
import logging

from cachet_adapter.models.cachet import CachetGroupAttributes
from cachet_adapter.models.scripts import ComponentData
from cachet_adapter.settings import AdapterSettings
from cachet_adapter.utils.cachet_api import CachetApi

log = logging.getLogger(__name__)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog='Load Components', description='Load a JSON file of groups and componentes into Cachet'
    )
    parser.add_argument(
        '--component-file', type=argparse.FileType('r'), dest='component_file', default='data/components.json'
    )
    parser.add_argument(
        '--prune',
        action='store_true',
        dest='prune',
        default=False,
        help='!Attention: danger zone!'
        'This will delete any groups and components not specified in the component file. '
        'Cachet will then be in-sync with the components file. '
        'Note that renaming a group or component is treated as a deletion + re-creation, thereby losing existing '
        'linked incidents. '
        'Therefore, please manually rename groups and components in the Cachet UI to circumvent the problem!',
    )
    args = parser.parse_args()
    return args


def load_components(api: CachetApi, data: ComponentData, prune: bool = False) -> dict[int, list[int]]:
    result = dict()

    available_groups = dict()
    available_components = dict()
    for group in api.list_groups():
        available_groups[group.attributes.name] = group.id
    for component in api.list_components().data:
        available_components[component.attributes.name] = {
            'id': component.id,
            'group_id': component.relationships.group.data.id if component.relationships.group.data else None,
        }

    for group_name, components in data.root.items():
        group_exists = group_name in available_groups.keys()
        if not group_exists:
            group = CachetGroupAttributes(name=group_name)
            group_id = api.create_group(group=group)
        else:
            group_id = available_groups.pop(group_name)

        group_component_id_list = list()
        for component in components:
            component_exists = (
                component.name in available_components.keys()
                and available_components[component.name]['group_id'] == group_id
            )
            if not component_exists:
                component_id = api.create_component(component=component, group_id=group_id)
            else:
                component_id = available_components.pop(component.name)['id']
            group_component_id_list.append(component_id)

        result[group_id] = group_component_id_list

    if prune:
        for group_id in available_groups.values():
            api.delete_group(group_id=group_id)
        for component in available_components.values():
            api.delete_component(component_id=component['id'])
    elif len(available_groups) > 0 or len(available_components) > 0:
        log.warning(
            f'The groups {available_groups} ({{group-name:id}}) and the components {available_components} '
            'are not specified in the input data but are present on the server.'
        )

    return result


def main() -> None:
    args = parse_args()
    raw_data = json.load(args.component_file)
    component_data = ComponentData(raw_data)

    settings = AdapterSettings()
    api = CachetApi(base_url=settings.cachet_api_url, token=settings.cachet_token)

    load_components(api=api, data=component_data, prune=args.prune)


if __name__ == '__main__':
    main()
