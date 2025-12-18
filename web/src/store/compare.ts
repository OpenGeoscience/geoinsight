import { defineStore } from 'pinia';
import { computed, ref, watch } from 'vue';
import { useLayerStore } from './layer';
import { cloneDeep, map } from 'lodash';
import { useMapStore } from './map';
import { MapLayerStyleRaw } from './style';
import { LayerStyle } from '@/types';
import { SourceSpecification } from 'maplibre-gl';

interface DisplayCompareMapLayerItem {
    displayName: string;
    state: boolean;
    layerIds: string[];
}

interface DisplayCompareMapLayer {
    mapLayerA: DisplayCompareMapLayerItem[];
    mapLayerB: DisplayCompareMapLayerItem[];
}

export interface MapStats {
    center: [number, number];
    zoom: number;
    bearing: number;
    pitch: number;
}



export const useMapCompareStore = defineStore('mapCompare', () => {
    const mapStore = useMapStore();
    const layerStore = useLayerStore();
    const isComparing = ref<boolean>(false);
    const mapLayersA = ref<string[]>([]);
    const mapLayersB = ref<string[]>([]);
    const orientation = ref<'horizontal' | 'vertical'>('vertical');
    const displayLayers = ref<DisplayCompareMapLayer>({
        mapLayerA: [],
        mapLayerB: [],
    });
    const mapStats = ref<MapStats>({
        center: [0,0],
        zoom: 0,
        bearing: 0,
        pitch: 0,
    });
    const sliderEnd = ref<{percentage: number, position: number}>({ percentage: 0, position: 0 });
    const mapAStyle = ref<ReturnType<maplibregl.Map['getStyle']> | undefined>(undefined);
    const mapBStyle = ref<ReturnType<maplibregl.Map['getStyle']> | undefined>(undefined);
    const compareLayerStyles = ref<{
        A: Record<string, {style: LayerStyle, opacity: number}>,
        B: Record<string, {style: LayerStyle, opacity: number}>,
    }>({
        A: {},
        B: {},
    });
    

    const initializeComparing = () => {
        const map = mapStore.getMap();
        const style = map.getStyle();
        mapStats.value = {
            center: map.getCenter().toArray() as [number, number],
            zoom: map.getZoom() as number,
            bearing: map.getBearing() as number,
            pitch: map.getPitch() as number,
        };
        mapAStyle.value = cloneDeep(style);
        mapBStyle.value = cloneDeep(style);
        generateDisplayLayers();
    }

    const generateDisplayLayers = () => {
        const localDisplayLayers: DisplayCompareMapLayer = {
            mapLayerA: [],
            mapLayerB: [],
        };
        layerStore.selectedLayers.forEach(layer => {
            const layerIds = layerStore.getMapLayersFromLayerObject(layer).flat();
            // Preserve existing visibility state if it exists, otherwise use layer.visible
            const existingLayerA = displayLayers.value.mapLayerA.find((l) => l.displayName === layer.name);
            const existingLayerB = displayLayers.value.mapLayerB.find((l) => l.displayName === layer.name);
            const layerItemA: DisplayCompareMapLayerItem = {
                displayName: layer.name,
                state: existingLayerA?.state ?? layer.visible,
                layerIds: [...layerIds]
            };
            const layerItemB: DisplayCompareMapLayerItem = {
                displayName: layer.name,
                state: existingLayerB?.state ?? layer.visible,
                layerIds: [...layerIds]
            };
            localDisplayLayers.mapLayerA.push(layerItemA);
            localDisplayLayers.mapLayerB.push(layerItemB);
        });
        displayLayers.value = localDisplayLayers;
    };


    const setAllVisibility = (map: 'A' | 'B', visible=true) => {
        const copyLayers = cloneDeep(displayLayers.value);
        const layerItems = (map === 'A' ? copyLayers.mapLayerA : copyLayers.mapLayerB);
        layerItems.forEach((layer) => {
            layer.state = visible;
        });
        displayLayers.value = copyLayers;
    }

    const setVisibility = (map: 'A' | 'B', displayName: string, visible=true) => {
        const copyLayers = cloneDeep(displayLayers.value);
        const layerItems = (map === 'A' ? copyLayers.mapLayerA : copyLayers.mapLayerB);
        const layerItemIndex = layerItems.findIndex((l) => l.displayName === displayName);
        if (layerItemIndex !== -1) {
            layerItems[layerItemIndex].state = visible;
        }
        displayLayers.value = copyLayers;
    };
    function updateMapStats(event: { center: [number, number], zoom: number, bearing: number, pitch: number }) {
        mapStats.value.center = event.center;
        mapStats.value.zoom = event.zoom;
        mapStats.value.bearing = event.bearing;
        mapStats.value.pitch = event.pitch;  
    }
    function updateSlider(event: { percentage: number, position: number }) {
        sliderEnd.value = event;
    }

    const updateMapLayerStyle = (map: 'A' | 'B', mapLayerId: string, style: MapLayerStyleRaw) => {
        const mapStyle = map === 'A' ? mapAStyle.value : mapBStyle.value;
        if (!mapStyle) return;
        const sources = new Set<string>();
        mapStyle.layers.forEach((layer: any) => {
            if (layer.id === mapLayerId) {
                layer.paint = style.paint;
                if (layer.layout) layer.layout['visibility'] =  style.visibility;
                sources.add(layer.source);
            }
        });
        if (style.tileURL && sources.size > 0) {
            sources.forEach((sourceId) => {
                if (mapStyle.sources[sourceId] && mapStyle.sources[sourceId].type === 'raster' && style.tileURL) {
                    mapStyle.sources[sourceId].tiles = [style.tileURL];
                }
            });
        }
    }

    const updateCompareLayersList = (mapType: 'A' | 'B') => {
        const mapDisplayLayers = mapType === 'A' ? displayLayers.value.mapLayerA : displayLayers.value.mapLayerB;
        const flatList: string[] = [];
        if (!mapStore.map) {
            return flatList;
        }
        const baseLayerSourceIds = mapStore.getBaseLayerIds().reverse();
        layerStore.selectedLayers.forEach((layer) => {
            if (mapDisplayLayers.find((l) => l.displayName === layer.name)?.state === false) {
                return;
            }
            const mapLayerIds = layerStore.getMapLayersFromLayerObject(layer);
            flatList.push(...(mapLayerIds.reverse()));
        });
        if (mapStore.currentBasemap?.name !== 'None') {
            baseLayerSourceIds.forEach((sourceId: string) => {
                if (sourceId) {
                    flatList.push(sourceId);
                }
            });
        }
        return flatList;
    }

    watch(displayLayers, () => {
        if (isComparing.value) {
            mapLayersA.value = updateCompareLayersList('A');
            mapLayersB.value = updateCompareLayersList('B');
        }
    }, { deep: true, immediate: true });

    watch(isComparing, (newVal) => {
        if (newVal) {
            initializeComparing();
        }
    }); 

    function updateCompareLayerStyle() {
        const compareMapAddedSources: {sourceId: string, sourceType: SourceSpecification['type']}[] = [];
        if (isComparing.value) {
            // We only need to update layers and sources that are added or removed
            const newStyle = mapStore.getMap()?.getStyle();
            if (newStyle && mapAStyle.value && mapBStyle.value) {
                // find if there are new sources
                const existingSourcesA = new Set<string>();
                mapAStyle.value?.sources && Object.keys(mapAStyle.value.sources).forEach((sourceId) => {
                    existingSourcesA.add(sourceId);
                });
                const existingSourcesB = new Set<string>();
                mapBStyle.value?.sources && Object.keys(mapBStyle.value.sources).forEach((sourceId) => {
                    existingSourcesB.add(sourceId);
                });
                Object.keys(newStyle.sources).forEach((sourceId) => {
                    if (!existingSourcesA.has(sourceId)) {
                        // New source found, add to both styles
                        if (mapAStyle.value) {
                            mapAStyle.value.sources[sourceId] = cloneDeep(newStyle.sources[sourceId]);
                        }
                    } else if (!existingSourcesB.has(sourceId)) {
                        if (mapBStyle.value) {
                            mapBStyle.value.sources[sourceId] = cloneDeep(newStyle.sources[sourceId]);
                            compareMapAddedSources.push({ sourceId, sourceType: newStyle.sources[sourceId].type });
                        }
                    }
                });
                // find if there are removed sources
                const newSources = new Set<string>();
                Object.keys(newStyle.sources).forEach((sourceId) => {
                    newSources.add(sourceId);
                });
                existingSourcesA.forEach((sourceId) => {
                    if (!newSources.has(sourceId)) {
                        // Source removed, remove from both styles
                        if (mapAStyle.value && mapAStyle.value.sources[sourceId]) {
                            delete mapAStyle.value.sources[sourceId];
                        }
                    }
                });
                existingSourcesB.forEach((sourceId) => {
                    if (!newSources.has(sourceId)) {
                        // Source removed, remove from both styles
                        if (mapBStyle.value && mapBStyle.value.sources[sourceId]) {
                            delete mapBStyle.value.sources[sourceId];
                        }
                    }
                });
                // Now we do the same for layers
                const existingLayerIdsA = new Set<string>();
                mapAStyle.value?.layers.forEach((layer: any) => {
                    existingLayerIdsA.add(layer.id);
                });
                const existingLayerIdsB = new Set<string>();
                mapBStyle.value?.layers.forEach((layer: any) => {
                    existingLayerIdsB.add(layer.id);
                });
                newStyle.layers.forEach((layer: any) => {
                    if (!existingLayerIdsA.has(layer.id)) {
                        // New layer found, add to both styles
                        if (mapAStyle.value) {
                            mapAStyle.value.layers.push(cloneDeep(layer));
                        }
                    } else if (!existingLayerIdsB.has(layer.id)) {
                        if (mapBStyle.value) {
                            mapBStyle.value.layers.push(cloneDeep(layer));
                        }
                    }
                });
                const newLayerIds = new Set<string>();
                newStyle.layers.forEach((layer: any) => {
                    newLayerIds.add(layer.id);
                });
                // find removed layers
                existingLayerIdsA.forEach((layerId) => {
                    if (!newLayerIds.has(layerId)) {
                        // Layer removed, remove from both styles
                        if (mapAStyle.value) {
                            mapAStyle.value.layers = mapAStyle.value.layers.filter((layer: any) => layer.id !== layerId);
                        }
                    }
                });
                existingLayerIdsB.forEach((layerId) => {
                    if (!newLayerIds.has(layerId)) {
                        // Layer removed, remove from both styles   
                        if (mapBStyle.value) {
                            mapBStyle.value.layers = mapBStyle.value.layers.filter((layer: any) => layer.id !== layerId);
                        }
                    }
                });
            } else {
                mapAStyle.value = mapStore.getMap()?.getStyle();
                mapBStyle.value = mapStore.getMap()?.getStyle();
            }
            generateDisplayLayers();
        }
        return compareMapAddedSources;
    }

    watch([() => layerStore.selectedLayers, () => mapStore.currentBasemap], async () => {
        const compareMapAddedSources = updateCompareLayerStyle();
        // Any new sources we need to add click handlers for
        compareMapAddedSources.forEach(({ sourceId, sourceType }) => {
            if (isComparing.value && mapStore.compareMap) {
                if (sourceType === 'vector') {
                    mapStore.compareMap.on("click", sourceId + '.fill', mapStore.handleCompareLayerClick);
                    mapStore.compareMap.on("click", sourceId + '.line', mapStore.handleCompareLayerClick);
                    mapStore.compareMap.on("click", sourceId + '.circle', mapStore.handleCompareLayerClick);
                } 
            }
        });
    }, { deep: true });

    return {
        isComparing,
        orientation,
        displayLayers,
        mapStats,
        sliderEnd,
        setVisibility,
        setAllVisibility,
        generateDisplayLayers,
        updateCompareLayersList,
        updateMapStats,
        updateSlider,
        updateMapLayerStyle,
        updateCompareLayerStyle,
        compareLayerStyles,
        mapAStyle,
        mapBStyle,
        mapLayersA,
        mapLayersB,
    }
});
