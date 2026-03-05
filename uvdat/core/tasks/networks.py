from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING

from django.contrib.gis.geos import LineString, Point
import geopandas
import shapely

if TYPE_CHECKING:
    import pandas as pd

from uvdat.core.models import Network, NetworkEdge, NetworkNode, VectorData, VectorFeature

logger = logging.getLogger(__name__)


def _get_or_create_node(
    network: Network,
    vector_data: VectorData,
    node_name: str,
    coordinates: shapely.Point,
    row_data: pd.Series,
) -> NetworkNode:
    try:
        node = NetworkNode.objects.get(network=network, name=node_name)
    except NetworkNode.DoesNotExist:
        node = NetworkNode.objects.create(
            network=network,
            name=node_name,
            location=Point(coordinates.x, coordinates.y),
            metadata={
                k: v
                for k, v in row_data.to_dict().items()
                if k not in ["index", "geometry", "index_right", "distance"]
                and str(v).lower() != "nan"
            },
        )
    if node.vector_feature is None:
        node.vector_feature = VectorFeature.objects.create(
            vector_data=vector_data,
            geometry=node.location,
            properties=node.metadata | {"node_id": node.id},
        )
        node.save()
    return node


def create_network(vector_data, network_options):
    # Overwrite previous results
    dataset = vector_data.dataset
    Network.objects.filter(vector_data=vector_data).delete()
    network = Network.objects.create(
        name=(
            f"{dataset.name} Network"
            f" {Network.objects.filter(vector_data__dataset=dataset).count() + 1}"
        ),
        category=dataset.category,
        vector_data=vector_data,
        metadata={"source": "Parsed from GeoJSON."},
    )

    connection_column = network_options.get("connection_column")
    connection_column_delimiter = network_options.get("connection_column_delimiter")
    node_id_column = network_options.get("node_id_column")

    geodata = geopandas.GeoDataFrame.from_features(
        vector_data.read_geojson_data().get("features")
    ).set_crs(4326)
    geodata = geodata.fillna({"connection_column": ""})
    edge_set = geodata[geodata.geom_type != "Point"]
    node_set = geodata[geodata.geom_type == "Point"]

    unique_routes = node_set[connection_column].drop_duplicates()
    unique_routes = unique_routes[~unique_routes.str.contains(connection_column_delimiter)]
    for unique_route in unique_routes:
        nodes = node_set[node_set[connection_column].str.contains(unique_route, regex=False)]
        edges = edge_set[edge_set[connection_column].str.contains(unique_route, regex=False)]

        # create one route line from all edges in this group
        if len(edges) < 1:
            continue
        route = edges.union_all("unary")
        if route.geom_type == "MultiLineString":
            route = shapely.ops.linemerge(route)
        route = shapely.extract_unique_points(route.segmentize(10))
        route_points = geopandas.GeoDataFrame(geometry=list(route.geoms)).set_crs(node_set.crs)

        # convert both nodes and route to a projected crs
        # for better accuracy of the sjoin_nearest function to follow
        nodes_reprojected = nodes.copy().to_crs(3857)
        route_points_reprojected = route_points.copy().to_crs(3857)

        # along the points of the route, find the nodes that are nearest
        # (in order of the route points)
        route_points_nearest_nodes = route_points_reprojected.sjoin_nearest(
            nodes_reprojected, distance_col="distance"
        )

        # find cutoff points where one edge geometry stops and another begins
        cutoff_points = {
            nearest_node: point_group.sort_values(by=["distance"]).iloc[0]["geometry"]
            for nearest_node, point_group in route_points_nearest_nodes.groupby(node_id_column)
        }

        # use ordered node names to create NetworkNode objects
        # and cutoff points to create NetworkEdge objects
        route_nodes = route_points_nearest_nodes.drop_duplicates(
            subset=[node_id_column]
        ).reset_index()
        for i, current_node in route_nodes.iterrows():
            current_node_name = current_node[node_id_column]
            # refer back to node_set for coords with original projection
            current_node_coordinates = node_set.loc[
                node_set[node_id_column] == current_node_name
            ].iloc[0]["geometry"]

            from_node_obj = _get_or_create_node(
                network, vector_data, current_node_name, current_node_coordinates, current_node
            )

            if i < len(route_nodes) - 1:
                next_node = route_nodes.iloc[i + 1]
                next_node_name = next_node[node_id_column]
                # refer back to node_set for coords with original projection
                next_node_coordinates = node_set.loc[
                    node_set[node_id_column] == next_node_name
                ].iloc[0]["geometry"]

                to_node_obj = _get_or_create_node(
                    network, vector_data, next_node_name, next_node_coordinates, next_node
                )

                route_points_start_index = route_points_reprojected.index[
                    route_points_reprojected["geometry"] == cutoff_points[current_node_name]
                ][0]
                route_points_end_index = route_points_reprojected.index[
                    route_points_reprojected["geometry"] == cutoff_points[next_node_name]
                ][0]

                edge_points = route_points[  # use original projection
                    route_points_start_index : route_points_end_index
                    + 1  # +1 to include end
                ]
                edge_line_geometry = LineString(*[Point(p.x, p.y) for p in edge_points["geometry"]])

                try:
                    edge = NetworkEdge.objects.get(
                        network=network,
                        name=f"{current_node_name} - {next_node_name}",
                    )
                except NetworkEdge.DoesNotExist:
                    metadata = json.loads(
                        json.dumps(
                            edge_set.loc[edge_set[connection_column] == unique_route]
                            .loc[:, edge_set.columns != "geometry"]
                            .iloc[0]
                            .fillna("")
                            .to_dict()
                        )
                    )
                    edge = NetworkEdge.objects.create(
                        network=network,
                        name=f"{current_node_name} - {next_node_name}",
                        from_node=from_node_obj,
                        to_node=to_node_obj,
                        line_geometry=edge_line_geometry,
                        metadata=metadata,
                    )
                edge.vector_feature = VectorFeature.objects.create(
                    vector_data=vector_data,
                    geometry=edge.line_geometry,
                    properties=edge.metadata
                    | {
                        "from_node_id": from_node_obj.id,
                        "to_node_id": to_node_obj.id,
                        "edge_id": edge.id,
                    },
                )
                edge.save()

    logger.info(
        "%d nodes and %d edges created.",
        NetworkNode.objects.filter(network=network).count(),
        NetworkEdge.objects.filter(network=network).count(),
    )
    logger.info(
        "%d vector features created.",
        VectorFeature.objects.filter(vector_data=vector_data).count(),
    )

    # rewrite vector_data geojson_data with updated features
    vector_data.write_geojson_data(geojson_from_network(vector_data.dataset))
    vector_data.metadata["network"] = True
    vector_data.save()


def geojson_from_network(dataset):
    new_feature_set = []
    for n in NetworkNode.objects.filter(network__vector_data__dataset=dataset):
        node_as_feature = {
            "id": n.id,
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": n.location.coords,
            },
            "properties": dict(node_id=n.id, **n.metadata),
        }
        new_feature_set.append(node_as_feature)

    for e in NetworkEdge.objects.filter(network__vector_data__dataset=dataset):
        edge_as_feature = {
            "id": e.id,
            "type": "Feature",
            "geometry": {
                "type": "LineString",
                "coordinates": e.line_geometry.coords,
            },
            "properties": dict(
                edge_id=e.id,
                from_node_id=e.from_node.id,
                to_node_id=e.to_node.id,
                **e.metadata,
            ),
        }
        new_feature_set.append(edge_as_feature)

    new_geodata = geopandas.GeoDataFrame.from_features(new_feature_set)
    return new_geodata.to_json()


def create_vector_features_from_network(network):
    vector_data = network.vector_data
    VectorFeature.objects.bulk_create(
        [
            VectorFeature(
                vector_data=vector_data,
                geometry=node.location,
                properties=dict(node_id=node.id, **node.metadata),
            )
            for node in network.nodes.all()
        ]
    )
    VectorFeature.objects.bulk_create(
        [
            VectorFeature(
                vector_data=vector_data,
                geometry=edge.line_geometry,
                properties=dict(
                    edge_id=edge.id,
                    from_node_id=edge.from_node.id,
                    to_node_id=edge.to_node.id,
                    **edge.metadata,
                ),
            )
            for edge in network.edges.all()
        ]
    )
