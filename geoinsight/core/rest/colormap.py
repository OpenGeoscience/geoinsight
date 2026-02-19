from __future__ import annotations

from rest_framework.viewsets import ModelViewSet

from geoinsight.core.models import Colormap
from geoinsight.core.rest.access_control import GuardianFilter, GuardianPermission
from geoinsight.core.rest.serializers import ColormapSerializer


class ColormapViewSet(ModelViewSet):
    queryset = Colormap.objects.all()
    serializer_class = ColormapSerializer
    permission_classes = [GuardianPermission]
    filter_backends = [GuardianFilter]
    lookup_field = 'id'
