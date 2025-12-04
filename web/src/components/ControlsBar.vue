<script setup lang="ts">
import { ref } from "vue";
import html2canvas from "html2canvas";

import { useAppStore, useLayerStore, useMapStore } from "@/store";
const appStore = useAppStore();
const layerStore = useLayerStore();
const mapStore = useMapStore();

const copyMenuShown = ref(false);
const screenOverlayShown = ref(false);
const mapOnly = ref(false);
const loadingBounds = ref(false);

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
</script>

<template>
  <div id="controls-bar" :class="appStore.openSidebars.includes('left') ? 'controls-bar shifted' : 'controls-bar'">
    <v-btn color="primary" class="control-btn" variant="flat">
      <v-icon>mdi-map-outline</v-icon>
      <v-menu activator="parent" :close-on-content-click="false" open-on-hover>
        <v-card style="max-height: 400px; overflow-y: auto;">
          <v-list :selected="[mapStore.currentBasemap]"
            @update:selected="(selected) => mapStore.currentBasemap = selected[0]" class="basemap-list"
            density="compact" mandatory>
            <v-list-subheader>Base Map Options</v-list-subheader>
            <v-list-item v-for="basemap in mapStore.availableBasemaps" :key="basemap.id" :value="basemap" class="px-2">
              {{ basemap.name }}
              <template v-slot:prepend>
                <v-icon :icon="basemap.id === mapStore.currentBasemap?.id ? 'mdi-check' : 'none'" color="success"
                  class="pa-0"></v-icon>
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
</style>
