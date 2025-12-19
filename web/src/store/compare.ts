import { defineStore } from 'pinia';
import { computed, ref, watch } from 'vue';
import { useLayerStore } from './layer';
import { cloneDeep, map } from 'lodash';
import { useMapStore } from './map';
import { useStyleStore } from './style';
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

// Extract source diffing logic
function findSourceDifferences(
    newStyle: maplibregl.StyleSpecification,
    existingStyle: ReturnType<maplibregl.Map['getStyle']> | undefined
): {
    added: string[];
    removed: string[];
} {
    if (!existingStyle) {
        return { added: Object.keys(newStyle.sources), removed: [] };
    }
    
    const existing = new Set(Object.keys(existingStyle.sources));
    const current = new Set(Object.keys(newStyle.sources));
    
    return {
        added: Array.from(current).filter(id => !existing.has(id)),
        removed: Array.from(existing).filter(id => !current.has(id)),
    };
}

// Extract layer diffing logic
function findLayerDifferences(
    newStyle: maplibregl.StyleSpecification,
    existingStyle: ReturnType<maplibregl.Map['getStyle']> | undefined
): {
    added: any[];
    removed: string[];
} {
    if (!existingStyle) {
        return { added: newStyle.layers, removed: [] };
    }
    
    const existing = new Set(existingStyle.layers.map((l: any) => l.id));
    const current = new Set(newStyle.layers.map((l: any) => l.id));
    
    return {
        added: newStyle.layers.filter((l: any) => !existing.has(l.id)),
        removed: Array.from(existing).filter(id => !current.has(id)),
    };
}

export const useMapCompareStore = defineStore('mapCompare', () => {
    const mapStore = useMapStore();
    const layerStore = useLayerStore();
    const styleStore = useStyleStore();
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

    /**
     * Reapply stored opacity values to all layers in compare mode
     * This ensures opacity values remain consistent when layers are added/removed/reordered
     */
    const reapplyStoredOpacityValues = () => {
        if (!isComparing.value) return;

        // Process both map A and map B
        (['A', 'B'] as const).forEach((panel) => {
            const storedStyles = compareLayerStyles.value[panel];
            
            // Iterate through all stored layer styles
            Object.entries(storedStyles).forEach(([styleKey, storedStyle]) => {
                // Parse the style key to get layer id and copy_id
                const [layerIdStr, copyIdStr] = styleKey.split('.');
                const layerId = parseInt(layerIdStr);
                const copyId = parseInt(copyIdStr);
                
                // Find the layer object
                const layer = layerStore.selectedLayers.find(
                    (l) => l.id === layerId && l.copy_id === copyId
                );
                
                if (!layer) return;
                
                // Get all map layer IDs for this layer
                const mapLayerIds = layerStore.getMapLayersFromLayerObject(layer).flat();
                
                // Get the current frame
                const frames = layerStore.layerFrames(layer);
                const currentFrame = frames.find(
                    (f) => f.index === layer.current_frame_index
                );
                
                if (!currentFrame) return;
                
                // Get the stored style spec with the stored opacity
                const styleSpec = storedStyle.style?.style_spec;
                if (!styleSpec) return;
                
                // Update the opacity in the style spec to match stored value
                const styleSpecWithOpacity = cloneDeep(styleSpec);
                styleSpecWithOpacity.opacity = storedStyle.opacity;
                
                // Apply the style to all map layers for this layer
                mapLayerIds.forEach((mapLayerId) => {
                    // Check if the map layer exists in the main map (required for returnMapLayerStyle)
                    const mainMap = mapStore.getMap();
                    if (!mainMap || !mainMap.getLayer(mapLayerId)) {
                        return;
                    }
                    
                    const visibileLayers = panel === 'A' ? mapLayersA.value : mapLayersB.value;
                    const visibility = visibileLayers.includes(mapLayerId) ? 'visible' : 'none';
                    
                    const result = styleStore.returnMapLayerStyle(
                        mapLayerId,
                        styleSpecWithOpacity,
                        currentFrame,
                        currentFrame.vector,
                        visibility
                    );
                    
                    if (result) {
                        updateMapLayerStyle(panel, mapLayerId, result);
                    }
                });
            });
        });
    };

    function updateCompareLayerStyle() {
        const compareMapAddedSources: {sourceId: string, sourceType: SourceSpecification['type']}[] = [];
        if (!isComparing.value) return compareMapAddedSources;
        
        const newStyle = mapStore.getMap()?.getStyle();
        if (!newStyle || !mapAStyle.value || !mapBStyle.value) {
            mapAStyle.value = newStyle;
            mapBStyle.value = newStyle;
            return compareMapAddedSources;
        }
        
        // Process both maps
        (['A', 'B'] as const).forEach((panel) => {
            const mapStyle = panel === 'A' ? mapAStyle.value : mapBStyle.value;
            if (!mapStyle) return;
            
            // Handle sources
            const sourceDiff = findSourceDifferences(newStyle, mapStyle);
            sourceDiff.added.forEach((sourceId) => {
                mapStyle.sources[sourceId] = cloneDeep(newStyle.sources[sourceId]);
                if (panel === 'B') {
                    compareMapAddedSources.push({
                        sourceId,
                        sourceType: newStyle.sources[sourceId].type,
                    });
                }
            });
            sourceDiff.removed.forEach((sourceId) => {
                delete mapStyle.sources[sourceId];
            });
            
            // Handle layers
            const layerDiff = findLayerDifferences(newStyle, mapStyle);
            layerDiff.added.forEach((layer) => {
                mapStyle.layers.push(cloneDeep(layer));
            });
            layerDiff.removed.forEach((layerId) => {
                mapStyle.layers = mapStyle.layers.filter((l: any) => l.id !== layerId);
            });
        });
        
        generateDisplayLayers();
        reapplyStoredOpacityValues();
        return compareMapAddedSources;
    }
    watch([() => layerStore.selectedLayers, () => mapStore.currentBasemap], async () => {
        const compareMapAddedSources = updateCompareLayerStyle();
        // Any new sources we need to add click handlers for
        compareMapAddedSources.forEach(({ sourceId, sourceType }) => {
            if (isComparing.value && mapStore.compareMap) {
                if (sourceType === 'vector') {
                    mapStore.setupVectorLayerClickHandlers(mapStore.compareMap, sourceId, mapStore.handleCompareLayerClick);
                } 
            }
        });
    }, { deep: true });

    const setOrientation = (newOrientation: 'horizontal' | 'vertical') => {
        orientation.value = newOrientation;
    };

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
        setOrientation,
    }
});
