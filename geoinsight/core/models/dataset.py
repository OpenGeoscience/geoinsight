from __future__ import annotations

import typing

from django.db import models, transaction
from guardian.models import UserObjectPermission
from guardian.shortcuts import assign_perm, get_users_with_perms

from geoinsight.core.tasks.dataset import convert_dataset

if typing.TYPE_CHECKING:
    from django.contrib.auth.models import User


class DatasetTag(models.Model):
    tag = models.CharField(max_length=255, unique=True)

    def __str__(self):
        return self.tag

    class Meta:
        ordering = ['tag']


class Dataset(models.Model):
    name = models.CharField(max_length=255, unique=True)
    description = models.TextField(null=True, blank=True)
    category = models.CharField(max_length=25)
    processing = models.BooleanField(default=False)
    tags = models.ManyToManyField(DatasetTag, blank=True)
    metadata = models.JSONField(blank=True, null=True)

    class Meta:
        permissions = [('owner', 'Can read, write, and delete')]

    def __str__(self):
        return f'{self.name} ({self.id})'

    @classmethod
    def filter_queryset_by_projects(cls, queryset, projects):
        # Dataset permissions are not determined by Project permissions
        return queryset

    def owner(self) -> User | None:
        users = typing.cast(
            'list[User]', list(get_users_with_perms(self, only_with_perms_in=['owner']))
        )
        if len(users) != 1:
            return None
        return users[0]

    @transaction.atomic()
    def set_owner(self, user: User):
        filters = {
            'content_type__app_label': self._meta.app_label,
            'content_type__model': self._meta.model_name,
            'object_pk': self.pk,
        }

        # Remove existing owner
        UserObjectPermission.objects.filter(
            **filters,
            permission__codename='owner',
        ).delete()

        # Delete any existing user perms and set owner
        UserObjectPermission.objects.filter(
            **filters,
            user_id__in=[user.id],
        ).delete()
        assign_perm('owner', user, self)

    @transaction.atomic()
    def set_tags(self, tags: list[str]):
        for tag in tags:
            DatasetTag.objects.get_or_create(tag=tag)
        self.tags.set(DatasetTag.objects.filter(tag__in=tags))

    def spawn_conversion_task(
        self,
        layer_options=None,
        network_options=None,
        region_options=None,
        asynchronous=True,
    ):
        if asynchronous:
            from geoinsight.core.models.task_result import TaskResult

            result = TaskResult.objects.create(
                name=f'Conversion of Dataset {self.name}',
                task_type='conversion',
                inputs={
                    'dataset_id': self.id,
                    'layer_options': layer_options,
                    'network_options': network_options,
                    'region_options': region_options,
                },
                status='Initializing task...',
            )
            convert_dataset.delay(
                self.id, layer_options, network_options, region_options, result.id
            )
            return result
        else:
            convert_dataset(self.id, layer_options, network_options, region_options)
            return None

    def get_size(self):
        from geoinsight.core.models import FileItem

        size = 0
        for file_item in FileItem.objects.filter(dataset=self):
            if file_item.file_size is not None:
                size += file_item.file_size
        return size

    def get_networks(self):
        from geoinsight.core.models import Network

        return Network.objects.filter(vector_data__dataset=self)

    def get_regions(self):
        from geoinsight.core.models import Region

        return Region.objects.filter(dataset=self)
