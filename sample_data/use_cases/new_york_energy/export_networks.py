import json
import shapely

from datetime import datetime
from pathlib import Path

from uvdat.core.models import Network, Region


OUTPUT_FOLDER = Path('sample_data/use_cases/new_york_energy/networks')


def perform_export():
    start = datetime.now()
    networks = Network.objects.filter(vector_data__dataset__name='National Grid Network')
    zones = Region.objects.filter(dataset__name='County Boundaries')

    for network in networks:
        sample_node = network.nodes.first()
        zone = zones.filter(boundary__contains=sample_node.location).first()
        if zone:
            features = []
            for node in network.nodes.all():
                geom = shapely.geometry.mapping(shapely.wkt.loads(node.location.wkt))
                features.append(dict(
                    geometry=geom,
                    properties=dict(
                        **node.metadata,
                        county=zone.name
                    )
                ))
            for edge in network.edges.all():
                geom = shapely.geometry.mapping(shapely.wkt.loads(edge.line_geometry.wkt))
                from_point = shapely.geometry.mapping(shapely.wkt.loads(edge.from_node.location.wkt))
                to_point = shapely.geometry.mapping(shapely.wkt.loads(edge.to_node.location.wkt))
                features.append(dict(
                    geometry=geom,
                    properties=dict(
                        **edge.metadata,
                        from_point=from_point,
                        to_point=to_point,
                        county=zone.name
                    )
                ))
            geodata = dict(
                type="FeatureCollection",
                crs=dict(type='name', properties=dict(name='EPSG:4326')),
                features=features,
            )
            filename = OUTPUT_FOLDER / f'{zone.name}.json'
            with open(filename, 'w') as f:
                json.dump(geodata, f)
            print(f'Wrote {len(features)} features to {filename}.')

    print(f'\tCompleted in {(datetime.now() - start).total_seconds()} seconds.')
