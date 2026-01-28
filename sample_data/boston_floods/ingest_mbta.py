import json

from geoinsight.core.models import VectorFeature

LINE_COLORS = {
    'RED': '#D31414',
    'GREEN': '#188A00',
    'BLUE': '#1F63AC',
    'ORANGE': '#D88901',
    'SILVER': '#7B8B86',
}


def convert_dataset(dataset, options):
    # Run standard conversion task first
    dataset.spawn_conversion_task(
        layer_options=options.get('layers'),
        network_options=options.get('network_options'),
        region_options=options.get('region_options'),
        asynchronous=False,
    )

    # Post-processing
    # For each associated vector feature, add style properties
    # To color features by the LINE property
    for feature in VectorFeature.objects.filter(vector_data__dataset=dataset):
        lines = feature.properties.get('LINE', '').split('/')
        colors = [LINE_COLORS[line] for line in lines if line in LINE_COLORS]
        if len(colors):
            fill = colors[0]
            stroke = colors[1] if len(colors) > 1 else fill
            default_style = {
                'fill': fill,
                'stroke': stroke,
            }
            feature.properties = feature.properties | default_style
            feature.save()
