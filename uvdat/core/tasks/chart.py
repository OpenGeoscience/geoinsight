from datetime import datetime

from celery import shared_task
import pandas
from webcolors import name_to_hex

from uvdat.core.models import Chart, Context, NetworkNode


@shared_task
def convert_chart(chart_id, conversion_options):
    chart = Chart.objects.get(id=chart_id)

    label_column = conversion_options.get('labels')
    dataset_columns = conversion_options.get('datasets')
    palette_options = conversion_options.get('palette')

    chart_data = {
        'labels': [],
        'datasets': [],
    }

    chart_file = chart.fileitem_set.first()
    if chart_file.file_type == 'csv':
        raw_data = pandas.read_csv(chart_file.file.open())
    else:
        raise NotImplementedError(
            f'Convert chart data for file type {chart_file.file_type}',
        )
    chart_data['labels'] = raw_data[label_column].fillna(-1).tolist()
    chart_data['datasets'] = [
        {
            'label': dataset_column,
            'backgroundColor': name_to_hex(palette_options.get(dataset_column, 'black')),
            'borderColor': name_to_hex(palette_options.get(dataset_column, 'black')),
            'data': raw_data[dataset_column].fillna(-1).tolist(),
        }
        for dataset_column in dataset_columns
    ]

    chart.chart_data = chart_data
    chart.save()
    print(f'\t Saved converted data for chart {chart.name}.')


def get_gcc_chart(dataset, context_id):
    chart_name = f'{dataset.name} Greatest Connected Component Sizes'
    try:
        return Chart.objects.get(name=chart_name)
    except Chart.DoesNotExist:
        chart = Chart.objects.create(
            name=chart_name,
            description="""
                A set of previously-run calculations
                for the network's greatest connected component (GCC),
                showing GCC size by number of excluded nodes
            """,
            context=Context.objects.get(id=context_id),
            editable=True,
            chart_data={},
            metadata=[],
            chart_options={
                'chart_title': 'Size of Greatest Connected Component over Period',
                'x_title': 'Step when Excluded Nodes Changed',
                'y_title': 'Number of Nodes',
                'y_range': [0, NetworkNode.objects.filter(network__dataset=dataset).count()],
            },
        )
        print('\t', f'Chart {chart.name} created.')
        chart.save()
        return chart


def add_gcc_chart_datum(dataset, context_id, excluded_node_names, gcc_size):
    chart = get_gcc_chart(dataset, context_id)
    if len(chart.metadata) == 0:
        # no data exists, need to initialize data structures
        chart.metadata = []
        chart.chart_data['labels'] = []
        chart.chart_data['datasets'] = [
            {
                'label': 'GCC Size',
                'backgroundColor': name_to_hex('blue'),
                'borderColor': name_to_hex('blue'),
                'data': [],
            },
            {
                'label': 'N Nodes Excluded',
                'backgroundColor': name_to_hex('red'),
                'borderColor': name_to_hex('red'),
                'data': [],
            },
        ]

    # Append to chart_data
    labels = chart.chart_data['labels']
    datasets = chart.chart_data['datasets']

    labels.append(len(labels) + 1)  # Add x-axis entry
    datasets[0]['data'].append(gcc_size)  # Add gcc size point
    datasets[1]['data'].append(len(excluded_node_names))  # Add n excluded point

    chart.chart_data['labels'] = labels
    chart.chart_data['datasets'] = datasets

    new_entry = {
        'run_time': datetime.now().strftime('%d/%m/%Y %H:%M'),
        'n_excluded_nodes': len(excluded_node_names),
        'excluded_node_names': excluded_node_names,
        'gcc_size': gcc_size,
    }

    # Append to metadata
    chart.metadata.append(new_entry)
    chart.save()
