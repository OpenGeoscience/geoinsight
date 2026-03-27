from __future__ import annotations

from celery import shared_task
from django.conf import settings
import numpy as np

from uvdat.core.models import TaskResult

from .analysis_type import AnalysisTask, AnalysisType
from .flood_simulation import FloodSimulation


class UncertaintyQuantification(AnalysisType):
    def __init__(self):
        super().__init__()
        self.name = "Flood Uncertainty Quantification"
        self.description = "Select simulated floods and calculate their standard error."
        self.db_value = "uncertainty_quant"
        self.input_types = {
            "flood_simulation_1": "TaskResult",
            "flood_simulation_2": "TaskResult",
            "flood_simulation_3": "TaskResult",
        }
        self.output_types = {
            "mean_precipitation_level_mm": "number",
            "standard_error_precipitation_level_mm": "number",
            "min_precipitation_level_mm": "number",
            "max_precipitation_level_mm": "number",
            "range_precipitation_level_mm": "number",
            "mean_discharge_ft3_per_second": "number",
            "standard_error_discharge_ft3_per_second": "number",
            "min_discharge_ft3_per_second": "number",
            "max_discharge_ft3_per_second": "number",
            "range_discharge_ft3_per_second": "number",
        }
        self.attribution = "Northeastern University"

    @classmethod
    def is_enabled(cls):
        return settings.UVDAT_ENABLE_UNCERTAINTY_QUANTIFICATION

    def get_input_options(self):
        return {
            "flood_simulation_1": TaskResult.objects.filter(task_type=FloodSimulation().db_value),
            "flood_simulation_2": TaskResult.objects.filter(task_type=FloodSimulation().db_value),
            "flood_simulation_3": TaskResult.objects.filter(task_type=FloodSimulation().db_value),
        }

    def run_task(self, *, project, **inputs):
        result = TaskResult.objects.create(
            name="Uncertainty Quantification",
            task_type=self.db_value,
            inputs=inputs,
            project=project,
            status="Initializing task...",
        )
        uncertainty_quantification.delay(result.id)
        return result

    def finalize(self, result):
        pass


@shared_task(base=AnalysisTask)
def uncertainty_quantification(result_id):
    result = TaskResult.objects.get(id=result_id)
    flood_sim_1_id = result.inputs.get("flood_simulation_1")
    flood_sim_1 = TaskResult.objects.get(id=flood_sim_1_id)
    flood_sim_2_id = result.inputs.get("flood_simulation_2")
    flood_sim_2 = TaskResult.objects.get(id=flood_sim_2_id)
    flood_sim_3_id = result.inputs.get("flood_simulation_3")
    flood_sim_3 = TaskResult.objects.get(id=flood_sim_3_id)

    # Update name
    result.name = (
        "Uncertainty Quantification for Flood Results "
        f"{flood_sim_1.id}, {flood_sim_2.id}, {flood_sim_3.id}"
    )
    result.save()

    precip1 = flood_sim_1.outputs.get("precipitation_level_mm")
    discharge1 = flood_sim_1.outputs.get("discharge_ft3_per_second")
    precip2 = flood_sim_2.outputs.get("precipitation_level_mm")
    discharge2 = flood_sim_2.outputs.get("discharge_ft3_per_second")
    precip3 = flood_sim_3.outputs.get("precipitation_level_mm")
    discharge3 = flood_sim_3.outputs.get("discharge_ft3_per_second")

    result.write_status("Calculating uncertainty...")

    precip_mean = np.mean([precip1, precip2, precip3])
    precip_stde = np.std([precip1, precip2, precip3])
    precip_max = np.max([precip1, precip2, precip3])
    precip_min = np.min([precip1, precip2, precip3])
    precip_range = precip_max - precip_min
    discharge_mean = np.mean([discharge1, discharge2, discharge3])
    discharge_stde = np.std([discharge1, discharge2, discharge3])
    discharge_max = np.max([discharge1, discharge2, discharge3])
    discharge_min = np.min([discharge1, discharge2, discharge3])
    discharge_range = discharge_max - discharge_min

    result.write_status("Saving result to database")

    result.write_outputs(
        {
            "mean_precipitation_level_mm": precip_mean,
            "standard_error_precipitation_level_mm": precip_stde,
            "min_precipitation_level_mm": precip_min,
            "max_precipitation_level_mm": precip_max,
            "range_precipitation_level_mm": precip_range,
            "mean_discharge_ft3_per_second": discharge_mean,
            "standard_error_discharge_ft3_per_second": discharge_stde,
            "min_discharge_ft3_per_second": discharge_min,
            "max_discharge_ft3_per_second": discharge_max,
            "range_discharge_ft3_per_second": discharge_range,
        }
    )
