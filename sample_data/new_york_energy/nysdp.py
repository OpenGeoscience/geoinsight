from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
import json
from pathlib import Path

from django.contrib.gis.geos import GEOSGeometry, LineString, Point
import geopandas
import requests

from geoinsight.core.models import (
    Network,
    NetworkEdge,
    NetworkNode,
    Region,
    VectorData,
    VectorFeature,
)
from geoinsight.core.tasks.networks import create_vector_features_from_network

from .interpret_network import interpret_group

DOWNLOAD_PATH = Path(__file__).parent.parent
NYDSP_URL = 'https://systemdataportal.nationalgrid.com/arcgis/rest/services/NYSDP'
RECORDS_PER_PAGE = 1000
SERVICE_SUFFIX = 'MapServer'
FORMAT_SUFFIX = 'f=pjson'
QUERY_CONTENT = (
    f'where=1%3D1&returnGeometry=true&outFields=*&resultRecordCount={RECORDS_PER_PAGE}&f=geojson'
)


def fetch_vector_features(service_name=None, **kwargs):
    feature_sets = {}
    if service_name is None:
        return feature_sets
    service_url = f'{NYDSP_URL}/{service_name}/{SERVICE_SUFFIX}'
    service_info = requests.get(f'{service_url}?{FORMAT_SUFFIX}').json()
    for layer in service_info.get('layers', []):
        feature_set = []
        layer_id = layer.get('id')
        if layer_id is not None:
            feature_page = None
            result_offset = 0
            while feature_page is None or len(feature_page) == RECORDS_PER_PAGE:
                query_response = requests.get(
                    f'{service_url}/{layer_id}/query?resultOffset={result_offset}&{QUERY_CONTENT}'
                )
                try:
                    query_json = query_response.json()
                    feature_page = query_json.get('features', [])
                    feature_set += feature_page
                    result_offset += RECORDS_PER_PAGE
                except Exception:
                    print(f'\t\tFailed to get {service_name} data from NYSDP.')
        if len(feature_set):
            feature_sets[layer_id] = feature_set
    return feature_sets


def create_vector_features(dataset, service_name=None, **kwargs):
    VectorData.objects.filter(dataset=dataset).delete()
    vector_data = VectorData.objects.create(dataset=dataset, name=dataset.name)
    feature_sets = fetch_vector_features(service_name=service_name)
    vector_features = []
    for feature_set in feature_sets.values():
        for feature in feature_set:
            vector_features.append(
                VectorFeature(
                    vector_data=vector_data,
                    geometry=GEOSGeometry(json.dumps(feature['geometry'])),
                    properties=feature['properties'],
                )
            )
    VectorFeature.objects.bulk_create(vector_features)


def download_all_deduped_vector_features(**kwargs):
    start = datetime.now()
    include_services = kwargs.get(
        'include_services',
        [
            'DistAssetsOverview',
            'Electrification_Data',
            'EV_Load_Serving_Capacity',
            'Hosting_Capacity_Data',
            'LSRV',
            'NY_SubT_SDP',
        ],
    )
    downloads_folder = kwargs.get('downloads_folder')
    downloads_folder = Path(__file__).parent if downloads_folder is None else Path(downloads_folder)
    filename = downloads_folder / 'nyc' / 'network_basic_features.json'
    if filename.exists():
        print('\t\tReading saved file of basic features.')
        return geopandas.GeoDataFrame.from_file(filename)

    print('\t\tDownloading basic features from NYSDP.')
    feature_sets = None
    with ThreadPoolExecutor(max_workers=len(include_services)) as pool:
        feature_sets = pool.map(fetch_vector_features, include_services)

    features = []
    for feature_set in feature_sets:
        for fset in feature_set.values():
            for feature in fset:
                properties = feature['properties']
                geometry = GEOSGeometry(json.dumps(feature['geometry']))
                geoms = []
                # split multilinestrings
                if geometry.geom_type == 'MultiLineString':
                    geoms = [LineString(*line) for line in geometry.coords]
                elif geometry.geom_type == 'LineString':
                    geoms = [geometry]
                for geom in geoms:
                    features.append(
                        {
                            'type': 'Feature',
                            'geometry': json.loads(geom.json),
                            'properties': properties,
                        }
                    )
    # normalize and eliminate duplicates
    gdf = geopandas.GeoDataFrame.from_features(features, crs='EPSG:4326')
    gdf['geometry'] = gdf.normalize()
    gdf = gdf.groupby(gdf.geometry.to_wkt()).first()
    gdf.reset_index(inplace=True)

    gdf.to_file(filename)
    print(f'\t\tCompleted download in {(datetime.now() - start).total_seconds()} seconds.')
    return gdf


def create_consolidated_network(dataset, **kwargs):
    start = datetime.now()
    Network.objects.filter(vector_data__dataset=dataset).delete()
    VectorData.objects.filter(dataset=dataset).delete()
    gdf = download_all_deduped_vector_features(**kwargs)

    zones_dataset_name = kwargs.get('zones_dataset_name')
    if zones_dataset_name is None:
        raise ValueError('`zones_dataset_name` is required.')
    zones = Region.objects.filter(dataset__name=zones_dataset_name)
    if zones.count() == 0:
        raise ValueError(f"No regions found with dataset name '{zones_dataset_name}'.")

    print(f'\t\tInterpreting networks from {len(gdf)} basic features...')
    # Divide into groups
    zone_geometries = [
        geopandas.GeoSeries.from_wkt([zone.boundary.wkt]).set_crs(4326).iloc[0] for zone in zones
    ]
    groups = [gdf[gdf.geometry.covered_by(zone_geom)] for zone_geom in zone_geometries]
    groups = [g for g in groups if len(g) > 0]
    print(f'\t\tSeparated into {len(groups)} groups.')

    with ThreadPoolExecutor(max_workers=10) as pool:
        results = pool.map(interpret_group, groups)
    for i, result in enumerate(results):
        nodes, edges = result
        vector_data = VectorData.objects.create(
            name=f'{dataset.name} Network {i}',
            dataset=dataset,
        )
        network = Network.objects.create(
            name=vector_data.name, vector_data=vector_data, category='energy'
        )
        NetworkNode.objects.bulk_create(
            [
                NetworkNode(
                    network=network,
                    name=f'Node {i}',
                    location=Point(n.get('location').x, n.get('location').y),
                    metadata=n.get('metadata', {}),
                )
                for i, n in enumerate(nodes)
            ],
            batch_size=1000,
        )
        NetworkEdge.objects.bulk_create(
            [
                NetworkEdge(
                    network=network,
                    name=f'Edge {i}',
                    from_node=NetworkNode.objects.get(
                        network=network,
                        location=Point(e.get('from_point').x, e.get('from_point').y),
                    ),
                    to_node=NetworkNode.objects.get(
                        network=network, location=Point(e.get('to_point').x, e.get('to_point').y)
                    ),
                    line_geometry=LineString(*e.get('line_geometry').coords),
                    metadata=e.get('metadata', {}),
                )
                for i, e in enumerate(edges)
            ],
            batch_size=1000,
        )

        print(f'\t\t{network.nodes.count()} nodes created, {network.edges.count()} edges created.')
        create_vector_features_from_network(network)

    print(f'\t\t{dataset.networks.count()} separate networks created.')
    print(f'\tCompleted in {(datetime.now() - start).total_seconds()} seconds.')
