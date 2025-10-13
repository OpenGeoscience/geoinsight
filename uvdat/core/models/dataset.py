import typing

from django.contrib.auth.models import User
from django.db import models, transaction
from guardian.models import UserObjectPermission
from guardian.shortcuts import assign_perm, get_users_with_perms

from uvdat.core.tasks.dataset import convert_dataset


class DatasetTag(models.Model):
    tag = models.CharField(max_length=255, unique=True)

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

    def owner(self) -> User:
        users = typing.cast(
            list[User], list(get_users_with_perms(self, only_with_perms_in=['owner']))
        )
        if len(users) != 1:
            return None
        return users[0]

    @transaction.atomic()
    def set_owner(self, user: User):
        filters = dict(
            content_type__app_label=self._meta.app_label,
            content_type__model=self._meta.model_name,
            object_pk=self.pk,
        )

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

    def spawn_conversion_task(
        self,
        layer_options=None,
        network_options=None,
        region_options=None,
        asynchronous=True,
    ):
        if asynchronous:
            from uvdat.core.models.task_result import TaskResult

            result = TaskResult.objects.create(
                name=f'Conversion of Dataset {self.name}',
                task_type='conversion',
                inputs=dict(
                    dataset_id=self.id,
                    layer_options=layer_options,
                    network_options=network_options,
                    region_options=region_options,
                ),
                status='Initializing task...',
            )
            convert_dataset.delay(
                self.id, layer_options, network_options, region_options, result.id
            )
            return result
        else:
            convert_dataset(self.id, layer_options, network_options, region_options)

    def get_size(self):
        from uvdat.core.models import FileItem

        size = 0
        for file_item in FileItem.objects.filter(dataset=self):
            if file_item.file_size is not None:
                size += file_item.file_size
        return size

    def get_networks(self):
        from uvdat.core.models import Network

        return Network.objects.filter(vector_data__dataset=self)

    def get_regions(self):
        from uvdat.core.models import Region

        return Region.objects.filter(dataset=self)
