import { fileURLToPath, URL } from 'node:url';

import vue from '@vitejs/plugin-vue';
import { defineConfig } from 'vite';

export default defineConfig({
  base: '/static/',
  plugins: [vue()],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url)),
    },
  },
  build: {
    outDir: '../src/cairn/server/static',
    assetsDir: 'assets',
    emptyOutDir: false,
    target: 'es2022',
  },
  server: {
    host: '0.0.0.0',
    port: 5173,
    proxy: {
      '/settings': 'http://127.0.0.1:8000',
      '/projects': 'http://127.0.0.1:8000',
      '/static': 'http://127.0.0.1:8000',
    },
  },
});
