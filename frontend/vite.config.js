import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// Lets you point the dev-server proxy at a non-default backend (e.g. an
// ngrok URL) without touching this file -- see DEPLOYMENT.md.
// Not needed for plain local dev; defaults to localhost:8000.
const proxyTarget = process.env.VITE_PROXY_TARGET || 'http://localhost:8000'

export default defineConfig({
  plugins: [react()],
  server: {
    host: true, // listen on 0.0.0.0 so other devices on your network can reach it too
    port: 5173,
    strictPort: true,
    proxy: {
      '/api': {
        target: proxyTarget,
        changeOrigin: true,
      },
    },
  },
})
