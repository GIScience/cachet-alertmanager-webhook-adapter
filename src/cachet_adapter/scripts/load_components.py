import argparse
import json
import logging
from typing import Optional

from cachet_adapter.models.cachet import BaseComponent, CachetGroupAttributes
from cachet_adapter.models.scripts import ComponentData
from cachet_adapter.settings import AdapterSettings
from cachet_adapter.utils.cachet_api import CachetApi

log = logging.getLogger(__name__)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog='Load Components', description='Load a JSON file of groups and componentes into Cachet'
    )
    parser.add_argument('--component-file', dest='component_file', default='data/components.json')
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

    available_groups, available_components = get_lookup_dicts(api=api)

    for group_name, components in data.root.items():
        group_id = handle_group(api=api, available_groups=available_groups, group_name=group_name)

        group_component_id_list = list()
        for component in components:
            component_id = handle_component(
                api=api, available_components=available_components, group_id=group_id, component=component
            )
            group_component_id_list.append(component_id)

        result[group_id] = group_component_id_list

    if prune:
        prune_data(api=api, remaingin_groups=available_groups, remaining_components=available_components)
    elif len(available_groups) > 0 or len(available_components) > 0:
        log.warning(
            f'The groups {available_groups} ({{group-name:id}}) and the components {available_components} '
            'are not specified in the input data but are present on the server.'
        )

    return result


def group_qualified_component_name(group_id: Optional[int], component_name: str) -> str:
    return f'{group_id}.{component_name}'


def get_lookup_dicts(api: CachetApi) -> tuple[dict[str, int], dict[str, int]]:
    available_groups = dict()
    for group in api.list_groups():
        available_groups[group.attributes.name] = group.id

    available_components = dict()
    for component in api.list_components().data:
        component_name = component.attributes.name
        group_id = component.relationships.group.data.id if component.relationships.group.data else None
        component_key = group_qualified_component_name(group_id=group_id, component_name=component_name)
        available_components[component_key] = component.id

    return available_groups, available_components


def handle_group(api: CachetApi, available_groups: dict[str, int], group_name: str) -> int:
    if group_name in available_groups.keys():
        group_id = available_groups.pop(group_name)
    else:
        group = CachetGroupAttributes(name=group_name)
        group_id = api.create_group(group=group)
    return group_id


def handle_component(
    api: CachetApi, available_components: dict[str, int], group_id: int, component: BaseComponent
) -> int:
    component_key = group_qualified_component_name(group_id=group_id, component_name=component.name)
    if component_key in available_components.keys():
        component_id = available_components.pop(component_key)
        api.update_component(group_id=group_id, component_id=component_id, component=component)
    else:
        component_id = api.create_component(group_id=group_id, component=component)
    return component_id


def prune_data(api: CachetApi, remaingin_groups: dict[str, int], remaining_components: dict[str, int]) -> None:
    for group_id in remaingin_groups.values():
        api.delete_group(group_id=group_id)
    for component_id in remaining_components.values():
        api.delete_component(component_id=component_id)


def main() -> None:
    args = parse_args()
    with open(args.component_file, 'r') as f:
        raw_data = json.load(f)
    component_data = ComponentData(raw_data)

    # Reading settings from .env file
    # noinspection argument-list
    settings = AdapterSettings()
    api = CachetApi(base_url=str(settings.cachet_api_url), token=settings.cachet_token)

    load_components(api=api, data=component_data, prune=args.prune)


if __name__ == '__main__':
    main()
