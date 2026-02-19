from __future__ import annotations

from rest_framework.viewsets import ModelViewSet

from geoinsight.core.models import Basemap
from geoinsight.core.rest.access_control import GuardianFilter, GuardianPermission
from geoinsight.core.rest.serializers import BasemapSerializer


class BasemapViewSet(ModelViewSet):
    queryset = Basemap.objects.all()
    serializer_class = BasemapSerializer
    permission_classes = [GuardianPermission]
    filter_backends = [GuardianFilter]
    lookup_field = 'id'
