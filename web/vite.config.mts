// Plugins
import Components from 'unplugin-vue-components/vite'
import Vue from '@vitejs/plugin-vue'
import { nodePolyfills } from 'vite-plugin-node-polyfills'
import Vuetify, { transformAssetUrls } from 'vite-plugin-vuetify'

// Utilities
import { defineConfig } from 'vite'
import { fileURLToPath, URL } from 'node:url'

import packageJson from './package.json'


process.env.VITE_APP_VERSION = packageJson.version;

// https://vitejs.dev/config/
export default defineConfig({
    plugins: [
        Vue({
            template: { transformAssetUrls },
        }),
        // https://github.com/vuetifyjs/vuetify-loader/tree/master/packages/vite-plugin#readme
        Vuetify({
            autoImport: true,
        }),
        Components(),
        nodePolyfills(),
    ],
    resolve: {
        alias: {
            '@': fileURLToPath(new URL('./src', import.meta.url)),
            // TODO: this is a fix for a bug in vite, see https://github.com/vitejs/vite/discussions/8549#discussioncomment-7333115
            '@jsdevtools/ono': '@jsdevtools/ono/cjs/index.js',
        },
        extensions: [
            '.js',
            '.json',
            '.jsx',
            '.mjs',
            '.ts',
            '.tsx',
            '.vue',
        ],
    },
    server: {
        host: true,
        port: 8080,
    },
    build: {
        commonjsOptions: {
            transformMixedEsModules: true,
        },
    },
})
