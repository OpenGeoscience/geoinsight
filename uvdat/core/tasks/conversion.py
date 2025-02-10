import json
from pathlib import Path
import tempfile
import zipfile

from django.core.files.base import ContentFile
import geopandas
import large_image
import large_image_converter
import numpy
import rasterio
import shapefile

from uvdat.core.models import RasterData, VectorData

RASTER_FILETYPES = ['tif', 'tiff', 'nc', 'jp2']
IGNORE_FILETYPES = ['dbf', 'sbn', 'sbx', 'cpg', 'shp.xml', 'shx', 'vrt', 'hdf', 'lyr']


def get_cog_path(file):
    raster_path = None
    try:
        # if large_image can open file and geospatial is True, rasterio is not needed.
        source = large_image.open(file)
        if source.geospatial:
            raster_path = file
    except large_image.exceptions.TileSourceError:
        pass

    if raster_path is None:
        # if original data cannot be interpreted by large_image, use rasterio
        raster_path = file.parent / 'rasterio.tiff'
        with open(file, 'rb') as f:
            input_data = rasterio.open(f)
            output_data = rasterio.open(
                raster_path,
                'w',
                driver='GTiff',
                height=input_data.height,
                width=input_data.width,
                count=1,
                dtype=numpy.float32,
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
    source_projection = 4326
    geodata_set = []
    cog_set = []
    metadata = dict(source_filenames=[])
    for file in files:
        metadata.update(file_item.metadata)
        metadata['source_filenames'].append(file_item.name)
        if file.name.endswith('.prj'):
            with open(file, 'rb') as f:
                contents = f.read()
                source_projection = contents.decode()
                continue
        elif file.name.endswith('.shp'):
            reader = shapefile.Reader(file)
            geodata_set.append(dict(name=file.name, features=reader.__geo_interface__['features']))
        elif any(file.name.endswith(suffix) for suffix in ['.json', '.geojson']):
            with open(file, 'rb') as f:
                data = json.load(f)
                geodata_set.append(dict(name=file.name, features=data.get('features')))
                source_projection = data.get('crs', {}).get('properties', {}).get('name')
        elif any(file.name.endswith(suffix) for suffix in RASTER_FILETYPES):
            cog_path = get_cog_path(file)
            if cog_path:
                cog_set.append(dict(name=file.name, path=cog_path))
        elif not any(file.name.endswith(suffix) for suffix in IGNORE_FILETYPES):
            print('\t\tUnable to convert', file.name)

    if combine:
        # combine only works for vector data currently, assumes consistent projection
        all_features = []
        for geodata in geodata_set:
            all_features += geodata.get('features')
        geodata_set = [dict(name=file_item.name, features=all_features)]

    for geodata in geodata_set:
        data, features = geodata.get('data'), geodata.get('features')
        if data is None and len(features):
            gdf = geopandas.GeoDataFrame.from_features(features)
            gdf = gdf.set_crs(source_projection, allow_override=True)
            gdf = gdf.to_crs(4326)
            data = json.loads(gdf.to_json())
        properties = {}
        for feature in data.get('features'):
            for name, value in feature.get('properties', {}).items():
                if name not in properties:
                    properties[name] = []
                if value not in properties[name]:
                    properties[name].append(value)
        metadata['properties'] = properties
        vector_data = VectorData.objects.create(
            name=geodata.get('name'),
            dataset=file_item.dataset,
            source_file=file_item,
            metadata=metadata,
        )
        vector_data.write_geojson_data(data)
        print('\t\t', str(vector_data), 'created for ' + geodata.get('name'))

    for cog in cog_set:
        cog_path = cog.get('path')
        source = large_image.open(cog_path)
        metadata.update(source.getMetadata())
        raster_data = RasterData.objects.create(
            name=cog.get('name'),
            dataset=file_item.dataset,
            source_file=file_item,
            metadata=metadata,
        )
        with open(cog_path, 'rb') as f:
            raster_data.cloud_optimized_geotiff.save(cog_path.name, ContentFile(f.read()))
        print('\t\t', str(raster_data), 'created for ' + cog.get('name'))


def convert_file_item(file_item):
    # write contents to temporary directory for conversion
    with tempfile.TemporaryDirectory() as temp_dir:
        if file_item.file_type == 'zip':
            archive_path = Path(temp_dir, 'archive.zip')
            with open(archive_path, 'wb') as archive_file:
                archive_file.write(file_item.file.open('rb').read())
                with zipfile.ZipFile(archive_path) as zip_archive:
                    files = []
                    for file in zip_archive.infolist():
                        if not file.is_dir():
                            filepath = Path(temp_dir, Path(file.filename).name)
                            with open(filepath, 'wb') as f:
                                f.write(zip_archive.open(file).read())
                            files.append(filepath)
                    combine = file_item.metadata.get('combine_contents', False)
                    convert_files(*files, file_item=file_item, combine=combine)
        else:
            filepath = Path(temp_dir, file_item.name)
            with open(filepath, 'wb') as f:
                with file_item.file.open('rb') as contents:
                    f.write(contents.read())
            convert_files(filepath, file_item=file_item)
