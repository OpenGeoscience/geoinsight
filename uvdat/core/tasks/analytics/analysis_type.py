from __future__ import annotations

from abc import ABC, abstractmethod

import celery

from uvdat.core.models import TaskResult


class AnalysisType(ABC):
    def __init__(self, *args):
        self.name = ""
        self.description = ""
        self.db_value = ""  # cannot be longer than 25 characters
        self.input_types = {}
        self.output_types = {}
        self.attribution = "Kitware, Inc."

    @classmethod
    @abstractmethod
    def is_enabled(cls):
        raise NotImplementedError

    @abstractmethod
    def get_input_options(self):
        raise NotImplementedError

    @abstractmethod
    def run_task(self, *, project, **inputs):
        raise NotImplementedError


class AnalysisTask(celery.Task):
    def on_failure(self, exc, task_id, args, kwargs, einfo):
        # All analysis tasks use this signature
        task_result_id = args[0]

        task_result = TaskResult.objects.get(pk=task_result_id)
        task_result.write_error("An error occurred during this task. See logs for details.")
        task_result.complete()
