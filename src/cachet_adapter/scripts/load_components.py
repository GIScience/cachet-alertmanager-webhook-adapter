import argparse
import json

from cachet_adapter.models.cachet import CachetGroupAttributes
from cachet_adapter.models.scripts import ComponentData
from cachet_adapter.settings import AdapterSettings
from cachet_adapter.utils.cachetapi import CachetApi


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog='Load Components', description='Load a JSON file of groups and componentes into Cachet'
    )
    parser.add_argument(
        '--component-file', type=argparse.FileType('r'), dest='component_file', default='data/components.json'
    )
    args = parser.parse_args()
    return args


def load_components(api: CachetApi, data: ComponentData) -> dict[int, list[int]]:
    result = dict()
    available_groups = dict()
    available_components = set()
    for group in api.list_groups():
        available_groups[group.attributes.name] = group.id
        if group.relationships:
            for component in group.relationships.components.data:
                available_components.add(component.id)

    for group_name, components in data.root.items():
        if group_name not in available_groups.keys():
            group = CachetGroupAttributes(name=group_name)
            group_id = api.create_group(group=group)
        else:
            group_id = available_groups.pop(group_name)

        group_component_id_list = list()
        for component in components:
            component_id = api.get_component_id(component_group=group_name, component_name=component.name)
            if component_id is None:
                component_id = api.create_component(component=component, group_id=group_id)
            else:
                available_components.remove(component_id)
            group_component_id_list.append(component_id)
        result[group_id] = group_component_id_list
    return result


def main() -> None:
    args = parse_args()
    raw_data = json.load(args.component_file)
    component_data = ComponentData(raw_data)

    settings = AdapterSettings()
    api = CachetApi(base_url=settings.cachet_api_url, token=settings.cachet_token)

    load_components(api=api, data=component_data)


if __name__ == '__main__':
    main()
