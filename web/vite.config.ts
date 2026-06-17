import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

// `base` must match the GitHub Pages project path. Change if the repo is renamed.
// Data is fetched relative to import.meta.env.BASE_URL, so this is the only knob.
export default defineConfig({
  base: '/antonelli-vs-russell/',
  plugins: [react(), tailwindcss()],
})
