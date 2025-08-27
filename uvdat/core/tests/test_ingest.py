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
    User.objects.create_superuser('testsuper')

    # smaller subset for faster evaluation
    # 0 is MBTA Rapid Transit, tests network eval
    # 4 is Massachusetts Elevation Data, tests raster eval
    # 6 is Boston Neighborhoods, tests regions eval
    # 9 is Boston Projected Flood Events, tests multilayer/multiframe dataset eval

    call_command(
        'ingest',
        './tests/ingest.json',
    )

    assert Chart.objects.all().count() == 3
    assert Project.objects.all().count() == 2
    assert Dataset.objects.all().count() == 4
    assert FileItem.objects.all().count() == 15
    assert Layer.objects.all().count() == 6
    assert LayerFrame.objects.all().count() == 12
    assert Network.objects.all().count() == 1
    assert NetworkEdge.objects.all().count() == 164
    assert NetworkNode.objects.all().count() == 158
    assert RasterData.objects.all().count() == 1
    assert Region.objects.all().count() == 24
    assert VectorData.objects.all().count() == 11
    assert VectorFeature.objects.count() == 357
