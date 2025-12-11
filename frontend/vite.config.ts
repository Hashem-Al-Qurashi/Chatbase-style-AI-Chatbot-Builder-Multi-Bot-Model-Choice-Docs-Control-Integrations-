import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 3005,
    strictPort: false, // Allow fallback to other ports
    host: true, // Allow external connections
    allowedHosts: ['481217dade00.ngrok-free.app', 'localhost', '.ngrok-free.app'],
    proxy: {
      '/api/v1': {
        target: 'http://localhost:8001',
        changeOrigin: true,
        secure: false,
      },
      '/auth': {
        target: 'http://localhost:8001',
        changeOrigin: true,
        secure: false,
      }
    }
  },
  build: {
    outDir: 'dist',
    sourcemap: true,
  },
  preview: {
    port: 3000,
    strictPort: true,
  }
})