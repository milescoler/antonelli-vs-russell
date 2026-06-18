import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

// Production (GitHub Pages project site) is served under /antonelli-vs-russell/;
// dev is served at the root so `npm run dev` works at localhost:5173/. Data is
// fetched relative to import.meta.env.BASE_URL, so this base is the only knob.
export default defineConfig(({ command }) => ({
  base: command === 'build' ? '/antonelli-vs-russell/' : '/',
  plugins: [react(), tailwindcss()],
}))
