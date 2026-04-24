import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  
  // Asegurar que Vite interpole las variables de entorno correctamente
  define: {
    __VITE_API_BASE_URL__: JSON.stringify(process.env.VITE_API_BASE_URL || 'http://localhost:8000')
  },
  
  preview: {
    allowedHosts: [
      "censo-frontend-production-dab7.up.railway.app"
    ]
  }
})
