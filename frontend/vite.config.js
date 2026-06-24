import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],

  preview: {
    allowedHosts: [
      "censo-frontend-production-dab7.up.railway.app",
      "censo-frontend-production-b6e8.up.railway.app"
    ]
  }
})
