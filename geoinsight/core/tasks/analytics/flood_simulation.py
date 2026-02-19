from __future__ import annotations

import datetime
import os
from pathlib import Path
import tempfile

from celery import shared_task
from django.conf import settings
from django.core.files.base import ContentFile

from geoinsight.core.models import Chart, Colormap, Dataset, FileItem, LayerStyle, TaskResult

from .analysis_type import AnalysisType


class FloodSimulation(AnalysisType):
    def __init__(self):
        super().__init__()
        self.name = 'Flood Simulation'
        self.description = 'Select parameters to simulate a 24-hour flood of the Charles River'
        self.db_value = 'flood_simulation'
        self.input_types = {
            'initial_conditions_id': 'string',
            'time_period': 'string',
            'hydrograph': 'Chart',
            'potential_evapotranspiration_percentile': 'number',
            'soil_moisture_percentile': 'number',
            'ground_water_percentile': 'number',
            'annual_probability': 'number',
        }
        self.output_types = {'flood': 'Dataset'}
        self.attribution = 'Northeastern University'

    @classmethod
    def is_enabled(cls):
        return settings.GEOINSIGHT_ENABLE_TASK_FLOOD_SIMULATION

    def get_input_options(self):
        return {
            'initial_conditions_id': ['001', '002', '003'],
            'time_period': ['2031-2050', '2041-2060'],
            'hydrograph': Chart.objects.filter(name__icontains='hydrograph'),
            'potential_evapotranspiration_percentile': [dict(min=0, max=100, step=1)],
            'soil_moisture_percentile': [dict(min=0, max=100, step=1)],
            'ground_water_percentile': [dict(min=0, max=100, step=1)],
            'annual_probability': [dict(min=0, max=1, step=0.01)],
        }

    def run_task(self, *, project, **inputs):
        result = TaskResult.objects.create(
            name='Flood Simulation',
            task_type=self.db_value,
            inputs=inputs,
            project=project,
            status='Initializing task...',
        )
        flood_simulation.delay(result.id)
        return result


@shared_task
def flood_simulation(result_id):
    from uvdat_flood_sim import run_sim, write_multiframe_geotiff

    result = TaskResult.objects.get(id=result_id)

    try:
        for input_key in [
            'initial_conditions_id',
            'time_period',
            'hydrograph',
            'potential_evapotranspiration_percentile',
            'soil_moisture_percentile',
            'ground_water_percentile',
            'annual_probability',
        ]:
            if result.inputs.get(input_key) is None:
                result.write_error(f'{input_key} not provided')
                result.complete()
                return

        result.write_status('Interpreting input values')
        initial_conditions_id = result.inputs.get('initial_conditions_id')
        time_period = result.inputs.get('time_period')
        hydrograph_id = result.inputs.get('hydrograph')
        hydrograph_chart = Chart.objects.get(id=hydrograph_id)
        hydrograph = hydrograph_chart.chart_data.get('datasets')[0].get('data')
        pet_percentile = result.inputs.get('potential_evapotranspiration_percentile')
        sm_percentile = result.inputs.get('soil_moisture_percentile')
        gw_percentile = result.inputs.get('ground_water_percentile')
        annual_probability = result.inputs.get('annual_probability')

        name = (
            f'{time_period} {annual_probability} Flood Simulation '
            f'with {hydrograph_chart.name}, initial condition set {initial_conditions_id}, '
            f'and percentiles {pet_percentile}, {sm_percentile}, {gw_percentile}'
        )
        result.name = name
        result.write_status('Running flood simulation module with specified inputs')

        flood_results = run_sim(
            initial_conditions_id=initial_conditions_id,
            time_period=time_period,
            annual_probability=annual_probability,
            hydrograph=hydrograph,
            pet_percentile=pet_percentile,
            sm_percentile=sm_percentile,
            gw_percentile=gw_percentile,
        )

        result.write_status('Saving result to database')

        with tempfile.TemporaryDirectory() as output_folder:
            output_path = Path(output_folder) / 'flood_simulation.tif'

            write_multiframe_geotiff(
                flood_results=flood_results,
                output_path=output_path,
                writer='large_image',
            )

            metadata = dict(
                attribution='Simulation code by August Posch at Northeastern University',
                simulation_steps=[
                    'downscaling_prediction',
                    'hydrological_prediction',
                    'hydrodynamic_prediction',
                ],
                module_repository='https://github.com/OpenGeoscience/uvdat-flood-sim',
                inputs=dict(
                    initial_conditions_id=initial_conditions_id,
                    time_period=time_period,
                    hydrograph=hydrograph,
                    pet_percentile=pet_percentile,
                    sm_percentile=sm_percentile,
                    gw_percentile=gw_percentile,
                    annual_probability=annual_probability,
                ),
                uploaded=datetime.datetime.now(datetime.timezone.utc).isoformat(),
            )
            name_match = Dataset.objects.filter(name__icontains=name)
            if name_match.count() > 0:
                name += f' ({name_match.count() + 1})'
            dataset = Dataset.objects.create(
                name=name,
                description='Generated by Flood Simulation Analytics Task',
                category='flood',
                metadata=metadata,
            )
            dataset.set_tags(['analytics', 'flood', 'simulation'])
            file_item = FileItem.objects.create(
                name=output_path.name,
                dataset=dataset,
                file_type='tif',
                file_size=os.path.getsize(output_path),
                metadata=metadata,
            )
            with output_path.open('rb') as f:
                file_item.file.save(output_path.name, ContentFile(f.read()))
            dataset.spawn_conversion_task(
                layer_options=[
                    dict(
                        name='Flood Simulation',
                        source_files=[output_path.name],
                        frame_property='frame',
                    ),
                ],
                network_options=None,
                region_options=None,
                asynchronous=False,
            )

            # Create a default style for new layer
            layer = dataset.layers.first()
            style = LayerStyle.objects.create(
                name='Flood Depth Viridis',
                layer=layer,
                project=result.project,
            )
            layer.default_style = style
            layer.save()
            viridis = Colormap.objects.filter(name='viridis').first()
            style.save_style_configs(
                dict(
                    default_frame=0,
                    opacity=1,
                    colors=[
                        dict(
                            name='all',
                            visible=True,
                            colormap=dict(
                                id=viridis.id,
                                discrete=False,
                                clamp=True,
                                color_by='value',
                                null_color='transparent',
                                range=[0, 2],
                            ),
                        )
                    ],
                    sizes=[
                        dict(
                            name='all',
                            zoom_scaling=True,
                            single_size=5,
                        )
                    ],
                )
            )

            result.outputs = dict(flood=dataset.id)
    except Exception as e:
        result.error = str(e)
    result.complete()
