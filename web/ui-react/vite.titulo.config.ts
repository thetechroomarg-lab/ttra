import path from 'node:path'
import tailwindcss from '@tailwindcss/vite'
import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// Compila el título de /blackhole en la home a un único JS+CSS que sirve FastAPI desde static/blackhole-titulo/.
export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: { alias: { '@': path.resolve(__dirname, './src') } },
  define: { 'process.env.NODE_ENV': '"production"' },
  build: {
    outDir: '../static/blackhole-titulo',
    emptyOutDir: true,
    copyPublicDir: false,
    lib: { entry: 'src/titulo-entry.tsx', formats: ['iife'], name: 'TTRABlackholeTitulo', fileName: () => 'titulo.js', cssFileName: 'titulo' },
  },
})
