from django.contrib.auth.models import User
from django.contrib.gis.geos import Point
from django.contrib.gis.serializers import geojson
from rest_framework import serializers

from uvdat.core.models import (
    Chart,
    Dataset,
    FileItem,
    Layer,
    LayerFrame,
    LayerStyle,
    Network,
    NetworkEdge,
    NetworkNode,
    Project,
    RasterData,
    Region,
    TaskResult,
    VectorData,
)


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'is_superuser']


class ProjectPermissionsSerializer(serializers.Serializer):
    owner_id = serializers.IntegerField()
    collaborator_ids = serializers.ListField(child=serializers.IntegerField())
    follower_ids = serializers.ListField(child=serializers.IntegerField())

    def validate(self, attrs):
        collaborators = set(attrs['collaborator_ids'])
        followers = set(attrs['follower_ids'])
        owner = attrs['owner_id']

        if collaborators & followers or owner in (collaborators | followers):
            raise serializers.ValidationError(
                'A user cannot have multiple permissions on a single project'
            )

        return super().validate(attrs)


class ProjectSerializer(serializers.ModelSerializer):
    default_map_center = serializers.SerializerMethodField('get_center')
    owner = serializers.SerializerMethodField('get_owner')
    collaborators = serializers.SerializerMethodField('get_collaborators')
    followers = serializers.SerializerMethodField('get_followers')
    item_counts = serializers.SerializerMethodField('get_item_counts')

    def get_center(self, obj):
        # Web client expects Lon, Lat
        if obj.default_map_center:
            return [obj.default_map_center.y, obj.default_map_center.x]

    def get_owner(self, obj: Project):
        return UserSerializer(obj.owner()).data

    def get_collaborators(self, obj: Project):
        return [UserSerializer(user).data for user in obj.collaborators()]

    def get_followers(self, obj: Project):
        return [UserSerializer(user).data for user in obj.followers()]

    def get_item_counts(self, obj):
        return {
            'datasets': obj.datasets.count(),
            'charts': obj.charts.count(),
            'analyses': obj.task_results.count(),
        }

    def to_internal_value(self, data):
        center = data.get('default_map_center')
        data = super().to_internal_value(data)
        if isinstance(center, list):
            data['default_map_center'] = Point(center[1], center[0])
        return data

    class Meta:
        model = Project
        fields = '__all__'


class DatasetSerializer(serializers.ModelSerializer):
    class Meta:
        model = Dataset
        fields = '__all__'


class FileItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = FileItem
        fields = '__all__'


class ChartSerializer(serializers.ModelSerializer):
    class Meta:
        model = Chart
        fields = '__all__'


class LayerStyleSerializer(serializers.ModelSerializer):
    is_default = serializers.SerializerMethodField('get_is_default')

    def get_is_default(self, obj):
        if obj.layer.default_style is None:
            return False
        return obj.layer.default_style.id == obj.id

    class Meta:
        model = LayerStyle
        fields = '__all__'


class LayerSerializer(serializers.ModelSerializer):
    default_style = LayerStyleSerializer()

    class Meta:
        model = Layer
        fields = ['id', 'name', 'metadata', 'dataset', 'default_style']


class VectorDataSerializer(serializers.ModelSerializer):
    file_size = serializers.SerializerMethodField('get_file_size')

    def get_file_size(self, obj):
        if obj.geojson_data:
            return obj.geojson_data.size
        return -1

    class Meta:
        model = VectorData
        fields = '__all__'


class RasterDataSerializer(serializers.ModelSerializer):
    file_size = serializers.SerializerMethodField('get_file_size')

    def get_file_size(self, obj):
        if obj.cloud_optimized_geotiff:
            return obj.cloud_optimized_geotiff.size
        return -1

    class Meta:
        model = RasterData
        fields = '__all__'


class LayerFrameSerializer(serializers.ModelSerializer):
    vector = VectorDataSerializer()
    raster = RasterDataSerializer()

    class Meta:
        model = LayerFrame
        fields = '__all__'


class RegionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Region
        fields = '__all__'


class RegionFeatureCollectionSerializer(geojson.Serializer):
    # Override this method to ensure the pk field is a number instead of a string
    def get_dump_object(self, obj):
        val = super().get_dump_object(obj)
        val['properties']['id'] = int(val['properties'].pop('pk'))

        return val


class NetworkNodeSerializer(serializers.ModelSerializer):
    class Meta:
        model = NetworkNode
        fields = '__all__'


class NetworkEdgeSerializer(serializers.ModelSerializer):
    class Meta:
        model = NetworkEdge
        fields = '__all__'


class NetworkSerializer(serializers.ModelSerializer):
    dataset = serializers.SerializerMethodField('get_dataset')
    nodes = serializers.PrimaryKeyRelatedField(many=True, read_only=True)
    edges = serializers.PrimaryKeyRelatedField(many=True, read_only=True)

    def get_dataset(self, obj):
        return DatasetSerializer(obj.vector_data.dataset).data

    class Meta:
        model = Network
        fields = '__all__'


class AnalysisTypeSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=255)
    db_value = serializers.CharField(max_length=25)
    description = serializers.CharField(max_length=255)
    attribution = serializers.CharField(max_length=255)
    input_options = serializers.JSONField()
    input_types = serializers.JSONField()
    output_types = serializers.JSONField()


class TaskResultSerializer(serializers.ModelSerializer):
    class Meta:
        model = TaskResult
        fields = '__all__'
