from __future__ import annotations

from django.db import models

from .data import RasterData, VectorData
from .dataset import Dataset


def default_source_filters():
    return {"band": 1}


class Layer(models.Model):
    name = models.CharField(max_length=255, default="Layer")
    dataset = models.ForeignKey(Dataset, related_name="layers", on_delete=models.CASCADE)
    metadata = models.JSONField(blank=True, null=True)
    default_style = models.ForeignKey(
        "LayerStyle", null=True, related_name="default_layer", on_delete=models.SET_NULL
    )

    def __str__(self):
        return f"{self.name} ({self.id})"

    @classmethod
    def filter_queryset_by_projects(cls, queryset, projects):
        return queryset.filter(dataset__project__in=projects)


class LayerFrame(models.Model):
    name = models.CharField(max_length=255, default="Layer Frame")
    layer = models.ForeignKey(Layer, related_name="frames", on_delete=models.CASCADE)
    vector = models.ForeignKey(VectorData, null=True, on_delete=models.CASCADE)
    raster = models.ForeignKey(RasterData, null=True, on_delete=models.CASCADE)
    index = models.PositiveIntegerField(default=0)
    source_filters = models.JSONField(default=default_source_filters)
    metadata = models.JSONField(blank=True, null=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=(models.Q(raster__isnull=False) & models.Q(vector__isnull=True))
                | (models.Q(raster__isnull=True) & models.Q(vector__isnull=False)),
                name="exactly_one_data",
            )
        ]

    def __str__(self):
        return f"{self.name} ({self.id})"

    @classmethod
    def filter_queryset_by_projects(cls, queryset, projects):
        return queryset.filter(layer__dataset__project__in=projects)

    def get_data(self):
        if self.raster is not None:
            return self.raster
        return self.vector
