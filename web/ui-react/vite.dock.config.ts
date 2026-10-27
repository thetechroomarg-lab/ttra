import path from 'node:path'
import tailwindcss from '@tailwindcss/vite'
import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// Compila la isla del dock a un único JS+CSS que sirve FastAPI desde static/dock/.
export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: { alias: { '@': path.resolve(__dirname, './src') } },
  define: { 'process.env.NODE_ENV': '"production"' },
  build: {
    outDir: '../static/dock',
    emptyOutDir: true,
    copyPublicDir: false,
    lib: { entry: 'src/dock-entry.tsx', formats: ['iife'], name: 'TTRADock', fileName: () => 'dock.js', cssFileName: 'dock' },
  },
})
