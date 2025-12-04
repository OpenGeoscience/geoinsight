import {
    getProjects,
    getProjectDatasets,
    getDatasetTags,
    getDatasets,
} from '@/api/rest';
import { Dataset, Project } from '@/types';
import { defineStore } from 'pinia';
import { ref, watch } from 'vue';

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

    const loadingProjects = ref<boolean>(true);
    const availableProjects = ref<Project[]>([]);
    const currentProject = ref<Project>();
    const projectConfigMode = ref<"new" | "existing">();
    const loadingDatasets = ref<boolean>(false);
    const allDatasets = ref<Dataset[]>();
    const availableDatasets = ref<Dataset[]>();
    const availableDatasetTags = ref<string[]>([]);

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

    watch(currentProject, () => {
        clearProjectState();
        mapStore.setMapCenter(currentProject.value);
        mapStore.clearMapLayers();
        styleStore.fetchColormaps();

        if (currentProject.value) {
            fetchProjectDatasets();
            analysisStore.initCharts(currentProject.value.id);
            analysisStore.initAnalysisTypes(currentProject.value.id);
            networkStore.initNetworks(currentProject.value.id);
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
        fetchProjectDatasets,
        fetchAvailableDatasetTags,
        clearState,
        clearProjectState,
        refreshAllDatasets,
        loadProjects,
    }
});
