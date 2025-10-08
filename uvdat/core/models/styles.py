from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from uvdat.core.models import Colormap, Layer, Project


class LayerStyle(models.Model):
    name = models.CharField(max_length=255, default='Layer Style')
    layer = models.ForeignKey(Layer, related_name='styles', on_delete=models.CASCADE)
    project = models.ForeignKey(Project, related_name='styles', on_delete=models.CASCADE)
    default_frame = models.IntegerField(default=0, validators=[MinValueValidator(0)])
    opacity = models.DecimalField(
        default=1,
        max_digits=2,
        decimal_places=1,
        validators=[
            MinValueValidator(0),
            MaxValueValidator(1),
        ],
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['name', 'layer', 'project'], name='unique_name_layer_project'
            )
        ]

    def save_style_configs(self, style_spec):
        if style_spec is None:
            raise ValueError('style_spec must not be None.')
        color_specs = style_spec.get('colors', [])
        size_specs = style_spec.get('sizes', [])
        filter_specs = style_spec.get('filters', [])
        if not len(color_specs) or not len(size_specs):
            raise ValueError(
                'style_spec must contain at least one color '
                'configuration and one size configuration.'
            )

        color_config_names = []
        for color_spec in color_specs:
            color_config_name = color_spec.get('name')
            if color_config_name is None:
                continue
            color_config_names.append(color_config_name)
            color_config, _ = ColorConfig.objects.get_or_create(style=self, name=color_config_name)
            color_config.visible = color_spec.get('visible', True)
            single_color = color_spec.get('single_color')
            if single_color is not None:
                color_config.single_color = single_color
                try:
                    color_config.colormap.delete()
                except ColorConfig.colormap.RelatedObjectDoesNotExist:
                    pass
            else:
                color_config.single_color = None
                colormap_spec = color_spec.get('colormap')
                colormap = Colormap.objects.get(id=colormap_spec.get('id'))
                map_range = colormap_spec.get('range') or [None, None]
                colormap_config_args = dict(
                    color_config=color_config,
                    colormap=colormap,
                    color_by=colormap_spec.get('color_by'),
                    null_color=colormap_spec.get('null_color'),
                    clamp=colormap_spec.get('clamp', False),
                    discrete=colormap_spec.get('discrete', False),
                    n_colors=colormap_spec.get('n_colors'),
                    range_minimum=map_range[0],
                    range_maximum=map_range[1],
                )
                try:
                    colormap_config = color_config.colormap
                    for key, value in colormap_config_args.items():
                        setattr(colormap_config, key, value)
                    colormap_config.save()
                except ColorConfig.colormap.RelatedObjectDoesNotExist:
                    ColormapConfig.objects.create(**colormap_config_args)
            color_config.save()
        ColorConfig.objects.filter(style=self).exclude(name__in=color_config_names).delete()

        size_config_names = []
        for size_spec in size_specs:
            size_config_name = size_spec.get('name')
            if size_config_name is None:
                continue
            size_config_names.append(size_config_name)
            size_config, _ = SizeConfig.objects.get_or_create(
                style=self,
                name=size_config_name,
            )
            size_config.zoom_scaling = size_spec.get('zoom_scaling')
            single_size = size_spec.get('single_size')
            if single_size is not None:
                size_config.single_size = single_size
                try:
                    size_config.size_range.delete()
                except SizeConfig.size_range.RelatedObjectDoesNotExist:
                    pass
            else:
                size_config.single_size = None
                size_range_spec = size_spec.get('size_range')
                null_size_spec = size_range_spec.get('null_size')
                size_range_config_args = dict(
                    size_config=size_config,
                    size_by=size_range_spec.get('size_by'),
                    minimum=size_range_spec.get('minimum'),
                    maximum=size_range_spec.get('maximum'),
                    null_size=null_size_spec.get('size'),
                    null_transparent=null_size_spec.get('transparency'),
                )
                try:
                    size_range_config = size_config.size_range
                    for key, value in size_range_config_args.items():
                        setattr(size_range_config, key, value)
                    size_range_config.save()
                except SizeConfig.size_range.RelatedObjectDoesNotExist:
                    SizeRangeConfig.objects.create(**size_range_config_args)
            size_config.save()
        SizeConfig.objects.filter(style=self).exclude(name__in=size_config_names).delete()

        filter_configs = list(FilterConfig.objects.filter(style=self))
        filter_config_ids = []
        for i, filter_spec in enumerate(filter_specs):
            filter_range = filter_spec.get('range') or [None, None]
            filter_config_args = dict(
                style=self,
                filter_by=filter_spec.get('filter_by'),
                include=filter_spec.get('include'),
                transparency=filter_spec.get('transparency'),
                range_minimum=filter_range[0],
                range_maximum=filter_range[1],
                values_list=filter_spec.get('list'),
            )
            if i < len(filter_configs):
                filter_config = filter_configs[i]
            else:
                filter_config = FilterConfig.objects.create(**filter_config_args)
            filter_config.save()
            filter_config_ids.append(filter_config.id)
        FilterConfig.objects.filter(style=self).exclude(id__in=filter_config_ids).delete()

    def repr_style_configs(self):
        def serialize_fields(obj, fields):
            serialized = {}
            for field in fields:
                value = getattr(obj, field)
                if value is not None:
                    serialized[field] = value
            return serialized

        colors = []
        for color_config in ColorConfig.objects.filter(style=self):
            color = serialize_fields(color_config, ['name', 'visible', 'single_color'])
            try:
                colormap = serialize_fields(
                    color_config.colormap,
                    ['discrete', 'clamp', 'n_colors', 'color_by', 'null_color'],
                )
                colormap['id'] = color_config.colormap.colormap.id
                colormap['range'] = [
                    float(color_config.colormap.range_minimum),
                    float(color_config.colormap.range_maximum),
                ]
                color['colormap'] = colormap
            except ColorConfig.colormap.RelatedObjectDoesNotExist:
                pass
            colors.append(color)

        sizes = []
        for size_config in SizeConfig.objects.filter(style=self):
            size = serialize_fields(size_config, ['name', 'zoom_scaling', 'single_size'])
            try:
                size_range = serialize_fields(
                    size_config.size_range, ['size_by', 'minimum', 'maximum']
                )
                size_range['null_size'] = dict(
                    size=size_config.size_range.null_size,
                    transparency=size_config.size_range.null_transparent,
                )
                size['size_range'] = size_range
            except SizeConfig.size_range.RelatedObjectDoesNotExist:
                pass
            sizes.append(size)

        filters = []
        for filter_config in FilterConfig.objects.filter(style=self):
            filter_ = serialize_fields(filter_config, ['filter_by', 'include', 'transparency'])
            if filter_config.range_minimum is not None and filter_config.range_maximum is not None:
                filter_['range'] = [
                    float(filter_config.range_minimum),
                    float(filter_config.range_maximum),
                ]
            if filter_config.values_list is not None:
                filter_['list'] = filter_config.values_list
            filters.append(filter_)

        return dict(colors=colors, sizes=sizes, filters=filters)


class ColorConfig(models.Model):
    style = models.ForeignKey(LayerStyle, related_name='color_configs', on_delete=models.CASCADE)
    name = models.CharField(max_length=255)
    visible = models.BooleanField(default=True)
    single_color = models.CharField(
        max_length=12, null=True
    )  # optionally contains a color hex or 'transparent'


class ColormapConfig(models.Model):
    color_config = models.OneToOneField(
        ColorConfig,
        related_name='colormap',
        on_delete=models.CASCADE,
    )
    colormap = models.ForeignKey(
        Colormap,
        related_name='colormap_configs',
        null=True,
        on_delete=models.SET_NULL,
    )
    color_by = models.CharField(max_length=255)  # contains property name
    null_color = models.CharField(max_length=12)  # contains a color hex or 'transparent'
    clamp = models.BooleanField(default=False)
    discrete = models.BooleanField(default=False)
    n_colors = models.IntegerField(
        null=True, validators=[MinValueValidator(2), MaxValueValidator(30)]
    )
    range_minimum = models.DecimalField(max_digits=10, decimal_places=2, null=True)
    range_maximum = models.DecimalField(max_digits=10, decimal_places=2, null=True)


class SizeConfig(models.Model):
    style = models.ForeignKey(LayerStyle, related_name='size_configs', on_delete=models.CASCADE)
    name = models.CharField(max_length=255)
    zoom_scaling = models.BooleanField(default=True)
    single_size = models.IntegerField(
        default=5,
        validators=[MinValueValidator(1)],
        null=True,
    )


class SizeRangeConfig(models.Model):
    size_config = models.OneToOneField(
        SizeConfig,
        related_name='size_range',
        on_delete=models.CASCADE,
    )
    size_by = models.CharField(max_length=255)  # contains property name
    minimum = models.IntegerField(
        default=3,
        validators=[MinValueValidator(1)],
    )
    maximum = models.IntegerField(
        default=6,
        validators=[MinValueValidator(1)],
    )
    null_size = models.IntegerField(
        default=1,
        validators=[MinValueValidator(1)],
        null=True,
    )
    null_transparent = models.BooleanField(default=True)


class FilterConfig(models.Model):
    style = models.ForeignKey(LayerStyle, related_name='filter_configs', on_delete=models.CASCADE)
    filter_by = models.CharField(max_length=255)  # contains property name
    include = models.BooleanField(default=True)
    transparency = models.BooleanField(default=True)
    range_minimum = models.DecimalField(max_digits=10, decimal_places=2, null=True)
    range_maximum = models.DecimalField(max_digits=10, decimal_places=2, null=True)
    values_list = models.JSONField(null=True)
