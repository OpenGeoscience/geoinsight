from __future__ import annotations

from django.contrib.auth.models import User
from django.core.management import call_command
import pytest

from uvdat.core.models import (
    Chart,
    Dataset,
    FileItem,
    Layer,
    LayerFrame,
    Network,
    NetworkEdge,
    NetworkNode,
    Project,
    RasterData,
    Region,
    VectorData,
    VectorFeature,
)


@pytest.mark.slow
@pytest.mark.django_db
def test_ingest():
    # ensure a superuser exists
    User.objects.create_superuser("testsuper")

    call_command(
        "ingest",
        "./tests/ingest.json",
    )

    assert Chart.objects.all().count() == 1
    assert Project.objects.all().count() == 1
    assert Dataset.objects.all().count() == 4
    assert FileItem.objects.all().count() == 5
    assert Layer.objects.all().count() == 4
    assert LayerFrame.objects.all().count() == 42
    assert Network.objects.all().count() == 1
    assert NetworkEdge.objects.all().count() == 164
    assert NetworkNode.objects.all().count() == 158
    assert RasterData.objects.all().count() == 1
    assert Region.objects.all().count() == 24
    assert VectorData.objects.all().count() == 3
    assert VectorFeature.objects.count() == 1306
