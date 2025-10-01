import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  // Allow Render preview host
  preview: {
    host: true, // bind to 0.0.0.0
    // Permit your Render domain; add others here if you create new services
    allowedHosts: [
      'email-auto-4.onrender.com',
      /\.onrender\.com$/,
    ],
  },
})
