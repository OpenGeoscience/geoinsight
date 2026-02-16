<script setup lang="ts">
import { ref, computed } from "vue";
import { Layer } from "@/types";
import ColormapPreview from './ColormapPreview.vue';

import { useLayerStore, useStyleStore } from "@/store";
const layerStore = useLayerStore();
const styleStore = useStyleStore();

const searchText = ref<string | undefined>();
const filteredLegend = computed(() => {
    return layerStore.selectedLayers?.filter((layer) => {
        return (
            layer.visible &&
            (!searchText.value || layer.name.toLowerCase().includes(searchText.value.toLowerCase()))
        )
    })
})

function getColormapPreviews(layer: Layer) {
    const styleKey = `${layer.id}.${layer.copy_id}`;
    const currentStyleSpec = styleStore.selectedLayerStyles[styleKey].style_spec;
    if (!currentStyleSpec) return [];
    const currentFrame = layerStore.layerFrames(layer).find(
        (f) => f.index === layer.current_frame_index
    )
    return currentStyleSpec.colors.map((colorConfig) => {
        let discrete = false;
        let nColors = 1;
        let colorBy = undefined;
        let useFeatureProps = currentFrame?.vector && colorConfig.use_feature_props;
        let colormap = styleStore.colormaps.find((cmap) => cmap.id === colorConfig.colormap?.id)
        if (colormap) {
            discrete = colorConfig.colormap?.discrete || discrete;
            nColors = colorConfig.colormap?.n_colors || nColors;
            colorBy = colorConfig.colormap?.color_by;
        } else if (colorConfig.single_color) {
            colormap = {
                markers: [
                    { color: colorConfig.single_color, value: 0 },
                ]
            }
        }
        return {
            name: colorConfig.name,
            colormap,
            discrete,
            nColors,
            colorBy,
            useFeatureProps,
        }
    })
}
</script>

<template>
    <div class="panel-content-outer with-search">
        <v-text-field v-model="searchText" label="Search Legend" variant="outlined" density="compact" class="mb-2"
            append-inner-icon="mdi-magnify" hide-details />
        <v-card class="panel-content-inner">
            <v-list v-if="filteredLegend?.length" density="compact">
                <v-list-item v-for="layer in filteredLegend" :key="layer.id">
                    {{ layer.name }}
                    <div v-for="colormap_preview in getColormapPreviews(layer)" class="ml-4">
                        <div v-if="getColormapPreviews(layer).length > 1">{{ colormap_preview.name }}</div>
                        <span v-if="colormap_preview.useFeatureProps">Use feature color properties; default to </span>
                        <span v-if="colormap_preview.colorBy">color by {{ colormap_preview.colorBy }}</span>
                        <span v-if="!colormap_preview.colormap">Use default style</span>
                        <colormap-preview v-if="colormap_preview.colormap" :colormap="colormap_preview.colormap"
                            :discrete="colormap_preview.discrete" :nColors="colormap_preview.nColors" />
                    </div>
                </v-list-item>
            </v-list>
        </v-card>
    </div>
</template>
