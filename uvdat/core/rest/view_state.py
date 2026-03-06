from __future__ import annotations

from rest_framework.viewsets import ModelViewSet

from uvdat.core.models import ViewState
from uvdat.core.rest.serializers import ViewStateSerializer


class ViewStateViewSet(ModelViewSet):
    queryset = ViewState.objects.all()
    serializer_class = ViewStateSerializer
