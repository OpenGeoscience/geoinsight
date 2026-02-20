from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from django.contrib.auth.models import User
import pooch
import pytest
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient

from .factory_fixtures import *  # noqa: F403

if TYPE_CHECKING:
    from geoinsight.core.models import Project


@pytest.fixture
def project_owner(project: Project) -> User:
    return project.owner()


@pytest.fixture
def project_collaborator(user, project: Project) -> User:
    project.add_collaborators([user])
    return user


@pytest.fixture
def project_follower(user, project: Project) -> User:
    project.add_followers([user])
    return user


USER_INFOS = [
    {
        "id": "superuser",
        "username": "userA",
        "password": "testmepassA",
        "email": "a@fakeemail.com",
        "is_superuser": True,
        "perm": None,
    },
    {
        "id": "owner",
        "username": "userB",
        "password": "testmepassB",
        "email": "b@fakeemail.com",
        "is_superuser": False,
        "perm": "owner",
    },
    {
        "id": "collaborator",
        "username": "userC",
        "password": "testmepassC",
        "email": "c@fakeemail.com",
        "is_superuser": False,
        "perm": "collaborator",
    },
    {
        "id": "follower",
        "username": "userD",
        "password": "testmepassD",
        "email": "d@fakeemail.com",
        "is_superuser": False,
        "perm": "follower",
    },
    {
        "id": "no_perms",
        "username": "userE",
        "password": "testmepassE",
        "email": "E@fakeemail.com",
        "is_superuser": False,
        "perm": None,
    },
]


@pytest.fixture
def api_client() -> APIClient:
    return APIClient()


@pytest.fixture
def authenticated_api_client(user) -> APIClient:
    client = APIClient()
    client.force_authenticate(user=user)
    return client


@pytest.fixture
def token(user) -> str:
    token, _ = Token.objects.get_or_create(user=user)
    return token.key


@pytest.fixture
def permissions_client(user_info) -> APIClient:
    user_info.pop("perm", None)
    user_info.pop("id", None)
    user = User.objects.create(**user_info)
    client = APIClient()
    client.force_authenticate(user=user)
    return (client, user)


@pytest.fixture
def multiframe_vector_file(tmp_path):
    file_info = {
        "name": "multiframe_vector.geojson",
        "file_type": "geojson",
        "content_type": "application/json",
        "url": "https://data.kitware.com/api/v1/item/6841f7e0dfcff796fee73d1a/download",
        "hash": "9c24922c9d95fd49f8fd3bafa7ed60f093ac292891a4301bac2be883eeef65ee",
    }
    pooch.retrieve(
        url=file_info["url"],
        known_hash=file_info["hash"],
        fname=file_info["name"],
        path=tmp_path,
    )
    file_info["path"] = Path(tmp_path, file_info["name"])
    return file_info
