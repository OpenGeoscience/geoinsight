import pytest

from uvdat.core.models.project import Dataset


@pytest.mark.django_db
def test_rest_dataset_list_retrieve_unauthenticated(api_client):
    resp = api_client.get('/api/v1/datasets/')
    assert resp.status_code == 401


@pytest.mark.django_db
def test_rest_dataset_list_retrieve(authenticated_api_client, dataset: Dataset):
    resp = authenticated_api_client.get('/api/v1/datasets/')
    assert len(resp.json()['results']) == 1
    assert resp.json()['results'][0]['id'] == dataset.id

    resp = authenticated_api_client.get(f'/api/v1/datasets/{dataset.id}/')
    assert resp.json()['id'] == dataset.id


@pytest.mark.django_db
def test_rest_dataset_layers(
    authenticated_api_client,
    dataset_factory,
    layer_factory,
):
    dataset = dataset_factory()
    layers = [layer_factory(dataset=dataset) for _ in range(3)]

    resp = authenticated_api_client.get(f'/api/v1/datasets/{dataset.id}/layers/')
    assert resp.status_code == 200

    data: list[dict] = resp.json()
    assert len(data) == 3

    # Assert these lists are the same objects
    assert sorted([x['id'] for x in data]) == sorted([x.id for x in layers])


@pytest.mark.django_db
def test_rest_dataset_data_objects(
    authenticated_api_client,
    dataset_factory,
    vector_data_factory,
    raster_data_factory,
):
    dataset = dataset_factory()
    data_objects = [
        *[vector_data_factory(dataset=dataset) for _ in range(3)],
        *[raster_data_factory(dataset=dataset) for _ in range(3)],
    ]

    resp = authenticated_api_client.get(f'/api/v1/datasets/{dataset.id}/data/')
    assert resp.status_code == 200

    data: list[dict] = resp.json()
    assert len(data) == 6

    # Assert these lists are the same objects
    assert sorted([x['id'] for x in data]) == sorted([x.id for x in data_objects])


@pytest.mark.django_db
def test_rest_create_dataset(authenticated_api_client):
    dataset_expected = dict(
        name='My Test Dataset',
        description='created to test dataset uploads',
        category='test',
        metadata=dict(source='pytest'),
    )
    resp = authenticated_api_client.post('/api/v1/datasets/', dataset_expected)
    assert resp.status_code == 201
    serialized_dataset = resp.json()
    for key, value in dataset_expected.items():
        assert serialized_dataset[key] == value
    assert 'id' in serialized_dataset


@pytest.mark.django_db
def test_rest_convert_dataset(file_item, authenticated_api_client, project, user):
    dataset = file_item.dataset
    project.set_collaborators([user])
    project.datasets.set([dataset])

    result_expected = dict(
        name=f'Conversion of Dataset {dataset.name}',
        task_type='conversion',
        inputs=dict(
            dataset_id=dataset.id,
            layer_options=[dict(name='Multiframe Vector Test', frame_property='frame')],
            network_options=None,
            region_options=None,
        ),
        status='Initializing task...',
        outputs=None,
        error=None,
        completed=None,
        project=None,
    )
    resp = authenticated_api_client.post(
        f'/api/v1/datasets/{dataset.id}/convert/', result_expected.get('inputs')
    )
    assert resp.status_code == 200
    serialized_result = resp.json()
    for key, value in result_expected.items():
        assert serialized_result[key] == value
    assert 'id' in serialized_result

    # Check that one Layer was created
    resp = authenticated_api_client.get(f'/api/v1/datasets/{dataset.id}/layers/')
    serialized_layers = resp.json()
    assert len(serialized_layers) == 1
    assert 'id' in serialized_layers[0]
    layer_id = serialized_layers[0]['id']

    # Check that 39 LayerFrames were created
    resp = authenticated_api_client.get(f'/api/v1/layers/{layer_id}/frames/')
    serialized_frames = resp.json()
    assert len(serialized_frames) == 39
