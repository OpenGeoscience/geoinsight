from __future__ import annotations

import secrets

from django.contrib.gis.geos import GEOSGeometry
import geopandas

from geoinsight.core.models import Region, VectorFeature


def create_source_regions(vector_data, region_options):
    # Overwrite previous results
    dataset = vector_data.dataset
    Region.objects.filter(dataset=dataset).delete()

    name_property = region_options.get("name_property")
    geodata = vector_data.read_geojson_data()

    region_count = 0
    new_feature_set = []
    for feature in geodata["features"]:
        properties = feature["properties"]
        geometry = feature["geometry"]

        # Ensure a name field
        name = secrets.token_hex(10)
        if name_property and name_property in properties:
            name = properties[name_property]

        # Convert Polygon to MultiPolygon if necessary
        if geometry["type"] == "Polygon":
            geometry["type"] = "MultiPolygon"
            geometry["coordinates"] = [geometry["coordinates"]]

        # Create region with properties and MultiPolygon
        region = Region.objects.create(
            name=name,
            boundary=GEOSGeometry(str(geometry)),
            metadata=properties,
            dataset=dataset,
        )
        region.vector_feature = VectorFeature.objects.create(
            vector_data=vector_data,
            geometry=region.boundary,
            properties=region.metadata,
        )
        region.save()
        region_count += 1

        properties["region_id"] = region.id
        properties["region_name"] = region.name
        properties["dataset_id"] = region.dataset.id
        new_feature_set.append(
            {
                "id": region.id,
                "type": "Feature",
                "geometry": geometry,
                "properties": properties,
            }
        )

    # Save updated features to layer
    new_geodata = geopandas.GeoDataFrame.from_features(new_feature_set).set_crs(3857)
    new_geodata.to_crs(4326)
    vector_data.write_geojson_data(new_geodata.to_json())
    vector_data.save()
    print("\t\t", f"{region_count} regions created.")

    all_features = VectorFeature.objects.filter(vector_data=vector_data)
    print("\t\t", f"{all_features.count()} vector features created.")
