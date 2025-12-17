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
        ws: true,  // 支持 WebSocket 和 SSE 长连接
        secure: false  // 允许代理到 HTTP 服务
        // 移除 rewrite 选项，确保 /api/stream-chat 被代理到 http://127.0.0.1:8000/api/stream-chat
      }
    }
  },
  build: {
    outDir: 'dist',  // 构建输出目录
    sourcemap: false,  // 生产环境关闭 sourcemap
    chunkSizeWarningLimit: 1000  // chunk 大小警告限制（KB）
  }
})
