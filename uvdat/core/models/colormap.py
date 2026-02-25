from __future__ import annotations

from django.db import models
from jsonschema import validate

from .project import Project
from .querysets import ProjectQuerySet

MARKER_SCHEMA = {
    "type": "array",
    "items": {
        "type": "object",
        "properties": {
            "color": {
                "type": "string",
            },
            "value": {
                "type": "number",
                "minimum": 0,
                "maximum": 1,
            },
        },
        "required": ["color", "value"],
    },
    "minItems": 2,
    "uniqueItems": True,
}


class Colormap(models.Model):
    name = models.CharField(max_length=255)
    markers = models.JSONField(default=list)
    project = models.ForeignKey(
        Project,
        related_name="colormaps",
        on_delete=models.CASCADE,
        null=True,
    )

    project_filter_path = "project"
    project_filter_allow_null = True
    objects = ProjectQuerySet.as_manager()

    def __str__(self):
        return f"{self.name} ({self.id})"

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def clean(self):
        if len(self.markers):
            validate(instance=self.markers, schema=MARKER_SCHEMA)
