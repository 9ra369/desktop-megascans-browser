import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

export default defineConfig({
  root: 'src/renderer',
  // Electronは file:// から読み込むので、相対パスで出力する。
  base: './',
  build: {
    outDir: '../../dist/renderer',
    emptyOutDir: true,
  },
  server: { port: 5173, strictPort: true },
})
