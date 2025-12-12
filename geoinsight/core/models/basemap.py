from django.db import models


class Basemap(models.Model):
    name = models.CharField(max_length=100)
    style = models.JSONField()

    def __str__(self):
        return f'{self.name} ({self.id})'

    @classmethod
    def filter_queryset_by_projects(cls, queryset, projects):
        # Basemap permissions are not determined by Project permissions
        return queryset
