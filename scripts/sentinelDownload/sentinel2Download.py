# /// script
# requires-python = ">=3.8"
# dependencies = [
#     "click",
#     "pystac-client",
#     "requests",
#     "shapely",
#     "rasterio",
#     "pyproj",
# ]
# ///

from datetime import datetime
import json
import os

import click
from pyproj import Transformer
from pystac_client import Client
import rasterio
from rasterio.windows import from_bounds
from shapely.geometry import Point, mapping

# STAC API from AWS Earth Search
STAC_API_URL = 'https://earth-search.aws.element84.com/v1'


def default_end_date():
    return datetime.utcnow().date().isoformat()


def read_cog_window(cog_url, lon, lat, size_km=10):
    """
    Read a size_km x size_km window from the remote COG at lon, lat.

    Returns numpy array data and updated affine transform.
    """
    with rasterio.Env():
        with rasterio.open(cog_url) as src:
            # Convert lat/lon to image CRS coordinates
            transformer = Transformer.from_crs('EPSG:4326', src.crs, always_xy=True)
            x, y = transformer.transform(lon, lat)

            half_size_m = (size_km * 1000) / 2
            bounds = (x - half_size_m, y - half_size_m, x + half_size_m, y + half_size_m)
            window = from_bounds(*bounds, transform=src.transform)

            data = src.read(1, window=window)
            transform = src.window_transform(window)

            # Copy metadata for output
            meta = src.meta.copy()
            meta.update(
                {
                    'height': data.shape[0],
                    'width': data.shape[1],
                    'transform': transform,
                }
            )

            return data, meta


def read_cog_window_rgb(cog_url, lon, lat, size_km=10):
    """
    Read a size_km x size_km window from the remote COG at lon, lat.

    Returns 3-band numpy array data (RGB) and updated affine transform.
    """
    import numpy as np

    with rasterio.Env():
        with rasterio.open(cog_url) as src:
            transformer = Transformer.from_crs('EPSG:4326', src.crs, always_xy=True)
            x, y = transformer.transform(lon, lat)

            half_size_m = (size_km * 1000) / 2
            bounds = (x - half_size_m, y - half_size_m, x + half_size_m, y + half_size_m)
            click.echo(f'  - Window bounds: {bounds}')
            window = from_bounds(*bounds, transform=src.transform)

            # Read bands 1,2,3 (RGB)
            bands = []
            for b in [1, 2, 3]:
                band_data = src.read(b, window=window)
                bands.append(band_data)

            data = np.stack(bands)  # shape: (3, height, width)

            transform = src.window_transform(window)
            meta = src.meta.copy()
            meta.update(
                {
                    'count': 3,
                    'height': data.shape[1],
                    'width': data.shape[2],
                    'transform': transform,
                    'dtype': data.dtype,
                }
            )

            return data, meta


@click.command()
@click.option(
    '--lat', default=43.135763, type=float, required=True, help='Latitude of the location.'
)
@click.option(
    '--lon', default=-74.1767949, type=float, required=True, help='Longitude of the location.'
)
@click.option(
    '--start-date',
    type=str,
    default='2025-01-01',
    show_default=True,
    help='Start date (YYYY-MM-DD).',
)
@click.option(
    '--end-date',
    type=str,
    default=default_end_date,
    show_default=True,
    help='End date (YYYY-MM-DD).',
)
@click.option(
    '--max-results',
    type=int,
    default=5,
    show_default=True,
    help='Maximum number of images to download.',
)
@click.option(
    '--output-dir',
    type=click.Path(),
    default='sequentialTestRasters',
    show_default=True,
    help='Directory to save the downloaded files.',
)
@click.option(
    '--cloud-cover', type=float, default=30.0, show_default=True, help='Max cloud cover percentage.'
)
@click.option(
    '--size-km',
    type=float,
    default=10.0,
    show_default=True,
    help='Size of square window to clip around the point in kilometers.',
)
def download_stac_sentinel(
    lat, lon, start_date, end_date, max_results, output_dir, cloud_cover, size_km
):
    """Download clipped Sentinel-2 L1C visual images from AWS via STAC API."""
    os.makedirs(output_dir, exist_ok=True)

    catalog = Client.open(STAC_API_URL)

    # Point geometry as GeoJSON
    point = Point(lon, lat)
    geom = mapping(point)

    search = catalog.search(
        collections=['sentinel-2-c1-l2a'],
        intersects=geom,
        datetime=f'{start_date}/{end_date}',
        query={'eo:cloud_cover': {'lt': cloud_cover}},
        limit=max_results,
    )

    items = list(search.get_items())

    if not items:
        click.echo('⚠️  No Sentinel-2 images found.')
        click.echo('🔍 Search parameters used:')
        click.echo(f'    - Location: lat={lat}, lon={lon}')
        click.echo(f'    - Date range: {start_date} to {end_date}')
        click.echo(f'    - Cloud cover < {cloud_cover}%')
        click.echo('    - Collection: sentinel-2-c1-l2a')
        click.echo(f'    - Max results: {max_results}')
        click.echo('💡 Suggestions:')
        click.echo('    - Try a wider date range.')
        click.echo('    - Increase the allowed cloud cover (e.g., --cloud-cover 60).')
        click.echo('    - Confirm Sentinel-2 covers your area and date range.')
        return

    click.echo(
        f'✅ Found {len(items)} items. Downloading up to {max_results} clipped visual images...'
    )

    downloaded_files = []

    for i, item in enumerate(items):
        if i >= max_results:
            break
        date_str = item.datetime.strftime('%Y-%m-%d')
        item_id = item.id
        click.echo(f'[{i + 1}/{len(items)}] {item_id} from {date_str}')

        visual_asset = item.assets.get('visual')
        if visual_asset:
            url = visual_asset.href
            filename = f'{item_id}_visual_clip_{int(size_km)}km.tif'
            filepath = os.path.join(output_dir, filename)

            click.echo(f'  - Reading {size_km}km x {size_km}km window around point')
            try:
                data, meta = read_cog_window_rgb(url, lon, lat, size_km=size_km)
                with rasterio.open(filepath, 'w', **meta) as dst:
                    dst.write(data)
                click.echo(f'  - Saved clipped image to {filename}')
                downloaded_files.append(filename)

            except Exception as e:
                click.echo(f'  - ⚠️ Failed to read or save clipped image: {e}')

        else:
            click.echo(f'  - ⚠️ Visual asset not available in item {item_id}')

    click.echo('✅ Download complete.')
    # Generate dataset.json
    dataset_json = {
        'type': 'Dataset',
        'name': 'Sequential Test Rasters',
        'description': 'Clipped Sentinel-2 images downloaded and clipped around point',
        'category': 'imagery',
        'files': [],
        'layers': [],
    }

    project_json = {
        'type': 'Project',
        'name': 'Sentinel-2 Clipped Images',
        'datasets': ['Sequential Test Rasters'],
        'default_map_center': [lat, lon],
        'default_map_zoom': 11,
    }

    # Add each file as its own layer
    layer_frames = []
    for idx, f in enumerate(downloaded_files):
        dataset_json['files'].append({'path': f'{output_dir}/{f}', 'name': f'Frame {idx}'})
        layer_frames.append({'name': f'Sequential Layer {idx}', 'index': idx, 'data': f})

    layer = {'name': 'Sequential Test Layers', 'frames': layer_frames}
    dataset_json['layers'].append(layer)

    json_path = os.path.join(output_dir, 'sample.json')
    with open(json_path, 'w') as jf:
        json.dump([project_json, dataset_json], jf, indent=4)


if __name__ == '__main__':
    download_stac_sentinel()
