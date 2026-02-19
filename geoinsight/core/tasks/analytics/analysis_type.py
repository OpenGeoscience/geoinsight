from __future__ import annotations

from abc import ABC, abstractmethod


class AnalysisType(ABC):
    def __init__(self, *args):
        self.name = ''
        self.description = ''
        self.db_value = ''  # cannot be longer than 25 characters
        self.input_types = {}
        self.output_types = {}
        self.attribution = 'Kitware, Inc.'

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
