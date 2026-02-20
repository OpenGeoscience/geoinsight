from __future__ import annotations

from django.db import models
from django.dispatch import receiver
from django_extensions.db.models import TimeStampedModel
from s3_file_field import S3FileField

from .chart import Chart
from .dataset import Dataset


class FileItem(TimeStampedModel):
    name = models.CharField(max_length=50)
    dataset = models.ForeignKey(
        Dataset, on_delete=models.CASCADE, related_name="source_files", null=True
    )
    chart = models.ForeignKey(Chart, on_delete=models.CASCADE, null=True)
    file = S3FileField()
    file_type = models.CharField(max_length=25)
    file_size = models.PositiveBigIntegerField(null=True)
    metadata = models.JSONField(blank=True, null=True)
    index = models.IntegerField(null=True)

    def __str__(self):
        return f"{self.name} ({self.id})"

    @classmethod
    def filter_queryset_by_projects(cls, queryset, projects):
        return queryset.filter(dataset__project__in=projects)


@receiver(models.signals.post_delete, sender=FileItem)
def delete_content(sender, instance, **kwargs):
    if instance.file:
        instance.file.delete(save=False)
