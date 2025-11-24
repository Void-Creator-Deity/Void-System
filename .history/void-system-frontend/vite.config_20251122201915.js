/**
 * Vite Configuration
 * -------------------
 * Vite 构建工具配置文件
 */

import { defineConfig } from "vite"
import vue from "@vitejs/plugin-vue"
import path from "path"

export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),  // 路径别名，@ 指向 src 目录
    },
  },
  server: {
    port: 5173,  // 开发服务器端口
    open: true,  // 自动打开浏览器
    proxy: {
      // 开发环境代理配置（可选）
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, '')
      }
    }
  },
  build: {
    outDir: 'dist',  // 构建输出目录
    sourcemap: false,  // 生产环境关闭 sourcemap
    chunkSizeWarningLimit: 1000  // chunk 大小警告限制（KB）
  }
})
