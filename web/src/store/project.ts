import {
    getProjects,
    getProjectDatasets,
    getDatasetTags,
    getDatasets,
    getView,
    getProjectViews,
    getLayer,
} from '@/api/rest';
import { Dataset, Project, View } from '@/types';
import { defineStore } from 'pinia';
import { ref, watch } from 'vue';
import { useRoute, useRouter } from 'vue-router';

import {
    useNetworkStore,
    useMapStore,
    useLayerStore,
    useAnalysisStore,
    usePanelStore,
    useAppStore,
    useStyleStore,
} from '.';

export const useProjectStore = defineStore('project', () => {
    const networkStore = useNetworkStore();
    const analysisStore = useAnalysisStore();
    const mapStore = useMapStore();
    const layerStore = useLayerStore();
    const panelStore = usePanelStore();
    const appStore = useAppStore();
    const styleStore = useStyleStore();

    const route = useRoute();
    const router = useRouter();

    const loadingProjects = ref<boolean>(true);
    const availableProjects = ref<Project[]>([]);
    const currentProject = ref<Project>();
    const projectConfigMode = ref<"new" | "existing">();
    const loadingDatasets = ref<boolean>(false);
    const allDatasets = ref<Dataset[]>();
    const availableDatasets = ref<Dataset[]>();
    const availableDatasetTags = ref<string[]>([]);
    const availableViews = ref<View[]>([]);
    const currentView = ref<View>();
    const currentViewLoaded = ref<boolean>(false);

    function fetchProjectDatasets() {
        if (!currentProject.value) { return; }

        loadingDatasets.value = true;
        getProjectDatasets(currentProject.value.id).then(async (datasets) => {
            availableDatasets.value = datasets;
            loadingDatasets.value = false;
        });
    }

    function fetchAvailableDatasetTags() {
        getDatasetTags().then((tags) => availableDatasetTags.value = tags)
    }

        function fetchProjectViews() {
        if (!currentProject.value) { return; }

        getProjectViews(currentProject.value.id).then((views) => {
            availableViews.value = views;
        });
    }

    function getCurrentView(): View | undefined {
        if (!currentProject.value) return undefined;
        const mapPosition = mapStore.getCurrentMapPosition();
        // use proportions instead of coordinates
        // so that the view looks good with other window sizes
        const panelArrangement = panelStore.panelArrangement.map((panelConfig => {
            const copyConfig = { ...panelConfig }
            delete copyConfig.element
            if (copyConfig.position) {
              copyConfig.position = {
                x: copyConfig.position.x / window.innerWidth,
                y: copyConfig.position.y / window.innerHeight,
              }
            }
            return copyConfig
        }))
        const view: View = {
          project: currentProject.value.id,
          current_analysis_type: analysisStore.currentAnalysisType?.db_value,
          current_result: analysisStore.currentResult?.id,
          current_chart: analysisStore.currentChart?.id,
          current_basemap: mapStore.currentBasemap?.id,
          current_network: networkStore.currentNetwork?.id,
          selected_layers: layerStore.selectedLayers.map((layer) => layer.id),
          selected_layer_current_frames: Object.fromEntries(
            layerStore.selectedLayers.map((layer) => {
              const styleKey = mapStore.uniqueLayerIdFromLayer(layer);
              return [styleKey, layer.current_frame_index]
            })
          ),
          selected_layer_order: layerStore.selectedLayers.map((layer) => {
            // Includes layer ID and copy ID
            return mapStore.uniqueLayerIdFromLayer(layer);
          }),
          selected_layer_styles: styleStore.selectedLayerStyles,
          left_sidebar_open: appStore.openSidebars.includes('left'),
          right_sidebar_open: appStore.openSidebars.includes('right'),
          panel_arrangement: panelArrangement,
          theme: appStore.theme,
          map_center: mapPosition.center,
          map_zoom: Math.round(mapPosition.zoom),
        }
        return view;
    }

    function navigateToView(view: View) {
        currentViewLoaded.value = false;
        router.push(`/view/${view.id}`);
    }

    watch(() => route?.fullPath, loadViewFromURL);
    function loadViewFromURL() {
        if (!route.path.includes('/view/')) {
            currentView.value = undefined;
            return;
        };
        const viewId = parseInt(route.path.split('/view/')[1]);
        getView(viewId).then((view) => {
            if (view) {
                currentView.value = view;
                // Set some state attrs that don't require the project to be loaded first
                panelStore.panelArrangement = view.panel_arrangement.map((panelConfig) => {
                  if (panelConfig.position) {
                    panelConfig.position = {
                      x: panelConfig.position.x * window.innerWidth,
                      y: panelConfig.position.y * window.innerHeight,
                    }
                  }
                  return panelConfig;
                });
                appStore.openSidebars = []
                if (view.left_sidebar_open) appStore.openSidebars.push('left');
                if (view.right_sidebar_open) appStore.openSidebars.push('right');

                const selectedProject = availableProjects.value.find((p) => p.id === view.project);
                if (currentProject.value?.id !== selectedProject?.id) {
                    currentProject.value = selectedProject;
                    // Remaining state attrs that depend on project loading will be set by the currentProject watcher
                } else {
                    if (mapStore.map) mapStore.clearMapLayers();
                    finishLoadingView();
                }
            }
        })
    }
    async function finishLoadingView() {
        const view = currentView.value;
        if (view && !currentViewLoaded.value && mapStore.map) {
            appStore.theme = view.theme;
            analysisStore.currentAnalysisType = analysisStore.availableAnalysisTypes?.find((a) => a.db_value === view.current_analysis_type);
            if (analysisStore.currentAnalysisType && currentProject.value) {
              await analysisStore.initResults(
                analysisStore.currentAnalysisType.db_value, currentProject.value.id,
              )
              analysisStore.currentResult = analysisStore.availableResults?.find((c) => c.id === view.current_result);
              if (analysisStore.currentResult) {
                analysisStore.currentAnalysisTab = 'old'
              }
            }
            analysisStore.currentChart = analysisStore.availableCharts?.find((c) => c.id === view.current_chart);
            networkStore.currentNetwork = networkStore.availableNetworks.find((n) => n.id === view.current_network);

            // @ts-ignore for "Type instantiation is excessively deep and possibly infinite"
            mapStore.currentBasemap = mapStore.availableBasemaps?.find((b) => b.id === view.current_basemap);
            mapStore.setMapPosition(view.map_center as [number, number], view.map_zoom)

            // Add layers with copy ids from selected_layer_styles
            layerStore.selectedLayers = []
            await Promise.all(Object.keys(view.selected_layer_styles).map(async (styleKey) => {
                // Parse the style key to get layer id and copy_id
                const [layerIdStr, copyIdStr] = styleKey.split('.');
                const layerId = parseInt(layerIdStr);
                const copyId = parseInt(copyIdStr);
                const layer = await getLayer(layerId);
                await layerStore.addLayer(layer, copyId);
            }))
            // Ensure correct layer order
            layerStore.selectedLayers = layerStore.selectedLayers.sort((layer1, layer2) => {
              const key1 = mapStore.uniqueLayerIdFromLayer(layer1);
              const key2 = mapStore.uniqueLayerIdFromLayer(layer2);
              return view.selected_layer_order.indexOf(key1) - view.selected_layer_order.indexOf(key2)
            })
            // Ensure correct current frames
            layerStore.selectedLayers = layerStore.selectedLayers.map((layer) => {
              const styleKey = mapStore.uniqueLayerIdFromLayer(layer);
              if (view.selected_layer_current_frames[styleKey]) {
                layer.current_frame_index = view.selected_layer_current_frames[styleKey];
              }
              return layer;
            })
            styleStore.selectedLayerStyles = view.selected_layer_styles;
            currentViewLoaded.value = true;
        }
    }

    watch(currentProject, async () => {
        clearProjectState();

        if (currentView.value) {
          mapStore.setMapPosition(
            currentView.value.map_center as [number, number],
            currentView.value.map_zoom,
            true,
          )
        } else {
          mapStore.resetMapPosition(currentProject.value);
        }

        mapStore.clearMapLayers();
        styleStore.fetchColormaps();

        if (currentProject.value) {
            fetchProjectDatasets();
            fetchProjectViews();
            await analysisStore.initCharts(currentProject.value.id);
            await analysisStore.initAnalysisTypes(currentProject.value.id);
            await networkStore.initNetworks(currentProject.value.id);
            finishLoadingView();
        }
    });

    function clearState() {
        clearProjectState();
        mapStore.setBasemapToDefault();
        appStore.currentError = undefined;

        panelStore.resetPanels();
        panelStore.draggingPanel = undefined;
        panelStore.draggingFrom = undefined;
        panelStore.dragModes = [];
    }

    function clearProjectState() {
        availableDatasets.value = undefined;

        layerStore.selectedLayers = [];
        styleStore.selectedLayerStyles = {};

        mapStore.clickedFeature = undefined;

        networkStore.availableNetworks = [];

        analysisStore.availableCharts = undefined;
        analysisStore.currentChart = undefined;
        analysisStore.availableAnalysisTypes = undefined;
        analysisStore.currentAnalysisType = undefined;
    }

    function refreshAllDatasets() {
        getDatasets().then(async (datasets) => {
            allDatasets.value = datasets
        })
    }

    watch(projectConfigMode, loadProjects);
    function loadProjects() {
        clearState();
        getProjects().then((data) => {
            availableProjects.value = data;
            loadingProjects.value = false;
        });
    }

    return {
        loadingProjects,
        availableProjects,
        currentProject,
        projectConfigMode,
        loadingDatasets,
        allDatasets,
        availableDatasets,
        availableDatasetTags,
        availableViews,
        fetchProjectDatasets,
        fetchAvailableDatasetTags,
        fetchProjectViews,
        getCurrentView,
        navigateToView,
        loadViewFromURL,
        clearState,
        clearProjectState,
        refreshAllDatasets,
        loadProjects,
    }
});
