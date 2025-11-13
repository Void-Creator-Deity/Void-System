import { defineConfig } from "vite"
import vue from "@vitejs/plugin-vue"
import path from "path"

export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),   // ✅ 让 @ 指向 src/
    },
  },
  server: {
    port: 5173,
    open: true,
  },
})
