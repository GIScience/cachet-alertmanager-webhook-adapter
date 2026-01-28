from sqlmodel import Session

from cachet_adapter.models.database import ComponentGraph, ComponentRelationship


def test_get_mapping_all(mocked_client, load_component_triangle):
    response = mocked_client.get('/component-mapping')
    assert response.status_code == 200
    assert response.json() == [
        {
            'from_group': '',
            'from_component': 'a',
            'to_group': '',
            'to_component': 'b',
            'relationship': 'requires',
        },
        {
            'from_group': '',
            'from_component': 'b',
            'to_group': '',
            'to_component': 'c',
            'relationship': 'optional',
        },
        {
            'from_group': '',
            'from_component': 'a',
            'to_group': '',
            'to_component': 'c',
            'relationship': 'requires',
        },
    ]


def test_get_mapping_group(mocked_client, database, load_component_chain):
    d_to_c = ComponentGraph(
        from_group='special',
        from_component='d',
        to_component='c',
        relationship=ComponentRelationship.REQUIRES,
    )

    with Session(database) as session:
        session.add(d_to_c)
        session.commit()

    response = mocked_client.get('/component-mapping', params={'group': 'special'})
    assert response.status_code == 200
    assert response.json() == [
        {
            'from_group': 'special',
            'from_component': 'd',
            'to_group': '',
            'to_component': 'c',
            'relationship': 'requires',
        }
    ]


def test_get_mapping_one(mocked_client, load_component_triangle):
    response = mocked_client.get('/component-mapping', params={'component': 'a'})
    assert response.status_code == 200
    assert response.json() == [
        {
            'from_group': '',
            'from_component': 'a',
            'to_group': '',
            'to_component': 'b',
            'relationship': 'requires',
        },
        {
            'from_group': '',
            'from_component': 'a',
            'to_group': '',
            'to_component': 'c',
            'relationship': 'requires',
        },
    ]


def test_get_recursive_dependencies(mocked_client, load_component_chain):
    response = mocked_client.get(
        '/component-mapping',
        params={'component': 'a', 'recursive': True},
    )
    assert response.status_code == 200
    assert response.json() == [
        {
            'from_group': '',
            'from_component': 'a',
            'to_group': '',
            'to_component': 'b',
            'relationship': 'requires',
        },
        {
            'from_group': '',
            'from_component': 'a',
            'to_group': '',
            'to_component': 'c',
            'relationship': 'optional',
            'transitive': True,
        },
    ]


def test_get_recursive_dependencies_fails_for_missing_info(mocked_client, load_component_chain):
    response = mocked_client.get(
        '/component-mapping',
        params={'from_group': 'a', 'recursive': True},
    )
    assert response.status_code == 400
    assert (
        'recursive listing is only available for exact component definitions (group + component).'
        in response.json()['detail'].lower()
    )


def test_get_recursive_dependencies_with_direct_route(mocked_client, load_component_triangle):
    response = mocked_client.get(
        '/component-mapping',
        params={'component': 'a', 'recursive': True},
    )
    assert response.status_code == 200
    assert response.json() == [
        {
            'from_group': '',
            'from_component': 'a',
            'to_group': '',
            'to_component': 'b',
            'relationship': 'requires',
        },
        {
            'from_group': '',
            'from_component': 'a',
            'to_group': '',
            'to_component': 'c',
            'relationship': 'requires',
        },
        {
            'from_group': '',
            'from_component': 'a',
            'to_group': '',
            'to_component': 'c',
            'relationship': 'optional',
            'transitive': True,
        },
    ]


def test_get_recursive_dependencies_with_required_after_optional(mocked_client, load_component_chain, database):
    c_to_d = ComponentGraph(
        from_component='c',
        to_component='d',
        relationship=ComponentRelationship.REQUIRES,
    )
    with Session(database) as session:
        session.add(c_to_d)
        session.commit()

    response = mocked_client.get(
        '/component-mapping',
        params={'component': 'a', 'recursive': True},
    )
    assert response.status_code == 200
    assert response.json() == [
        {
            'from_group': '',
            'from_component': 'a',
            'to_group': '',
            'to_component': 'b',
            'relationship': 'requires',
        },
        {
            'from_group': '',
            'from_component': 'a',
            'to_group': '',
            'to_component': 'c',
            'relationship': 'optional',
            'transitive': True,
        },
        {
            'from_group': '',
            'from_component': 'a',
            'to_group': '',
            'to_component': 'd',
            'relationship': 'optional',
            'transitive': True,
        },
    ]


def test_get_recursive_dependencies_with_required_after_optional_upward(mocked_client, load_component_chain, database):
    c_to_d = ComponentGraph(
        from_component='c',
        to_component='d',
        relationship=ComponentRelationship.REQUIRES,
    )
    with Session(database) as session:
        session.add(c_to_d)
        session.commit()

    response = mocked_client.get(
        '/component-mapping',
        params={
            'component': 'd',
            'recursive': True,
            'upward': True,
        },
    )
    assert response.status_code == 200
    assert response.json() == [
        {
            'from_group': '',
            'from_component': 'c',
            'to_group': '',
            'to_component': 'd',
            'relationship': 'requires',
        },
        {
            'from_group': '',
            'from_component': 'b',
            'to_group': '',
            'to_component': 'd',
            'relationship': 'optional',
            'transitive': True,
        },
        {
            'from_group': '',
            'from_component': 'a',
            'to_group': '',
            'to_component': 'd',
            'relationship': 'optional',
            'transitive': True,
        },
    ]


def test_get_reverse_dependencies(mocked_client, load_component_chain):
    response = mocked_client.get(
        '/component-mapping',
        params={'component': 'b', 'upward': True},
    )
    assert response.status_code == 200
    assert response.json() == [
        {
            'from_group': '',
            'from_component': 'a',
            'to_group': '',
            'to_component': 'b',
            'relationship': 'requires',
        },
    ]


def test_get_reverse_dependencies_recursive(mocked_client, load_component_chain):
    response = mocked_client.get(
        '/component-mapping',
        params={
            'component': 'c',
            'upward': True,
            'recursive': True,
        },
    )
    assert response.status_code == 200
    assert response.json() == [
        {
            'from_group': '',
            'from_component': 'b',
            'to_group': '',
            'to_component': 'c',
            'relationship': 'optional',
        },
        {
            'from_group': '',
            'from_component': 'a',
            'to_group': '',
            'to_component': 'c',
            'relationship': 'optional',
            'transitive': True,
        },
    ]


def test_put_mapping_new(mocked_client):
    response = mocked_client.put(
        '/component-mapping',
        json={
            'from_component': 'a',
            'to_component': 'd',
            'relationship': 'requires',
        },
    )

    assert response.status_code == 201
    expected_response = [
        {
            'from_group': '',
            'from_component': 'a',
            'to_group': '',
            'to_component': 'd',
            'relationship': 'requires',
        },
    ]
    assert response.json() == expected_response

    response = mocked_client.get('/component-mapping', params={'from_component': 'a'})
    assert response.json() == expected_response


def test_put_mapping_new_with_group(mocked_client):
    response = mocked_client.put(
        '/component-mapping',
        json={
            'from_group': 'group 1',
            'from_component': 'a',
            'to_group': 'group 2',
            'to_component': 'd',
            'relationship': 'requires',
        },
    )

    assert response.status_code == 201
    expected_response = [
        {
            'from_group': 'group 1',
            'from_component': 'a',
            'to_group': 'group 2',
            'to_component': 'd',
            'relationship': 'requires',
        },
    ]
    assert response.json() == expected_response

    response = mocked_client.get('/component-mapping', params={'from_group': 'group 1', 'from_component': 'a'})
    assert response.json() == expected_response


def test_put_mapping_changed(mocked_client, load_component_chain):
    response = mocked_client.put(
        '/component-mapping',
        json={
            'from_component': 'b',
            'to_component': 'c',
            'relationship': 'requires',
        },
    )

    assert response.status_code == 201
    assert response.json() == [
        {
            'from_group': '',
            'from_component': 'b',
            'to_group': '',
            'to_component': 'c',
            'relationship': 'requires',
        }
    ]


def test_delete_existing_mapping(mocked_client, load_component_triangle):
    response = mocked_client.delete(
        '/component-mapping',
        params={
            'from_group': '',
            'from_component': 'a',
            'to_group': '',
            'to_component': 'b',
        },
    )
    assert response.status_code == 200
    assert response.json() == [
        {
            'from_group': '',
            'from_component': 'a',
            'to_group': '',
            'to_component': 'c',
            'relationship': 'requires',
        }
    ]


def test_delete_inexistent_mapping(mocked_client):
    response = mocked_client.delete(
        '/component-mapping',
        params={
            'from_group': '',
            'from_component': 'e',
            'to_group': '',
            'to_component': 'f',
        },
    )

    assert response.status_code == 200
    assert response.json() == []


def test_prevent_circular_dependency(mocked_client, load_component_chain):
    # Directly circular
    response = mocked_client.put(
        '/component-mapping',
        json={
            'from_component': 'b',
            'to_component': 'a',
            'relationship': 'requires',
        },
    )
    assert response.status_code == 400
    assert 'circular' in response.json()['detail'].lower()

    # Transitive circular
    response = mocked_client.put(
        '/component-mapping',
        json={
            'from_component': 'c',
            'to_component': 'a',
            'relationship': 'requires',
        },
    )
    assert response.status_code == 400
    assert 'circular' in response.json()['detail'].lower()
