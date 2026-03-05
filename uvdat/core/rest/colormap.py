from __future__ import annotations

from rest_framework.viewsets import ModelViewSet

from uvdat.core.models import Colormap
from uvdat.core.rest.serializers import ColormapSerializer


class ColormapViewSet(ModelViewSet):
    queryset = Colormap.objects.all()
    serializer_class = ColormapSerializer
