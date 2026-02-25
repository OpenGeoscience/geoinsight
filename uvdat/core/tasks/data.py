from __future__ import annotations

import json
import logging

from django.contrib.gis.geos import GEOSGeometry

from uvdat.core.models import VectorData, VectorFeature

logger = logging.getLogger(__name__)


def create_vector_features(vector_data: VectorData):
    features = vector_data.read_geojson_data()["features"]
    vector_features = [
        VectorFeature(
            vector_data=vector_data,
            geometry=GEOSGeometry(json.dumps(feature["geometry"])),
            properties=feature["properties"],
        )
        for feature in features
    ]

    created = VectorFeature.objects.bulk_create(vector_features)
    logger.info("%d vector features created.", len(created))

    return created
