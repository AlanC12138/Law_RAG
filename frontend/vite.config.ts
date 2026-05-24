import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    host: '0.0.0.0',   // required to accept connections from outside the container
    proxy: {
      '/api': {
        // Use BACKEND_URL when running inside Docker, fall back to localhost for local dev
        target: process.env.BACKEND_URL || 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
})
