from django.conf import settings
from django.contrib import admin
from django.urls import include, path
from django.views.generic.base import RedirectView
from drf_yasg import openapi
from drf_yasg.views import get_schema_view
from rest_framework import permissions, routers

from uvdat.core.rest import (
    ChartViewSet,
    DatasetViewSet,
    LayerFrameViewSet,
    LayerViewSet,
    ProjectViewSet,
    RasterDataViewSet,
    RegionViewSet,
    SimulationViewSet,
    UserViewSet,
    VectorDataViewSet,
)

router = routers.SimpleRouter()
# OpenAPI generation
schema_view = get_schema_view(
    openapi.Info(title='UVDAT', default_version='v1', description=''),
    public=True,
    permission_classes=(permissions.AllowAny,),
)

router.register(r'users', UserViewSet, basename='users')
router.register(r'projects', ProjectViewSet, basename='projects')
router.register(r'datasets', DatasetViewSet, basename='datasets')
router.register(r'charts', ChartViewSet, basename='charts')
router.register(r'layers', LayerViewSet, basename='layers')
router.register(r'layer-frames', LayerFrameViewSet, basename='layer-frames')
router.register(r'rasters', RasterDataViewSet, basename='rasters')
router.register(r'vectors', VectorDataViewSet, basename='vectors')
router.register(r'source-regions', RegionViewSet, basename='source-regions')
router.register(r'simulations', SimulationViewSet, basename='simulations')

urlpatterns = [
    path('accounts/', include('allauth.urls')),
    path('oauth/', include('oauth2_provider.urls')),
    path('admin/', admin.site.urls),
    path('api/v1/s3-upload/', include('s3_file_field.urls')),
    path('api/v1/', include(router.urls)),
    path('api/docs/redoc/', schema_view.with_ui('redoc'), name='docs-redoc'),
    path('api/docs/swagger/', schema_view.with_ui('swagger'), name='docs-swagger'),
    # Redirect all other server requests to Vue client
    path('', RedirectView.as_view(url=settings.HOMEPAGE_REDIRECT_URL)),  # type: ignore
]

if settings.DEBUG:
    import debug_toolbar

    urlpatterns = [path('__debug__/', include(debug_toolbar.urls))] + urlpatterns
