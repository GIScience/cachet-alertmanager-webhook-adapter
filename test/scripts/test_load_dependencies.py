import csv

from responses import matchers

from cachet_adapter.scripts.load_dependencies import load_dependencies
from test.conftest import TEST_RESOURCES


def test_load_dependencies(responses):
    responses.post(
        'http://test-adapter/adapter/component-mapping',
        match=[
            matchers.json_params_matcher(
                [
                    {
                        'from_component': 'a',
                        'to_component': 'b',
                        'relationship': 'requires',
                        'from_group': '',
                        'to_group': '',
                    }
                ]
            )
        ],
    )

    with open(TEST_RESOURCES / 'dependency_graph.csv', 'r') as f:
        reader = csv.DictReader(f)
        data = list(reader)

    load_dependencies(
        data=data,
        adapter_url='http://test-adapter/adapter',
    )
