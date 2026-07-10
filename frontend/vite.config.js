import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

const apiProxy = process.env.VITE_API_PROXY || 'http://localhost:8000'

export default defineConfig({
  plugins: [react()],
  server: {
    host: '127.0.0.1',
    port: Number(process.env.VITE_PORT) || 5173,
    proxy: {
      '/api': apiProxy,
      '/posters': apiProxy,
    },
  },
  test: {
    environment: 'jsdom',
    setupFiles: './src/test/setup.js',
    globals: true,
  },
})
