from celery import shared_task


def create_layers_and_frames(dataset, layer_options=None):
    from uvdat.core.models import Layer, LayerFrame, RasterData, VectorData

    Layer.objects.filter(dataset=dataset).delete()
    LayerFrame.objects.filter(layer__dataset=dataset).delete()
    vectors = VectorData.objects.filter(dataset=dataset)
    rasters = RasterData.objects.filter(dataset=dataset)

    if layer_options is None:
        layer_options = [
            dict(name=data.name.split('.')[0].replace('_', ' '), frames=None, data=data.name)
            for data in [*vectors.all(), *rasters.all()]
        ]

    for layer_info in layer_options:
        layer = Layer.objects.create(
            dataset=dataset,
            name=layer_info.get('name', dataset.name),
            metadata=layer_info.get('metadata', {}),
        )
        frames = layer_info.get('frames')
        if frames is None:
            frames = []
            kwargs = dict(dataset=dataset)
            data_name = layer_info.get('data')
            source_file_name = layer_info.get('source_file')
            if data_name is not None:
                kwargs['name'] = data_name
            if source_file_name is not None:
                kwargs['source_file__name'] = source_file_name

            for layer_data in [
                *VectorData.objects.filter(**kwargs).order_by('name').all(),
                *RasterData.objects.filter(**kwargs).order_by('name').all(),
            ]:
                frame_property = layer_info.get('frame_property')
                additional_filters = layer_info.get('additional_filters', {})
                metadata = layer_data.metadata or {}
                bands = metadata.get('bands')
                summary = layer_data.summary if hasattr(layer_data, 'summary') else {}
                properties = summary.get('properties')
                if properties and frame_property and frame_property in properties:
                    property_summary = properties.get(frame_property)
                    value_set = property_summary.get('value_set')
                    if value_set is not None:
                        for value in value_set:
                            frames.append(
                                dict(
                                    name=value,
                                    index=len(frames),
                                    data=layer_data.name,
                                    source_filters=dict(frame_property=value, **additional_filters),
                                )
                            )
                    value_range = property_summary.get('range')
                    if value_range is not None:
                        for i in range(*value_range):
                            frames.append(
                                dict(
                                    name=f'Frame {i}',
                                    index=len(frames),
                                    data=layer_data.name,
                                    source_filters=dict(frame_property=i, **additional_filters),
                                )
                            )
                elif bands and len(bands) > 1:
                    for band in bands:
                        frames.append(
                            dict(
                                name=band,
                                index=len(frames),
                                data=layer_data.name,
                                source_filters=dict(band=band),
                            )
                        )
                else:
                    frames.append(
                        dict(
                            name=layer_data.name,
                            index=len(frames),
                            data=layer_data.name,
                            source_filters={},
                        )
                    )
        for i, frame_info in enumerate(frames):
            index = frame_info.get('index', i)
            data_name = frame_info.get('data')
            if data_name:
                vector, raster = None, None
                vectors = VectorData.objects.filter(dataset=dataset, name=data_name)
                rasters = RasterData.objects.filter(dataset=dataset, name=data_name)
                if vectors.count():
                    vector = vectors.first()
                if rasters.count():
                    raster = rasters.first()
                LayerFrame.objects.create(
                    name=frame_info.get('name', f'Frame {index}'),
                    layer=layer,
                    index=index,
                    vector=vector,
                    raster=raster,
                    source_filters=frame_info.get('source_filters', dict(band=1)),
                )


@shared_task
def convert_dataset(
    dataset_id,
    layer_options=None,
    network_options=None,
    region_options=None,
    result_id=None,
):
    from uvdat.core.models import Dataset, FileItem, RasterData, TaskResult, VectorData

    from .conversion import convert_file_item
    from .data import create_vector_features
    from .networks import create_network
    from .regions import create_source_regions

    dataset = Dataset.objects.get(id=dataset_id)
    dataset.processing = True
    dataset.save()

    result = None
    if result_id:
        try:
            result = TaskResult.objects.get(id=result_id)
        except TaskResult.DoesNotExist:
            pass

    VectorData.objects.filter(dataset=dataset).delete()
    RasterData.objects.filter(dataset=dataset).delete()

    for file_to_convert in FileItem.objects.filter(dataset=dataset):
        if result is not None:
            result.write_status(f'Converting file {file_to_convert.name}...')
        convert_file_item(file_to_convert)

    vectors = VectorData.objects.filter(dataset=dataset)
    for vector_data in vectors.all():
        if result is not None:
            result.write_status(f'Processing vector data {vector_data.name}...')

        if network_options:
            create_network(vector_data, network_options)
        elif region_options:
            create_source_regions(vector_data, region_options)

        # Create vector features after geojson_data may have
        # been altered by create_network or create_source_regions
        create_vector_features(vector_data)
        vector_data.get_summary()

    create_layers_and_frames(dataset, layer_options)

    dataset.processing = False
    dataset.save()

    if result is not None:
        result.complete()
