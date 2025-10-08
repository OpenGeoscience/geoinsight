import pytest

from uvdat.core.models import ColorConfig, SizeConfig

SIMPLE_SPEC = dict(
    colors=[
        dict(
            name='all',
            visible=True,
            single_color='#ffffff',
        )
    ],
    sizes=[
        dict(
            name='all',
            zoom_scaling=True,
            single_size=4,
        )
    ],
    filters=[],
)

COMPLEX_SPEC = dict(
    colors=[
        dict(
            name='all',
            visible=True,
            # Discretely apply 5 colors of terrain colormap by 'depth' with range [-1.5, 1.5]
            colormap=dict(
                id=1,
                discrete=True,
                clamp=False,
                n_colors=5,
                color_by='depth',
                null_color='#000000',
                range=[-1.5, 1.5],
            ),
        )
    ],
    sizes=[
        dict(
            name='all',
            zoom_scaling=True,
            # Size features between 2 and 8 by 'magnitude' (1 if null)
            size_range=dict(
                size_by='magnitude',
                minimum=2,
                maximum=8,
                null_size=dict(
                    transparency=False,
                    size=1,
                ),
            ),
        )
    ],
    filters=[
        dict(
            # Exclude features with 'timestep' 0-10
            filter_by='timestep',
            include=False,
            transparency=True,
            range=[0, 10],
        ),
        dict(
            # Include features where 'day' is a weekend day
            filter_by='day',
            include=True,
            transparency=True,
            list=['sunday', 'saturday'],
        ),
    ],
)


@pytest.mark.django_db
def test_style_config_none(layer_style):
    with pytest.raises(ValueError, match='style_spec must not be None.'):
        layer_style.save_style_configs(None)


@pytest.mark.django_db
def test_style_config_empty(layer_style):
    with pytest.raises(
        ValueError,
        match=(
            'style_spec must contain at least one '
            'color configuration and one size configuration.'
        ),
    ):
        layer_style.save_style_configs({})


@pytest.mark.django_db
def test_style_config_update(layer_style):
    # Initialize simple style and verify related objects
    layer_style.save_style_configs(SIMPLE_SPEC)
    assert layer_style.repr_style_configs() == SIMPLE_SPEC
    color_configs = layer_style.color_configs.all()
    assert color_configs.count() == 1
    color_config_id = color_configs.first().id
    size_configs = layer_style.size_configs.all()
    assert size_configs.count() == 1
    size_config_id = size_configs.first().id
    assert layer_style.filter_configs.count() == 0

    # Update to complex style and verify same objects modified and new related objects created
    layer_style.save_style_configs(COMPLEX_SPEC)
    assert layer_style.repr_style_configs() == COMPLEX_SPEC
    color_config = layer_style.color_configs.first()
    assert color_config.id == color_config_id
    assert color_config.colormap
    size_config = layer_style.size_configs.first()
    assert size_config.id == size_config_id
    assert size_config.size_range
    assert layer_style.filter_configs.count() == 2

    # Set back to simple style and verify extra objects deleted
    layer_style.save_style_configs(SIMPLE_SPEC)
    assert layer_style.repr_style_configs() == SIMPLE_SPEC
    color_config = layer_style.color_configs.first()
    assert color_config.id == color_config_id
    with pytest.raises(ColorConfig.colormap.RelatedObjectDoesNotExist):
        color_config.colormap
    size_config = layer_style.size_configs.first()
    assert size_config.id == size_config_id
    with pytest.raises(SizeConfig.size_range.RelatedObjectDoesNotExist):
        size_config.size_range
    assert layer_style.filter_configs.count() == 0


@pytest.mark.django_db
def test_rest_style_create_and_update(authenticated_api_client, layer, project, user):
    project.set_collaborators([user])
    project.datasets.set([layer.dataset])

    style = dict(
        name='Test Style',
        layer=layer.id,
        project=project.id,
        default_frame=1,
        opacity=0.5,
    )

    # Create style with simple spec
    style['style_spec'] = SIMPLE_SPEC
    resp = authenticated_api_client.post('/api/v1/layer-styles/', style)
    assert resp.status_code == 200
    serialized_result = resp.json()
    style_id = serialized_result.pop('id')
    assert serialized_result.pop('is_default') is not None
    assert serialized_result == style

    # Update style with complex spec
    style['style_spec'] = COMPLEX_SPEC
    resp = authenticated_api_client.patch(f'/api/v1/layer-styles/{style_id}/', style)
    assert resp.status_code == 200
    serialized_result = resp.json()
    assert serialized_result.pop('id') is not None
    assert serialized_result.pop('is_default') is not None
    assert serialized_result == style
