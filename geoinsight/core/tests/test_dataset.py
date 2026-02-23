from __future__ import annotations

from typing import TYPE_CHECKING

from django.core.files.base import File
import pytest

if TYPE_CHECKING:
    from geoinsight.core.models.project import Dataset


@pytest.mark.django_db
def test_rest_dataset_list_retrieve_unauthenticated(api_client):
    resp = api_client.get("/api/v1/datasets/")
    assert resp.status_code == 401


@pytest.mark.django_db
def test_rest_dataset_list_retrieve(authenticated_api_client, dataset: Dataset):
    resp = authenticated_api_client.get("/api/v1/datasets/")
    assert len(resp.json()["results"]) == 1
    assert resp.json()["results"][0]["id"] == dataset.id

    resp = authenticated_api_client.get(f"/api/v1/datasets/{dataset.id}/")
    assert resp.json()["id"] == dataset.id


@pytest.mark.django_db
def test_rest_dataset_layers(
    authenticated_api_client,
    dataset_factory,
    layer_factory,
):
    dataset = dataset_factory()
    layers = [layer_factory(dataset=dataset) for _ in range(3)]

    resp = authenticated_api_client.get(f"/api/v1/datasets/{dataset.id}/layers/")
    assert resp.status_code == 200

    data: list[dict] = resp.json()
    assert len(data) == 3

    # Assert these lists are the same objects
    assert sorted([x["id"] for x in data]) == sorted([x.id for x in layers])


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

    resp = authenticated_api_client.get(f"/api/v1/datasets/{dataset.id}/data/")
    assert resp.status_code == 200

    data: list[dict] = resp.json()
    assert len(data) == 6

    # Assert these lists are the same objects
    assert sorted([x["id"] for x in data]) == sorted([x.id for x in data_objects])


@pytest.mark.django_db
def test_rest_create_dataset(authenticated_api_client, user):
    dataset_expected = {
        "name": "My Test Dataset",
        "description": "created to test dataset uploads",
        "category": "test",
        "tags": ["boston", "flood", "simulation"],
        "metadata": {"source": "pytest"},
    }
    resp = authenticated_api_client.post("/api/v1/datasets/", dataset_expected)
    assert resp.status_code == 201
    serialized_dataset = resp.json()
    for key, value in dataset_expected.items():
        assert serialized_dataset[key] == value
    assert "id" in serialized_dataset
    assert serialized_dataset["owner"]["id"] == user.id


@pytest.mark.django_db
def test_rest_convert_dataset(
    file_item_factory, multiframe_vector_file, authenticated_api_client, project, user
):
    with multiframe_vector_file["path"].open("rb") as f:
        file_item = file_item_factory(
            file=File(f),
            name=multiframe_vector_file["name"],
            file_type=multiframe_vector_file["file_type"],
        )
    dataset = file_item.dataset
    project.set_collaborators([user])
    project.datasets.set([dataset])

    result_expected = {
        "task_type": "conversion",
        "inputs": {
            "dataset_id": dataset.id,
            "layer_options": [{"name": "Multiframe Vector Test", "frame_property": "frame"}],
            "network_options": None,
            "region_options": None,
        },
        "status": "Initializing task...",
        "outputs": None,
        "error": None,
        "completed": None,
        "project": None,
    }
    resp = authenticated_api_client.post(
        f"/api/v1/datasets/{dataset.id}/convert/", result_expected.get("inputs")
    )
    assert resp.status_code == 200
    serialized_result = resp.json()
    for key, value in result_expected.items():
        assert serialized_result[key] == value
    assert "id" in serialized_result

    # Check that one Layer was created
    resp = authenticated_api_client.get(f"/api/v1/datasets/{dataset.id}/layers/")
    serialized_layers = resp.json()
    assert len(serialized_layers) == 1
    assert "id" in serialized_layers[0]
    layer_id = serialized_layers[0]["id"]

    # Check that 39 LayerFrames were created
    resp = authenticated_api_client.get(f"/api/v1/layers/{layer_id}/frames/")
    serialized_frames = resp.json()
    assert len(serialized_frames) == 39


@pytest.mark.django_db
def test_dataset_set_owner(dataset, user):
    owner = dataset.owner()
    assert owner.id != user.id

    dataset.set_owner(user)
    assert dataset.owner().id == user.id


@pytest.mark.django_db
def test_rest_dataset_edit(authenticated_api_client, user, dataset: Dataset):
    patch = {"name": "New Name"}
    resp = authenticated_api_client.patch(f"/api/v1/datasets/{dataset.id}/", patch)
    assert resp.status_code == 403

    dataset.set_owner(user)
    resp = authenticated_api_client.patch(f"/api/v1/datasets/{dataset.id}/", patch)
    assert resp.status_code == 200

    dataset.refresh_from_db()
    assert dataset.name == patch["name"]


@pytest.mark.django_db
def test_rest_dataset_delete(authenticated_api_client, user, dataset: Dataset):
    resp = authenticated_api_client.delete(f"/api/v1/datasets/{dataset.id}/")
    assert resp.status_code == 403

    dataset.set_owner(user)
    resp = authenticated_api_client.delete(f"/api/v1/datasets/{dataset.id}/")
    assert resp.status_code == 204


@pytest.mark.django_db
def test_rest_dataset_invalid_tags(authenticated_api_client):
    dataset_expected = {
        "name": "My Test Dataset",
        "description": "created to test dataset uploads",
        "category": "test",
        "tags": "invalid",
        "metadata": {"source": "pytest"},
    }
    resp = authenticated_api_client.post("/api/v1/datasets/", dataset_expected)
    assert resp.status_code == 400
    assert resp.json() == {"tags": ["Dataset tags must be expressed as a list of strings."]}
