from __future__ import annotations

from datetime import datetime
import json
from pathlib import Path
import tempfile
import zipfile

from django.contrib.gis.geos import LineString, Point

from geoinsight.core.models import Network, NetworkEdge, NetworkNode, VectorData
from geoinsight.core.tasks.networks import create_vector_features_from_network

TOLERANCE_METERS = 15


def get_metadata(feature):
    return {k: v for k, v in feature.get('properties', {}).items() if k and v}


def create_network(dataset, network_name, geodata):
    print(f'\t\tCreating network for {network_name}.')
    vector_data = VectorData.objects.create(
        name=network_name,
        dataset=dataset,
    )
    network = Network.objects.create(
        name=network_name,
        category='energy',
        vector_data=vector_data,
        metadata=dict(name=network_name),
    )
    features = geodata.get('features')
    nodes = []
    edges = []
    for feature in features:
        geom = feature.get('geometry')
        if geom.get('type') == 'Point':
            nodes.append(
                NetworkNode(
                    name=f'{network_name} {len(nodes)}',
                    network=network,
                    location=Point(*geom.get('coordinates')),
                    metadata=get_metadata(feature),
                )
            )
        elif geom.get('type') == 'LineString':
            edges.append(
                NetworkEdge(
                    name=f'{network_name} {len(edges)}',
                    network=network,
                    line_geometry=LineString(*geom.get('coordinates')),
                    metadata=get_metadata(feature),
                )
            )
    NetworkNode.objects.bulk_create(nodes, batch_size=1000)

    # fill in node relationships on edges now that nodes exist
    connected_node_ids = []
    for edge in edges:
        metadata = edge.metadata
        from_point = metadata.get('from_point', {}).get('coordinates')
        to_point = metadata.get('to_point', {}).get('coordinates')
        if from_point is not None and to_point is not None:
            from_point = Point(*from_point)
            to_point = Point(*to_point)
            from_nodes = NetworkNode.objects.filter(network=network, location=from_point)
            to_nodes = NetworkNode.objects.filter(network=network, location=to_point)
            if from_nodes.count() > 0 and to_nodes.count() > 0:
                edge.from_node = from_nodes.first()
                edge.to_node = to_nodes.first()
                if edge.from_node.id not in connected_node_ids:
                    connected_node_ids.append(edge.from_node.id)
                if edge.to_node.id not in connected_node_ids:
                    connected_node_ids.append(edge.to_node.id)

    # remove any nodes that have no connections
    not_connected = NetworkNode.objects.filter(network=network).exclude(id__in=connected_node_ids)
    not_connected.delete()

    NetworkEdge.objects.bulk_create(edges, batch_size=1000)
    create_vector_features_from_network(network)
    print(f'\t\tCreated {network.nodes.count()} nodes and {network.edges.count()} edges.')


def perform_import(dataset, **kwargs):
    print('\tEstimated time: 45 minutes.')
    start = datetime.now()
    Network.objects.filter(vector_data__dataset=dataset).delete()
    VectorData.objects.filter(dataset=dataset).delete()
    for file_item in dataset.source_files.all():
        with tempfile.TemporaryDirectory() as temp_dir:
            archive_path = Path(temp_dir, 'archive.zip')
            with open(archive_path, 'wb') as archive_file:
                archive_file.write(file_item.file.open('rb').read())
                with zipfile.ZipFile(archive_path) as zip_archive:
                    filenames = zip_archive.namelist()
                    for filename in filenames:
                        if filename.endswith('.json'):
                            network_name = filename.split('/')[-1].replace('.json', '').title()
                            content = zip_archive.open(filename).read()
                            geodata = json.loads(content)
                            create_network(dataset, network_name, geodata)
    print(f'\tCompleted in {(datetime.now() - start).total_seconds()} seconds.')
