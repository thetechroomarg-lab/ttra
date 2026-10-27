import path from 'node:path'
import tailwindcss from '@tailwindcss/vite'
import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// Compila el spiral slider de /blackhole a un único JS+CSS que sirve FastAPI desde static/blackhole-slider/.
export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: { alias: { '@': path.resolve(__dirname, './src') } },
  define: { 'process.env.NODE_ENV': '"production"' },
  build: {
    outDir: '../static/blackhole-slider',
    emptyOutDir: true,
    copyPublicDir: false,
    lib: { entry: 'src/blackhole-entry.tsx', formats: ['iife'], name: 'TTRABlackholeSlider', fileName: () => 'slider.js', cssFileName: 'slider' },
  },
})
