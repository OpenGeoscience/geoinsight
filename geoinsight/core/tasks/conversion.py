from __future__ import annotations

import json
from pathlib import Path
import tempfile
import zipfile

from django.core.files.base import ContentFile
from django_large_image import utilities
import geopandas
import numpy as np
import rasterio
import shapefile

from geoinsight.core.models import RasterData, VectorData

RASTER_FILETYPES = ['tif', 'tiff', 'nc', 'jp2']
IGNORE_FILETYPES = ['dbf', 'sbn', 'sbx', 'cpg', 'shp.xml', 'shx', 'vrt', 'hdf', 'lyr']


def get_cog_path(file):
    import large_image
    import large_image_converter

    raster_path = None
    try:
        # if large_image can open file and geospatial is True, rasterio is not needed.
        source = large_image.open(file)
        if source.geospatial:
            raster_path = file
            metadata = source.getMetadata()
            if len(metadata.get('frames', [])) > 1:
                # If multiframe, return early;
                # large_image_converter is not multiframe-compatible yet
                return raster_path
    except large_image.exceptions.TileSourceError:
        pass

    if raster_path is None:
        # if original data cannot be interpreted by large_image, use rasterio
        raster_path = file.parent / 'rasterio.tiff'
        with file.open('rb') as f:
            input_data = rasterio.open(f)
            output_data = rasterio.open(
                raster_path,
                'w',
                driver='GTiff',
                height=input_data.height,
                width=input_data.width,
                count=1,
                dtype=np.float32,
                crs=input_data.crs,
                transform=input_data.transform,
            )
            band = input_data.read(1)
            output_data.write(band, 1)
            output_data.close()

    cog_path = file.parent / file.name.replace(file.suffix, 'tiff')
    # use large_image to convert new raster data to COG
    large_image_converter.convert(str(raster_path), str(cog_path), overwrite=True)
    return cog_path


def convert_files(*files, file_item=None, combine=False):
    source_projection = 'epsg:4326'
    geodata_set = []
    cog_set = []
    metadata = {'source_filenames': []}
    for file in files:
        if file_item.metadata:
            metadata.update(file_item.metadata)
        metadata['source_filenames'].append(file_item.name)
        if file.name.endswith('.prj'):
            with file.open('rb') as f:
                contents = f.read()
                source_projection = contents.decode()
                continue
        elif file.name.endswith('.shp'):
            reader = shapefile.Reader(file)
            geodata_set.append(
                {'name': file.name, 'features': reader.__geo_interface__['features']}
            )
        elif any(file.name.endswith(suffix) for suffix in ['.json', '.geojson']):
            with file.open('rb') as f:
                data = json.load(f)
                geodata_set.append({'name': file.name, 'features': data.get('features')})
                source_projection = data.get('crs', {}).get('properties', {}).get('name')
        elif any(file.name.endswith(suffix) for suffix in RASTER_FILETYPES):
            cog_path = get_cog_path(file)
            if cog_path:
                cog_set.append({'name': file.name, 'path': cog_path})
        elif not any(file.name.endswith(suffix) for suffix in IGNORE_FILETYPES):
            print('\t\tUnable to convert', file.name)

    if combine:
        # combine only works for vector data currently, assumes consistent projection
        all_features = []
        for geodata in geodata_set:
            all_features += geodata.get('features')
        geodata_set = [{'name': file_item.name, 'features': all_features}]

    for geodata in geodata_set:
        data, features = geodata.get('data'), geodata.get('features')
        if data is None and len(features):
            gdf = geopandas.GeoDataFrame.from_features(features)
            if source_projection is not None:
                gdf = gdf.set_crs(source_projection, allow_override=True)
                gdf = gdf.to_crs(4326)
            data = json.loads(gdf.to_json())
        vector_data = VectorData.objects.create(
            name=geodata.get('name'),
            dataset=file_item.dataset,
            source_file=file_item,
            metadata=metadata,
        )
        vector_data.write_geojson_data(data)
        print('\t\t', str(vector_data), 'created for ' + geodata.get('name'))

    for cog in cog_set:
        import large_image

        cog_path = cog.get('path')
        source = large_image.open(cog_path)
        metadata.update(source.getMetadata())
        raster_data = RasterData.objects.create(
            name=cog.get('name'),
            dataset=file_item.dataset,
            source_file=file_item,
            metadata=metadata,
        )
        with cog_path.open('rb') as f:
            raster_data.cloud_optimized_geotiff.save(cog_path.name, ContentFile(f.read()))
        print('\t\t', str(raster_data), 'created for ' + cog.get('name'))


def convert_file_item(file_item):
    path = utilities.field_file_to_local_path(file_item.file)
    if file_item.file_type == 'zip':
        # write contents to temporary directory for conversion
        with tempfile.TemporaryDirectory() as temp_dir, zipfile.ZipFile(path) as zip_archive:
            files = []
            for file in zip_archive.infolist():
                if not file.is_dir():
                    filepath = Path(temp_dir, Path(file.filename).name)
                    with filepath.open('wb') as f:
                        f.write(zip_archive.open(file).read())
                    files.append(filepath)
            combine = False
            if file_item.metadata:
                combine = file_item.metadata.get('combine_contents', combine)
            convert_files(*files, file_item=file_item, combine=combine)
    else:
        convert_files(path, file_item=file_item)
