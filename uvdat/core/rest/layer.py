import jsonschema
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet, ReadOnlyModelViewSet

from uvdat.core.models import Layer, LayerFrame, LayerStyle
from uvdat.core.rest.access_control import GuardianFilter, GuardianPermission
from uvdat.core.rest.serializers import LayerFrameSerializer, LayerSerializer, LayerStyleSerializer


class LayerViewSet(ReadOnlyModelViewSet):
    queryset = Layer.objects.select_related('dataset').all()
    serializer_class = LayerSerializer
    permission_classes = [GuardianPermission]
    filter_backends = [GuardianFilter]
    lookup_field = 'id'

    @action(detail=True, methods=['get'])
    def summary(self, request, **kwargs):
        instance = self.get_object()
        return Response(instance.get_summary(), status=200)


class LayerFrameViewSet(ReadOnlyModelViewSet):
    queryset = LayerFrame.objects.all()
    serializer_class = LayerFrameSerializer
    permission_classes = [GuardianPermission]
    filter_backends = [GuardianFilter]
    lookup_field = 'id'


class LayerStyleViewSet(ModelViewSet):
    queryset = LayerStyle.objects.all()
    serializer_class = LayerStyleSerializer
    permission_classes = [GuardianPermission]
    filter_backends = [GuardianFilter]
    lookup_field = 'id'

    def get_queryset(self):
        qs = super().get_queryset()
        project_id = int(self.request.query_params.get('project', -1))
        if project_id > -1:
            qs = qs.filter(project=int(project_id))
        layer_id = int(self.request.query_params.get('layer', -1))
        if layer_id > -1:
            qs = qs.filter(layer=int(layer_id))
        return qs

    def create(self, request, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            serializer.save()
        except jsonschema.exceptions.ValidationError as e:
            return Response(e.message, status=400)
        return Response(serializer.data, status=200)

    def partial_update(self, request, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        try:
            serializer.save()
        except jsonschema.exceptions.ValidationError as e:
            return Response(e.message, status=400)
        return Response(serializer.data, status=200)
