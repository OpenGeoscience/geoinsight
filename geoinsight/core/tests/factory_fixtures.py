from __future__ import annotations

import pytest

from geoinsight.core.models import Project

from .factories import (
    DatasetFactory,
    FileItemFactory,
    LayerFactory,
    LayerFrameFactory,
    LayerStyleFactory,
    NetworkEdgeFactory,
    NetworkFactory,
    NetworkNodeFactory,
    ProjectFactory,
    RasterDataFactory,
    SuperUserFactory,
    UserFactory,
    VectorDataFactory,
)


# User
@pytest.fixture
def user_factory():
    return UserFactory


@pytest.fixture
def user(user_factory):
    return user_factory()


@pytest.fixture
def superuser_factory():
    return SuperUserFactory


@pytest.fixture
def superuser(superuser_factory):
    return superuser_factory()


# Project
@pytest.fixture
def project_factory():
    return ProjectFactory


# Ensure that when a project is created, it always has an owner
@pytest.fixture
def project(user_factory, project_factory) -> Project:
    project = project_factory()
    project.set_owner(user_factory())
    return project


# Dataset
@pytest.fixture
def dataset_factory():
    return DatasetFactory


# Ensure that when a dataset is created, it always has an owner
@pytest.fixture
def dataset(user_factory, dataset_factory):
    dataset = dataset_factory()
    dataset.set_owner(user_factory())
    return dataset


# File Item
@pytest.fixture
def file_item_factory():
    return FileItemFactory


@pytest.fixture
def file_item(file_item_factory):
    return file_item_factory()


# Network
@pytest.fixture
def network_factory():
    return NetworkFactory


@pytest.fixture
def network(network_factory):
    return network_factory()


# Network Node
@pytest.fixture
def network_node_factory():
    return NetworkNodeFactory


@pytest.fixture
def network_node(network_node_factory):
    return network_node_factory()


# Network Edge
@pytest.fixture
def network_edge_factory():
    return NetworkEdgeFactory


@pytest.fixture
def network_edge(network_edge_factory):
    return network_edge_factory()


# Raster Data
@pytest.fixture
def raster_data_factory():
    return RasterDataFactory


@pytest.fixture
def raster_data(raster_data_factory):
    return raster_data_factory()


# Vector Data
@pytest.fixture
def vector_data_factory():
    return VectorDataFactory


@pytest.fixture
def vector_data(vector_data_factory):
    return vector_data_factory()


# Layer
@pytest.fixture
def layer_factory():
    return LayerFactory


@pytest.fixture
def layer(layer_factory):
    return layer_factory()


# Layer Frame
@pytest.fixture
def layer_frame_factory():
    return LayerFrameFactory


@pytest.fixture
def layer_frame(layer_frame_factory):
    return layer_frame_factory()


# Layer Style
@pytest.fixture
def layer_style_factory():
    return LayerStyleFactory


@pytest.fixture
def layer_style(layer_style_factory):
    return layer_style_factory()
