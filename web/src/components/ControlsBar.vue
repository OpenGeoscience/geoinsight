<script setup lang="ts">
import { ref, watch } from "vue";
import html2canvas from "html2canvas";
import { Map } from "maplibre-gl";

import JsonEditorVue from 'json-editor-vue'
import 'vanilla-jsoneditor/themes/jse-theme-dark.css'
import { Mode } from 'vanilla-jsoneditor'

import { useAppStore, useLayerStore, useMapStore } from "@/store";
import { createBasemap } from "@/api/rest";
const appStore = useAppStore();
const layerStore = useLayerStore();
const mapStore = useMapStore();

const copyMenuShown = ref(false);
const screenOverlayShown = ref(false);
const mapOnly = ref(false);
const loadingBounds = ref(false);
const basemapList = ref();
const basemapPreviews = ref<Record<number, Map>>({});
const showBasemapCreation = ref(false);
const newBasemapTab = ref<'url' | 'json'>('url')
const newBasemapName = ref();
const newBasemapTileURL = ref();
const newBasemapStyleJSON = ref();
const newBasemapPreview = ref<Map | undefined>();

function createBasemapPreviews() {
  if (basemapList.value) {
    const map = mapStore.getMap();
    const center = map.getCenter();
    const zoom = map.getZoom();
    mapStore.availableBasemaps.forEach((basemap) => {
      if (basemap.id === undefined) return;
      if (basemapPreviews.value[basemap.id]) {
        basemapPreviews.value[basemap.id].remove()
      }
      const preview = new Map({
        container: 'basemap-preview-' + basemap.id,
        attributionControl: false,
      });
      preview.setZoom(zoom);
      preview.setCenter(center);
      preview.setStyle(basemap.style);
      basemapPreviews.value[basemap.id] = preview;
    })
  }
}

function cancelBasemapCreate() {
  showBasemapCreation.value = false;
  newBasemapTab.value = 'url';
  newBasemapName.value = undefined;
  newBasemapTileURL.value = undefined;
  newBasemapStyleJSON.value = undefined;
  newBasemapPreview.value = undefined;
}

function switchBasemapCreateTab() {
  newBasemapTileURL.value = undefined;
  newBasemapStyleJSON.value = undefined;
  createNewBasemapPreview()
}

function setNewBasemapStyleFromTileURL() {
  if (newBasemapTileURL.value) {
    newBasemapStyleJSON.value = {
      version: 8,
      sources: {
        "base-source": {
          type: "raster",
          tiles: [newBasemapTileURL.value],
          tileSize: 256,
        }
      },
      layers: [
        {
          id: "base-layer",
          type: "raster",
          source: "base-source"
        }
      ]
    }
  } else {
    newBasemapStyleJSON.value = undefined
  }
}

function createNewBasemapPreview() {
  if (!newBasemapPreview.value) {
    const map = mapStore.getMap();
    const center = map.getCenter();
    const zoom = map.getZoom();
    newBasemapPreview.value = new Map({
      container: 'basemap-preview-new',
      attributionControl: false,
      center,
      zoom,
    })
  }
  if (newBasemapStyleJSON.value) {
    newBasemapPreview.value.setStyle(newBasemapStyleJSON.value);
  } else {
    newBasemapPreview.value.setStyle({
      version: 8,
      sources: {},
      layers: []
    })
  }
}

function submitBasemapCreate() {
  createBasemap({
    name: newBasemapName.value,
    style: newBasemapStyleJSON.value,
  }).then((basemap) => {
    cancelBasemapCreate();
    mapStore.fetchAvailableBasemaps();
    mapStore.currentBasemap = basemap;
  })
}

async function fitMap() {
  loadingBounds.value = true;
  const map = mapStore.getMap();
  const bounds = await layerStore.getBoundsOfVisibleLayers()
  if (bounds) map.fitBounds(bounds)
  loadingBounds.value = false;
}

function takeScreenshot(save: boolean) {
  copyMenuShown.value = false;
  const screenshotTarget = document.getElementById("app");
  if (screenshotTarget) {
    html2canvas(screenshotTarget, {
      ignoreElements: (element) => {
        return (
          element.id === "controls-bar" ||
          element.classList.contains("control-menu") ||
          (mapOnly.value && element.classList.contains('v-navigation-drawer'))
        );
      },
    }).then((canvas) => {
      canvas.toBlob((blob) => {
        if (blob) {
          if (save) {
            const link = document.createElement("a");
            link.href = URL.createObjectURL(blob);
            link.download = "geoinsight_screenshot.png";
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
          } else {
            const clipboardItem = new ClipboardItem({
              "image/png": blob,
            });
            navigator.clipboard.write([clipboardItem]);
          }

          // animate camera flash with overlay
          setTimeout(() => {
            screenOverlayShown.value = true;
            setTimeout(() => {
              screenOverlayShown.value = false;
            }, 200);
          }, 200);
        }
      });
    });
  }
}

watch(basemapList, createBasemapPreviews)
watch(newBasemapTab, switchBasemapCreateTab)
watch(newBasemapTileURL, setNewBasemapStyleFromTileURL)
watch(newBasemapStyleJSON, createNewBasemapPreview)
</script>

<template>
  <div id="controls-bar" :class="appStore.openSidebars.includes('left') ? 'controls-bar shifted' : 'controls-bar'">
    <v-btn color="primary" class="control-btn" variant="flat">
      <v-icon>mdi-map-outline</v-icon>
      <v-menu activator="parent" :close-on-content-click="false" open-on-hover>
        <v-card style="max-height: 400px; overflow-y: auto;">
          <v-list :selected="[mapStore.currentBasemap]"
            @update:selected="(selected) => mapStore.currentBasemap = selected[0]" class="basemap-list"
            ref="basemapList" density="compact" mandatory>
            <v-list-subheader>Base Map Options</v-list-subheader>
            <v-list-item v-for="basemap in mapStore.availableBasemaps" :key="basemap.id" :value="basemap" class="px-2">
              {{ basemap.name }}
              <template v-slot:prepend>
                <v-icon :icon="basemap.id === mapStore.currentBasemap?.id ? 'mdi-check' : 'none'" color="success"
                  class="pa-0"></v-icon>
              </template>
              <template v-slot:append>
                <div v-if="basemap.id !== undefined" class="basemap-preview" :id="'basemap-preview-' + basemap.id">
                </div>
              </template>
            </v-list-item>
            <v-list-item key="new" title="New" @click="showBasemapCreation = true">
              <template v-slot:prepend>
                <v-icon icon="mdi-plus" class="pa-0"></v-icon>
              </template>
            </v-list-item>
          </v-list>
        </v-card>
      </v-menu>
    </v-btn>
    <v-btn class="control-btn" @click="fitMap" variant="flat">
      <v-progress-circular v-if="loadingBounds" indeterminate />
      <v-icon v-else icon="mdi-fit-to-page-outline" v-tooltip="'Fit Map to Visible Layers'"></v-icon>
    </v-btn>
    <v-btn class="control-btn" variant="flat">
      <v-icon icon="mdi-camera"></v-icon>
      <v-menu v-model="copyMenuShown" activator="parent" :open-on-hover="true" :close-on-content-click="false">
        <v-card class="control-menu">
          <div class="control-menu-title">Take Screenshot</div>
          <v-card-text class="pa-3">
            <div class="control-menu-row">
              <v-checkbox v-model="mapOnly" label="Map Only" density="compact" hide-details />
            </div>
            <div class="control-menu-row" @click="() => takeScreenshot(false)">
              <div>Copy image to clipboard</div>
            </div>
            <div class="control-menu-row" @click="() => takeScreenshot(true)">
              <div>Save image</div>
            </div>
          </v-card-text>
        </v-card>
      </v-menu>
    </v-btn>
    <v-btn class="control-btn" variant="flat">
      <v-icon icon="mdi-information-outline"></v-icon>
      <v-menu activator="parent" :open-on-hover="true" :close-on-content-click="false">
        <v-card class="control-menu">
          <div class="control-menu-title">Input Controls</div>
          <v-card-text class="pa-3">
            <div style="text-align: right; width: 100%">
              <v-icon icon="mdi-keyboard"></v-icon>,
              <v-icon icon="mdi-mouse"></v-icon>
            </div>
            <div class="control-menu-row">
              <div>Zoom</div>
              <div>+/-, scroll</div>
            </div>
            <div class="control-menu-row">
              <div>Pan</div>
              <div>arrows, drag</div>
            </div>
          </v-card-text>
        </v-card>
      </v-menu>
    </v-btn>
    <v-overlay :model-value="screenOverlayShown" absolute persistent :opacity="0.8" scrim="white">
    </v-overlay>
    <v-dialog :model-value="showBasemapCreation" width="500">
      <v-card>
        <v-card-title class="pa-3">
          New Basemap
          <v-btn class="close-button transparent" variant="flat" icon @click="cancelBasemapCreate">
            <v-icon>mdi-close</v-icon>
          </v-btn>
        </v-card-title>
        <v-card-text class="d-flex" style="flex-direction: column; row-gap: 5px">
          <v-text-field v-model="newBasemapName" label="Name" hide-details density="compact" autofocus />
          <v-tabs v-model="newBasemapTab" color="primary">
            <v-tab value="url">Tile URL</v-tab>
            <v-tab value="json">MapLibre Style JSON</v-tab>
          </v-tabs>
          <v-window v-model="newBasemapTab">
            <v-window-item value="url">
              <div>Supply a tile URL</div>
              <div>(e.g. https://a.tile.openstreetmap.org/{z}/{x}/{y}.png)</div>
              <v-text-field v-model="newBasemapTileURL" label="Tile URL" hide-details density="compact" />
            </v-window-item>
            <v-window-item value="json">
              <div>
                Supply a JSON that adheres to the
                <a href="https://maplibre.org/maplibre-style-spec/">Maplibre Style Spec</a>.
              </div>
              <div>
                Style spec can be supplied directly as JSON or as a URL string that references a publicly accessible
                JSON file (e.g. "https://basemaps.cartocdn.com/gl/voyager-gl-style/style.json").
              </div>
              <json-editor-vue v-model="newBasemapStyleJSON" :mode="Mode.text" :stringified="false"
                :main-menu-bar="false" :ask-to-format="false" :indentation="4"
                :class="appStore.theme === 'dark' ? 'jse-theme-dark' : ''" />
            </v-window-item>
          </v-window>
          <v-spacer />
          <div>Map Preview:</div>
          <div id="basemap-preview-new"></div>
        </v-card-text>
        <v-card-actions style="text-align: right;">
          <v-btn @click="cancelBasemapCreate" variant="tonal">
            Cancel
          </v-btn>
          <v-btn color="primary" :disabled="!newBasemapName || !newBasemapStyleJSON" @click="submitBasemapCreate">
            Create
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </div>
</template>

<style>
.controls-bar {
  padding: 3px 8px;
  position: absolute;
  top: 10px;
  left: 225px;
  opacity: 80%;
  background-color: rgb(var(--v-theme-surface));
  display: flex;
  border-radius: 8px;
}

.controls-bar.shifted {
  left: 375px;
}

.controls-bar i {
  font-size: 24px;
}

.control-btn {
  min-width: 0 !important;
  width: 40px;
}

.control-menu {
  min-width: 200px;
  border-radius: 10px;
  background-color: rgb(var(--v-theme-surface-variant)) !important;
}

.control-menu-title {
  width: 100%;
  padding: 3px 8px;
  background-color: rgb(var(--v-theme-surface-bright));
}

.control-menu-row {
  display: flex;
  justify-content: space-between;
  margin-bottom: 5px;
}

.basemap-list .v-list-item__prepend>.v-icon~.v-list-item__spacer {
  width: 5px;
}

.basemap-preview {
  margin: 0px 10px;
  height: 50px;
  width: 50px;
}

#basemap-preview-new {
  width: 100%;
  height: 150px;
  border: 1px solid rgb(var(--v-theme-on-surface-variant))
}
</style>
