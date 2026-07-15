/**
 * Vite development and production build configuration.
 */

import { defineConfig, loadEnv } from 'vite'
import vue from '@vitejs/plugin-vue'
import path from 'path'

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')
  const apiTarget = env.VITE_API_PROXY_TARGET || 'http://127.0.0.1:8000'

  return {
    plugins: [vue()],
    resolve: {
      alias: {
        '@': path.resolve(__dirname, './src')
      }
    },
    server: {
      port: 5173,
      open: false,
      proxy: {
        '/api': {
          target: apiTarget,
          changeOrigin: true,
          ws: true,
          secure: false
        }
      }
    },
    build: {
      outDir: 'dist',
      sourcemap: false,
      rollupOptions: {
        output: {
          manualChunks(id) {
            if (!id.includes('node_modules')) return undefined
            if (id.includes('element-plus') || id.includes('@element-plus')) return 'ui-vendor'
            if (id.includes('/vue/') || id.includes('vue-router') || id.includes('pinia')) return 'vue-vendor'
            if (id.includes('axios')) return 'http-vendor'
            if (id.includes('marked')) return 'markdown-vendor'
            return 'vendor'
          }
        }
      },
      chunkSizeWarningLimit: 1000
    }
  }
})
