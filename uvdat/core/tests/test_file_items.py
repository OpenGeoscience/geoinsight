from __future__ import annotations

from typing import Callable

from django.core.files.base import File
import pytest


@pytest.mark.django_db
def test_upload_and_create_file_item(
    multiframe_vector_file,
    dataset,
    authenticated_api_client,
    s3ff_field_value_factory: Callable[[File[bytes]], str],
):
    with open(multiframe_vector_file['path'], 'rb') as f:
        s3ff_value = s3ff_field_value_factory(File(file=f, name=multiframe_vector_file['name']))

    fileitem_expected = dict(
        name='multiframe_vector.geojson',
        file=s3ff_value,
        file_type='geojson',
        dataset=dataset.id,
        metadata=dict(
            source='pytest',
        ),
    )
    resp = authenticated_api_client.post('/api/v1/files/', fileitem_expected)
    assert resp.status_code == 201
    serialized_fileitem = resp.json()
    for key, value in fileitem_expected.items():
        if key == 'file':
            assert ':9000/test-django-storage' in serialized_fileitem[key]
        else:
            assert serialized_fileitem[key] == value
    assert 'id' in serialized_fileitem
