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


class AnalysisInputError(Exception):
    pass


class AnalysisTask(celery.Task):
    def get_task_result(self, args):
        # All analysis tasks use this signature
        task_result_id = args[0]
        return TaskResult.objects.get(pk=task_result_id)

    def before_start(self, task_id, args, kwargs):
        # Avoid circular import
        from . import analysis_types

        task_result = self.get_task_result(args)
        for analysis_type_class in analysis_types:
            analysis_type = analysis_type_class()
            if analysis_type.db_value == task_result.task_type:
                # Validate inputs present
                for input_name in analysis_type.input_types:
                    input_value = task_result.inputs.get(input_name)
                    if input_value is None:
                        raise AnalysisInputError(f"{input_name} not provided.")

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        task_result = self.get_task_result(args)
        err_msg = (
            str(exc)
            if isinstance(exc, AnalysisInputError)
            else "An error occurred during this task. See logs for details."
        )
        task_result.write_error(err_msg)

    def after_return(self, status, retval, task_id, args, kwargs, einfo):  # noqa: PLR0913
        task_result = self.get_task_result(args)
        task_result.complete()
