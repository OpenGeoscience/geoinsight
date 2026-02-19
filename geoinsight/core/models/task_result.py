from __future__ import annotations

import json

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone

from .project import Project


class TaskResult(models.Model):
    name = models.CharField(max_length=255)
    task_type = models.CharField(max_length=25)
    project = models.ForeignKey(
        Project, on_delete=models.CASCADE, related_name='task_results', null=True
    )
    inputs = models.JSONField(blank=True, null=True)
    outputs = models.JSONField(blank=True, null=True)
    status = models.TextField(null=True, blank=True)
    error = models.TextField(null=True, blank=True)
    created = models.DateTimeField(auto_now_add=True, editable=False)
    completed = models.DateTimeField(null=True)

    def __str__(self):
        return f'{self.name} ({self.id})'

    @classmethod
    def filter_queryset_by_projects(cls, queryset, projects):
        return queryset.filter(models.Q(project__isnull=True) | models.Q(project__in=projects))

    def write_error(self, err):
        if self.error is None:
            self.error = ''
        else:
            self.error += ', '
        self.error += err
        self.save()

    def write_status(self, stat):
        self.status = stat
        self.save()

    def complete(self):
        self.completed = timezone.now()
        seconds = (self.completed - self.created).total_seconds()
        self.status = f'Completed in {seconds:.2f} seconds.'
        self.save()


@receiver(post_save, sender=TaskResult)
def result_post_save(sender, instance, **kwargs):
    from geoinsight.core.rest.serializers import TaskResultSerializer

    payload = TaskResultSerializer(instance).data
    group_name = 'conversion'
    if instance.project:
        group_name = f'analytics_{instance.project.id}'
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        group_name, {'type': 'send_notification', 'message': json.dumps(payload)}
    )
