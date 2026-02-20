from __future__ import annotations

import json

from django.contrib.gis.geos import GEOSGeometry

from geoinsight.core.models import VectorData, VectorFeature


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
    print("\t\t", f"{len(created)} vector features created.")

    return created
