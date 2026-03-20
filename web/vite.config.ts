// Plugins
import Vue from '@vitejs/plugin-vue'
import Vuetify, { transformAssetUrls } from 'vite-plugin-vuetify'

// Utilities
import { defineConfig } from 'vite'
import process from 'node:process'
import { fileURLToPath, URL } from 'node:url'

import packageJson from './package.json'

process.env.VITE_APP_VERSION = packageJson.version;

export default defineConfig({
    plugins: [
        Vue({
            template: { transformAssetUrls },
        }),
        Vuetify({
            autoImport: true,
        }),
    ],
    resolve: {
        alias: {
            '@': fileURLToPath(new URL('./src', import.meta.url)),
        },
    },
    server: {
        port: 8080,
    },
})
