# Created for the GeoDatalytics Data Explorer, which uses ipyleaflet
# ipyleaflet does not support custom headers, so auth token must be sent as a URL param
from __future__ import annotations

from django.contrib.auth.models import User
from rest_framework.authentication import BaseAuthentication


class IPyLeafletTokenAuth(BaseAuthentication):
    def authenticate(self, request):
        token = request.query_params.get("token")
        if token is None:
            return None

        try:
            user = User.objects.get(auth_token=token)
        except User.DoesNotExist:
            return None

        if not user.is_active:
            return None

        return (user, token)
