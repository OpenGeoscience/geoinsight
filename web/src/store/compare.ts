import { defineStore } from 'pinia';
import { computed, ref, watch } from 'vue';
import { useLayerStore } from './layer';
import { cloneDeep } from 'lodash';
import { useMapStore } from './map';
import { MapLayerStyleRaw } from './style';
import { LayerStyle } from '@/types';

interface DisplayCompareMapLayerItem {
    displayName: string;
    state: boolean;
    layerIds: string[];
}

interface DisplaycompareMapLayer {
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
    const orientation = ref<'horizontal' | 'vertical'>('vertical');
    const displayLayers = ref<DisplaycompareMapLayer>({
        mapLayerA: [],
        mapLayerB: [],
    });
    const mapStats = ref<MapStats>({
        center: [0,0],
        zoom: 0,
        bearing: 0,
        pitch: 0,
    });
    const mapAStyle = ref<ReturnType<maplibregl.Map['getStyle']> | undefined>(undefined);
    const mapBStyle = ref<ReturnType<maplibregl.Map['getStyle']> | undefined>(undefined);
    const compareLayerStyles = ref<{
        A: Record<string, LayerStyle>,
        B :Record<string, LayerStyle>,
    }>({
        A: {},
        B: {},
    });
    

    const initlizeComparing = () => {
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
        const localDisplayLayers: DisplaycompareMapLayer = {
            mapLayerA: [],
            mapLayerB: [],
        };
        layerStore.selectedLayers.forEach(layer => {
            const layerIds = layerStore.getMapLayersFromLayerObject(layer).flat();
            const layerItemA: DisplayCompareMapLayerItem = {
                displayName: layer.name,
                state: layer.visible,
                layerIds: [...layerIds]
            };
            const layerItemB: DisplayCompareMapLayerItem = {
                displayName: layer.name,
                state: layer.visible,
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

    const getBaseLayerSourceIds = () => {
        const map = mapStore.getMap();
        if (!map) return [];
        return map.getStyle().layers.filter((layer: any) => {
            const layerWithSource = layer as { source?: string };
            return layerWithSource.source?.includes('openstreetmap');
        }).map((layer: any) => layer.id);
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

    // Array of Enabled map layer IDs for Map A in order
    const mapLayersA = computed(() => {
        const flatList: string[] = [];
        if (!mapStore.map) {
            return flatList;
        }
        const baseLayerSourceIds = getBaseLayerSourceIds().reverse();
        
        layerStore.selectedLayers.forEach((layer) => {
            if (displayLayers.value.mapLayerA.find((l) => l.displayName === layer.name)?.state === false) {
                return;
            }
            const mapLayerIds = layerStore.getMapLayersFromLayerObject(layer);
            flatList.push(...(mapLayerIds.reverse()));
        });
        if (mapStore.showMapBaseLayer) {
        baseLayerSourceIds.forEach((sourceId: string) => {
                if (sourceId) {
                    flatList.push(sourceId);
                }
            });
        }
        return flatList;
    });

    // Array of enabled Layers for Map B in order
    const mapLayersB = computed(() => {
        const flatList: string[] = [];
        if (!mapStore.map) {
            return flatList;
        }
        const baseLayerSourceIds = getBaseLayerSourceIds().reverse();
        layerStore.selectedLayers.forEach((layer) => {
            if (displayLayers.value.mapLayerB.find((l) => l.displayName === layer.name)?.state === false) {
                return;
            }
            const mapLayerIds = layerStore.getMapLayersFromLayerObject(layer);
            flatList.push(...(mapLayerIds.reverse()));
        });
        if (mapStore.showMapBaseLayer) {
            baseLayerSourceIds.forEach((sourceId: string) => {
                if (sourceId) {
                    flatList.push(sourceId);
                }
            });
        }
        return flatList;
    });


    watch(isComparing, (newVal) => {
        if (newVal) {
            initlizeComparing();
        }
    });


    watch(() => layerStore.selectedLayers, () => {
        if (isComparing.value) {
            // We only need to update layers and sources that are added or removed
            const newStyle = mapStore.getMap()?.getStyle();
            if (newStyle && mapAStyle.value && mapBStyle.value) {
                // find if there are new sources
                const existingSources = new Set<string>();
                mapAStyle.value?.sources && Object.keys(mapAStyle.value.sources).forEach((sourceId) => {
                    existingSources.add(sourceId);
                });
                Object.keys(newStyle.sources).forEach((sourceId) => {
                    if (!existingSources.has(sourceId)) {
                        // New source found, add to both styles
                        if (mapAStyle.value) {
                            mapAStyle.value.sources[sourceId] = cloneDeep(newStyle.sources[sourceId]);
                        }
                        if (mapBStyle.value) {
                            mapBStyle.value.sources[sourceId] = cloneDeep(newStyle.sources[sourceId]);
                        }
                    }
                });
                // find if there are removed sources
                const newSources = new Set<string>();
                Object.keys(newStyle.sources).forEach((sourceId) => {
                    newSources.add(sourceId);
                });
                existingSources.forEach((sourceId) => {
                    if (!newSources.has(sourceId)) {
                        // Source removed, remove from both styles
                        if (mapAStyle.value && mapAStyle.value.sources[sourceId]) {
                            delete mapAStyle.value.sources[sourceId];
                        }
                        if (mapBStyle.value && mapBStyle.value.sources[sourceId]) {
                            delete mapBStyle.value.sources[sourceId];
                        }
                    }
                });
                // Now we do the same for layers
                const existingLayerIds = new Set<string>();
                mapAStyle.value?.layers.forEach((layer: any) => {
                    existingLayerIds.add(layer.id);
                });
                newStyle.layers.forEach((layer: any) => {
                    if (!existingLayerIds.has(layer.id)) {
                        // New layer found, add to both styles
                        if (mapAStyle.value) {
                            mapAStyle.value.layers.push(cloneDeep(layer));
                        }
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
                existingLayerIds.forEach((layerId) => {
                    if (!newLayerIds.has(layerId)) {
                        // Layer removed, remove from both styles
                        if (mapAStyle.value) {
                            mapAStyle.value.layers = mapAStyle.value.layers.filter((layer: any) => layer.id !== layerId);
                        }
                        if (mapBStyle.value) {
                            mapBStyle.value.layers = mapBStyle.value.layers.filter((layer: any) => layer.id !== layerId);
                        }
                    }
                });
                // Determine Layer order and adjust if needed
                const layerOrderA: string[] = [];
                const layerOrderB: string[] = [];
                layerStore.selectedLayers.forEach((layer) => {
                    const mapLayerIds = layerStore.getMapLayersFromLayerObject(layer);
                    layerOrderA.push(...mapLayerIds);
                    layerOrderB.push(...mapLayerIds);
                });
                if (mapStore.showMapBaseLayer) {
                    const baseLayerSourceIds = getBaseLayerSourceIds();
                    baseLayerSourceIds.forEach((sourceId: string) => {
                        if (sourceId) {
                            layerOrderA.push(sourceId);
                            layerOrderB.push(sourceId);
                        }
                    });
                }
                // Reorder layers in mapAStyle
                if (mapAStyle.value) {
                    const reorderedLayersA: any[] = [];
                    layerOrderA.forEach((layerId) => {
                        const layer = mapAStyle.value!.layers.find((l: any) => l.id === layerId);
                        if (layer) {
                            reorderedLayersA.push(layer);
                        }
                    });
                    mapAStyle.value.layers = reorderedLayersA;
                }
                // Reorder layers in mapBStyle
                if (mapBStyle.value) {
                    const reorderedLayersB: any[] = [];
                    layerOrderB.forEach((layerId) => {
                        const layer = mapBStyle.value!.layers.find((l: any) => l.id === layerId);
                        if (layer) {
                            reorderedLayersB.push(layer);
                        }
                    });
                    mapBStyle.value.layers = reorderedLayersB;
                }
            } else {
                mapAStyle.value = mapStore.getMap()?.getStyle();
                mapBStyle.value = mapStore.getMap()?.getStyle();
            }
            generateDisplayLayers();
        }
    }, { deep: true });

    return {
        isComparing,
        orientation,
        displayLayers,
        mapStats,
        setVisibility,
        setAllVisibility,
        generateDisplayLayers,
        updateMapStats,
        updateMapLayerStyle,
        compareLayerStyles,
        mapAStyle,
        mapBStyle,
        mapLayersA,
        mapLayersB,
    }
});
