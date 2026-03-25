import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import tailwindcss from '@tailwindcss/vite'

export default defineConfig({
  plugins: [
    vue(),
    tailwindcss(),
  ],
  server: {
    host: '0.0.0.0',   // 监听所有网卡，局域网其他电脑可访问
    port: 5173,
    allowedHosts: 'all', // 允许任意 Host 头访问（局域网/手机访问需要）
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8000',  // 后端地址（本机运行时不需要改）
        changeOrigin: true,
      },
      '/static': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      }
    }
  }
})
