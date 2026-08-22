import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],

  server: {
    port: 5173,
    // During development the page is served from here and the API from the
    // Python process on 8000. Proxying /api makes them look like one origin to
    // the browser, so there is no CORS configuration to get wrong, and the
    // fetch calls are written exactly as they will run in production.
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
    },
  },

  build: {
    // The production image serves the built page from the same FastAPI process
    // that serves the API: one port, one container. Building straight into the
    // place main.py looks for it keeps that from needing a copy step.
    outDir: '../backend/static',
    emptyOutDir: true,
  },
})
