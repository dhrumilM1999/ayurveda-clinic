// Settings for the Vite development server. ASK FIRST before editing.
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// Inside Docker the backend is reachable as "backend"; outside Docker it is localhost.
const backend = process.env.VITE_PROXY_TARGET || 'http://localhost:8000';

export default defineConfig({
  plugins: [react()],
  server: {
    host: '0.0.0.0',
    port: 5173,
    // Polling makes code changes on Windows show up inside Docker.
    watch: { usePolling: true, interval: 300 },
    // Send /api calls to Django, so the browser sees one address (no CORS problems).
    proxy: {
      '/api': { target: backend, changeOrigin: false, xfwd: true },
      '/media': { target: backend, changeOrigin: false },
    },
  },
});
