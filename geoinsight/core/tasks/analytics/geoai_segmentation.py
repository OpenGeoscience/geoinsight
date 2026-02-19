from __future__ import annotations

import datetime

from celery import shared_task
from django.conf import settings
from django.core.files.base import ContentFile
from django_large_image import utilities
import large_image
from pyproj import CRS, Transformer

from geoinsight.core.models import Dataset, FileItem, RasterData, TaskResult

from .analysis_type import AnalysisType


class GeoAISegmentation(AnalysisType):
    def __init__(self):
        super().__init__()
        self.name = 'GeoAI Segmentation'
        self.description = (
            'Leverage GeoAI to detect objects in aerial imagery based on a text prompt'
        )
        self.db_value = 'geoai_segmentation'
        self.input_types = {
            'aerial_imagery': 'RasterData',
            'segmentation_prompt': 'string',
            'tile_size': 'number',
            'tile_overlap': 'number',
            'threshold': 'number',
            'smoothing_sigma': 'number',
        }
        self.output_types = {'result': 'Dataset'}
        self.attribution = 'Open Geospatial Solutions'

    @classmethod
    def is_enabled(cls):
        return settings.GEOINSIGHT_ENABLE_TASK_GEOAI_SEGMENTATION

    def get_input_options(self):
        return {
            'aerial_imagery': RasterData.objects.filter(dataset__category='imagery'),
            'segmentation_prompt': [],
            'tile_size': [128, 256, 512, 1024, 2048],
            'tile_overlap': [4, 8, 16, 32, 64],
            'threshold': [{'min': 0, 'max': 1, 'step': 0.01}],
            'smoothing_sigma': [{'min': 0, 'max': 1, 'step': 0.01}],
        }

    def run_task(self, *, project, **inputs):
        prompt = inputs.get('segmentation_prompt', '')
        result = TaskResult.objects.create(
            name=f'Segment {prompt}',
            task_type=self.db_value,
            inputs=inputs,
            project=project,
            status='Initializing task...',
        )
        geoai_segmentation.delay(result.id)
        return result


@shared_task
def geoai_segmentation(result_id):
    result = TaskResult.objects.get(id=result_id)
    try:
        # Verify inputs
        imagery = None
        imagery_id = result.inputs.get('aerial_imagery')
        segmentation_prompt = result.inputs.get('segmentation_prompt')
        tile_size = result.inputs.get('tile_size')
        tile_overlap = result.inputs.get('tile_overlap')
        threshold = result.inputs.get('threshold')
        smoothing_sigma = result.inputs.get('smoothing_sigma')
        if imagery_id is None:
            result.write_error('Aerial imagery raster data not provided')
        else:
            try:
                imagery = RasterData.objects.get(id=imagery_id)
            except RasterData.DoesNotExist:
                result.write_error('Aerial imagery raster data not found')

        # Run task
        if result.error is None:
            import geoai

            # Update name
            result.name = f'Segmentation of {segmentation_prompt} in {imagery.name}'
            result.save()

            result.write_status('Reading aerial imagery...')
            imagery_path = utilities.field_file_to_local_path(imagery.cloud_optimized_geotiff)
            segmentation_path = imagery_path.parent / 'segmentation.tif'
            mask_path = imagery_path.parent / f'{segmentation_prompt}_mask.tif'

            result.write_status('Loading GeoAI CLIPSegmentation model...')
            segmenter = geoai.CLIPSegmentation(tile_size=tile_size, overlap=tile_overlap)

            result.write_status(f'Segmenting image with prompt "{segmentation_prompt}"...')
            segmenter.segment_image(
                imagery_path,
                output_path=segmentation_path,
                text_prompt=segmentation_prompt,
                threshold=threshold,
                smoothing_sigma=smoothing_sigma,
            )

            # Reformat data as binary mask
            seg = large_image.open(segmentation_path)
            sink = large_image.new()
            region_size = 1000
            for iy in range(int(seg.sizeY / region_size)):
                for ix in range(int(seg.sizeX / region_size)):
                    region = {
                        'top': iy * region_size,
                        'left': ix * region_size,
                        'bottom': (iy + 1) * region_size,
                        'right': (ix + 1) * region_size,
                    }
                    data, _ = seg.getRegion(region=region, format='numpy')
                    mask = (data[:, :, 0] > 0).astype(int) * 255
                    sink.addTile(mask, x=region['left'], y=region['top'])

            # Apply georeferencing to raster output
            projection = 'epsg:4326'
            original = large_image.open(imagery_path)
            source_bounds = original.getMetadata().get('sourceBounds')
            crs_from = CRS(source_bounds.get('srs'))
            crs_to = CRS(projection)
            transformer = Transformer.from_crs(crs_from, crs_to)
            p1 = transformer.transform(source_bounds['xmin'], source_bounds['ymax'])
            p2 = transformer.transform(source_bounds['xmax'], source_bounds['ymin'])
            gcps = [[p1[1], p1[0], 0, 0], [p2[1], p2[0], sink.sizeX, sink.sizeY]]
            sink.projection = projection
            sink.gcps = gcps
            sink.write(mask_path)

            result.write_status('Saving results...')
            dataset_name = f'Segmentation of {segmentation_prompt}'
            existing_count = Dataset.objects.filter(name__contains=dataset_name).count()
            if existing_count:
                dataset_name += f' ({existing_count + 1})'
            dataset = Dataset.objects.create(
                name=dataset_name,
                description='Segmentation generated by GeoAI from aerial imagery',
                category='segmentation',
                metadata={
                    'creation_time': datetime.datetime.now(datetime.timezone.utc).isoformat(),
                    'api': 'https://opengeoai.org/geoai/?h=clipseg#geoai.geoai.CLIPSegmentation',
                },
            )
            dataset.set_tags(['analytics', 'segmentation', 'imagery'])
            raster_file_item = FileItem.objects.create(
                name=mask_path.name,
                dataset=dataset,
                file_type='tif',
                file_size=mask_path.stat().st_size,
            )
            with mask_path.open('rb') as f:
                raster_file_item.file.save(mask_path, ContentFile(f.read()))

            dataset.spawn_conversion_task(asynchronous=False)
            result.outputs = {'result': dataset.id}
    except Exception as e:
        result.error = str(e)
    result.complete()
