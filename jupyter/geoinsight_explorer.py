from __future__ import annotations

from urllib.parse import urlencode

from ipyleaflet import FullScreenControl, Map, TileLayer, VectorTileLayer, basemaps, projections
from IPython import display
from ipytree import Node, Tree
import ipywidgets as widgets
import requests

DEFAULT_CENTER = [42.36, -71.06]
DEFAULT_ZOOM = 14


class LayerRepresentation:
    def __init__(self, layer, api_url, session, token, center, zoom):
        self.layer = layer
        self.session = session
        self.api_url = api_url
        self.token = token
        self.center = center
        self.zoom = zoom

        self.output = widgets.Output()
        self.frame_index = 0
        self.frames = self.layer.get('frames', [])
        self.max_frame = max(frame.get('index') for frame in self.frames) if len(self.frames) else 0
        self.play_widget = widgets.Play(
            min=0,
            max=self.max_frame,
            interval=1500,
        )
        self.frame_slider = widgets.IntSlider(
            description='Frame Index:',
            min=0,
            max=self.max_frame,
        )
        widgets.jslink((self.play_widget, 'value'), (self.frame_slider, 'value'))
        label_text = 'Frame Name: '
        if len(self.frames):
            label_text += self.frames[0].get('name')
        self.frame_name_label = widgets.Label(label_text)
        self.frame_slider.observe(self.update_frame)
        self.map = Map(
            crs=projections.EPSG3857,
            basemap=basemaps.OpenStreetMap.Mapnik,
            center=self.center,
            zoom=self.zoom,
            max_zoom=20,
            min_zoom=0,
            scroll_wheel_zoom=True,
            dragging=True,
            attribution_control=False,
        )
        self.map.add(FullScreenControl())
        self.map_layers = []
        self.update_frame(dict(name='value'))

    def get_frame_path_and_metadata(self, frame):
        raster = frame.get('raster')
        vector = frame.get('vector')
        path, metadata = None, None
        if raster:
            raster_id = raster.get('id')
            path = f'rasters/{raster_id}/'
            metadata = raster.get('metadata')
        elif vector:
            vector_id = vector.get('id')
            path = f'vectors/{vector_id}/'
            metadata = vector.get('metadata')
        return path, metadata

    def get_flat_filters(self, filters):
        flat = {}
        for key, value in filters.items():
            if isinstance(value, dict):
                for k, v in self.get_flat_filters(value).items():
                    flat[f'{key}.{k}'] = v
            else:
                flat[key] = value
        return flat

    def update_frame(self, event):
        with self.output:
            if event.get('name') == 'value':
                for map_layer in self.map_layers:
                    self.map.remove_layer(map_layer)
                self.map_layers = []

                self.frame_index = int(event.get('new', 0))
                current_frames = [
                    frame for frame in self.frames if frame.get('index') == self.frame_index
                ]
                for frame in current_frames:
                    tile_size = 256
                    frame_name = frame.get('name')
                    self.frame_name_label.value = f'Frame Name: {frame_name}'
                    url_path, metadata = self.get_frame_path_and_metadata(frame)
                    if metadata is not None:
                        tile_size = metadata.get('tileWidth', 256)
                    url_suffix = 'tiles/{z}/{x}/{y}'
                    layer_class = None
                    layer_kwargs = dict(min_zoom=0, max_zoom=20, tile_size=tile_size)
                    query = dict(token=self.token)
                    source_filters = frame.get('source_filters')
                    if source_filters is not None and source_filters != dict(band=1):
                        query.update(self.get_flat_filters(source_filters))

                    if 'raster' in url_path:
                        url_suffix += '.png'
                        layer_class = TileLayer
                        query.update(projection='EPSG:3857')
                    elif 'vector' in url_path:
                        layer_class = VectorTileLayer
                    if layer_class is not None:
                        query_string = urlencode(query)
                        map_layer = layer_class(
                            url=self.api_url + url_path + url_suffix + '?' + query_string,
                            **layer_kwargs,
                        )
                        self.map_layers.append(map_layer)
                        self.map.add_layer(map_layer)

    def get_widget(self):
        children = [
            self.map,
            self.output,
        ]
        if self.max_frame:
            children = [self.frame_slider, self.play_widget, self.frame_name_label, *children]
        return widgets.VBox(children)


class GeoInsightExplorer:
    def __init__(self, api_url=None, email=None, password=None, center=None, zoom=None):
        if api_url is None:
            msg = 'GeoInsightExplorer missing argument: %s must be specified.'
            raise ValueError(msg % '`api_url`')
        if not api_url.endswith('/'):
            api_url += '/'
        self.api_url = api_url
        self.session = requests.Session()
        self.token = None
        self.authenticated = False
        self.email = email
        self.password = password
        self.center = center or DEFAULT_CENTER
        self.zoom = zoom or DEFAULT_ZOOM

        # Widgets
        self.tree = None
        self.tree_nodes = {}
        self.output = widgets.Output()
        self.email_input = widgets.Text(description='Email:')
        self.password_input = widgets.Password(description='Password:')
        self.button = widgets.Button(description='Get Datasets')
        self.button.on_click(self.get_datasets)
        children = [self.output]

        if email is None:
            children.append(self.email_input)
        if password is None:
            children.append(self.password_input)

        if email and password:
            authenticated = self.authenticate()
            if authenticated:
                children.append(widgets.Label('Session Authenticated.'))
        children.append(self.button)

        # Display
        self.display = display.display(widgets.VBox(children), display_id=True)
        self.update_display(children)

    def __del__(self):
        self.session.close()

    def authenticate(self):
        with self.output:
            self.output.clear_output()
            email = self.email or self.email_input.value
            password = self.password or self.password_input.value
            self.email_input.value = ''
            self.password_input.value = ''

            response = requests.post(
                self.api_url + 'token/',
                dict(
                    username=email,
                    password=password,
                ),
            )
            if response.status_code == 200:
                self.token = response.json().get('token')
                self.session.headers['Authorization'] = f'Token {self.token}'
                self.authenticated = True
                return True
            else:
                print('Invalid login.')
                return False

    def get_datasets(self, *args):
        with self.output:
            if not self.authenticated:
                self.authenticate()
            response = self.session.get(self.api_url + 'datasets')
            response.raise_for_status()
            datasets = response.json().get('results')

            self.tree = Tree()
            for dataset in datasets:
                node = Node(dataset.get('name'), icon='database')
                node.observe(self.get_dataset_layers, 'selected')
                self.tree_nodes[node._id] = dataset
                self.tree.add_node(node)

            children = [self.tree, self.output]
            self.update_display(children)

    def get_dataset_layers(self, event):
        with self.output:
            node = event.get('owner')
            for child in node.nodes:
                node.remove_node(child)
            node_id = node._id
            dataset = self.tree_nodes[node_id]
            dataset_id = dataset.get('id')

            response = self.session.get(self.api_url + f'datasets/{dataset_id}/layers')
            response.raise_for_status()
            layers = response.json()

            for layer in layers:
                child_node = Node(layer.get('name'), icon='file')
                child_node.observe(self.select_layer, 'selected')
                self.tree_nodes[child_node._id] = layer
                node.add_node(child_node)

    def select_layer(self, event):
        with self.output:
            node = event.get('owner')
            node_id = node._id
            layer = self.tree_nodes[node_id]

            self.map = LayerRepresentation(
                layer,
                self.api_url,
                self.session,
                self.token,
                self.center,
                self.zoom,
            )
            children = [self.tree, self.output, self.map.get_widget()]
            self.update_display(children)

    def update_display(self, children):
        self.display.update(widgets.VBox(children))

    def _ipython_display_(self):
        return self.display
