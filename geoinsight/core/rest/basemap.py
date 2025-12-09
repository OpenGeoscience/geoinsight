import json

from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from geoinsight.core.models import Colormap
from geoinsight.core.rest.access_control import GuardianFilter, GuardianPermission
from geoinsight.core.rest.serializers import ColormapSerializer


class BasemapViewSet(ModelViewSet):
    queryset = Colormap.objects.all()
    serializer_class = ColormapSerializer
    permission_classes = [GuardianPermission]
    filter_backends = [GuardianFilter]
    lookup_field = 'id'

    def list(self, request, **kwargs):
        with open('geoinsight/core/rest/basemaps.json') as f:
            return Response(json.load(f), status=200)
