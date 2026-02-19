from __future__ import annotations

from django.db import models
from jsonschema import validate

from .project import Project

MARKER_SCHEMA = dict(
    type='array',
    items=dict(
        type='object',
        properties=dict(
            color=dict(
                type='string',
            ),
            value=dict(
                type='number',
                minimum=0,
                maximum=1,
            ),
        ),
        required=['color', 'value'],
    ),
    minItems=2,
    uniqueItems=True,
)


class Colormap(models.Model):
    name = models.CharField(max_length=255)
    markers = models.JSONField(default=list)
    project = models.ForeignKey(
        Project,
        related_name='colormaps',
        on_delete=models.CASCADE,
        null=True,
    )

    def __str__(self):
        return f'{self.name} ({self.id})'

    @classmethod
    def filter_queryset_by_projects(cls, queryset, projects):
        return queryset.filter(models.Q(project__isnull=True) | models.Q(project__in=projects))

    def clean(self):
        if len(self.markers):
            validate(instance=self.markers, schema=MARKER_SCHEMA)

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)
