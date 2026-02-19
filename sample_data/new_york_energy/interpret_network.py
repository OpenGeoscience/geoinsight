from __future__ import annotations

import json

import geopandas
import shapely
from webcolors import name_to_hex

TOLERANCE = 0.0001


def get_properties(feature):
    properties = json.loads(
        feature.drop(['geometry', 'index'], errors='ignore').fillna('').to_json()
    )
    properties.update(
        {
            'colors': ','.join(
                [
                    name_to_hex(
                        (
                            properties.get(
                                'color',
                            )
                            or 'black'
                        ).replace(' ', '')
                    ),
                    '#ffffff',
                ]
            )
        }
    )
    return properties


def merge_properties(p1, p2):
    properties = {}
    if p1 is None:
        return p2
    if p2 is None:
        return p1
    for k1, v1 in p1.items():
        v2 = p2.get(k1)
        if v2 is None or v2 == '':
            properties[k1] = v1
        elif v1 is None or v1 == '':
            properties[k1] = v2
        else:
            properties[k1] = ','.join([str(v1), str(v2)])
    # update p2 with merged properties to catch keys not in p1
    return p2.update(properties)


def cut_crossed_lines(gdf):
    # cut lines at any cross points
    separated_features = []
    for _, feature in gdf.iterrows():
        properties = json.loads(
            feature.drop(['geometry', 'index'], errors='ignore').fillna('').to_json()
        )
        curr_geom = feature.geometry
        crosses = gdf[gdf.geometry.crosses(curr_geom)]
        separated = []
        if len(crosses) > 0:
            split_points = []
            for _, cross in crosses.iterrows():
                p = cross.geometry.intersection(curr_geom)
                if p.geom_type == 'MultiPoint':
                    split_points.append(p.geoms[0])
                elif p.geom_type == 'Point':
                    split_points.append(p)
            separated = shapely.ops.split(curr_geom, shapely.MultiPoint(split_points)).geoms
        else:
            separated = [feature.geometry]
        separated_features.extend(
            [
                {
                    'type': 'Feature',
                    'geometry': json.loads(shapely.to_geojson(s)),
                    'properties': properties,
                }
                for s in separated
            ]
        )

    return geopandas.GeoDataFrame.from_features(separated_features)


def merge_lines(gdf):
    visited = []
    merged_features = []
    for feat_index, feature in gdf.iterrows():
        if feat_index not in visited:
            visited.append(feat_index)
            properties = json.loads(
                feature.drop(['geometry', 'index'], errors='ignore').fillna('').to_json()
            )
            curr_geom = feature.geometry
            not_visited = gdf[~gdf.index.isin(visited)]
            touching = not_visited[not_visited.geometry.touches(curr_geom)]
            snapped = touching.snap(curr_geom, TOLERANCE * 2)
            merge = shapely.line_merge(shapely.union_all([*snapped.geometry, curr_geom]))
            curr_segment = None
            if merge.geom_type == 'MultiLineString':
                for segment in merge.geoms:
                    if segment.contains(curr_geom) and not any(
                        s.touches(segment) for s in merge.geoms if s != segment
                    ):
                        curr_segment = segment
            elif merge.geom_type == 'LineString':
                curr_segment = merge

            if curr_segment is None:
                # no valid merge segment, include feature as-is
                merged_features.append(
                    {
                        'type': 'Feature',
                        'geometry': json.loads(shapely.to_geojson(curr_geom)),
                        'properties': properties,
                    }
                )
            else:
                # valid merge segment, mark constituent features as visited
                visited_indexes = list(snapped[snapped.geometry.within(curr_segment)].index)
                visited += visited_indexes
                visited_features = gdf.loc[visited_indexes]
                for _, v_feature in visited_features.iterrows():
                    properties = merge_properties(
                        properties,
                        json.loads(
                            v_feature.drop(['geometry', 'index'], errors='ignore')
                            .fillna('')
                            .to_json()
                        ),
                    )
                merged_features.append(
                    {
                        'type': 'Feature',
                        'geometry': json.loads(shapely.to_geojson(curr_segment)),
                        'properties': properties,
                    }
                )
    gdf = geopandas.GeoDataFrame.from_features(merged_features)
    return cut_crossed_lines(gdf)


def find_nodes(gdf):
    nodes = []

    for _, feature in gdf.iterrows():
        properties = get_properties(feature)
        curr_geom = feature.geometry
        points = [shapely.Point(*p) for p in curr_geom.coords]
        # create nodes at line endpoints
        for endpoint in [points[0], points[-1]]:
            # touching_lines = gdf[gdf.geometry.snap(endpoint, TOLERANCE).touches(endpoint)]
            existing_node_locations = geopandas.GeoSeries([n['location'] for n in nodes])
            if (
                # allow endpoints (1 touching) and intersections (>2 touching)
                # (len(touching_lines) == 1 or len(touching_lines) > 2 ) and
                # omit duplicates within tolerance radius
                not existing_node_locations.dwithin(endpoint, TOLERANCE).any()
            ):
                nodes.append({'location': endpoint, 'metadata': properties})
    return nodes


def find_edges(gdf, nodes):
    edges = []
    existing_node_locations = geopandas.GeoSeries([n['location'] for n in nodes])
    for _, feature in gdf.iterrows():
        properties = get_properties(feature)
        curr_geom = feature.geometry
        points = [shapely.Point(*p) for p in curr_geom.coords]
        nearby_nodes = existing_node_locations[
            existing_node_locations.dwithin(curr_geom, TOLERANCE)
        ]
        snapped = shapely.snap(
            shapely.MultiPoint(list(nearby_nodes.geometry)), curr_geom, TOLERANCE
        )
        separated = shapely.ops.split(shapely.LineString(points), snapped).geoms
        existing_edge_geometries = geopandas.GeoSeries([e['line_geometry'] for e in edges])
        for segment in separated:
            endpoints = [
                shapely.Point(segment.coords[0]),
                shapely.Point(segment.coords[-1]),
            ]
            from_points = nearby_nodes[nearby_nodes.dwithin(endpoints[0], TOLERANCE)]
            to_points = nearby_nodes[nearby_nodes.dwithin(endpoints[1], TOLERANCE)]
            if (
                len(from_points) > 0
                and len(to_points) > 0
                and not shapely.snap(existing_edge_geometries, segment, TOLERANCE)
                .covers(segment)
                .any()
            ):
                edges.append(
                    {
                        'line_geometry': segment,
                        'from_point': from_points.iloc[0],
                        'to_point': to_points.iloc[0],
                        'metadata': properties,
                    }
                )
    return edges


def interpret_group(gdf):
    print(f'\t\t Reading group with {len(gdf)} features.')
    # iteratively merge lines until no more merging can be done
    merged_gdf = merge_lines(gdf)
    while len(merged_gdf) < len(gdf):
        gdf = merged_gdf
        merged_gdf = merge_lines(gdf)
    print(f'\t\tMerged to {len(gdf)} lines.')

    nodes = find_nodes(gdf)
    edges = find_edges(gdf, nodes)

    return nodes, edges
