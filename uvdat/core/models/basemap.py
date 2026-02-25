from __future__ import annotations

from django.db import models

from .querysets import ProjectQuerySet


class Basemap(models.Model):
    name = models.CharField(max_length=100)
    style = models.JSONField()

    # Basemap permissions are not determined by Project permissions
    project_filter_path = None
    objects = ProjectQuerySet.as_manager()

    def __str__(self):
        return f"{self.name} ({self.id})"
