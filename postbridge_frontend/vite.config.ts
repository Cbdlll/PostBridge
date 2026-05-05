import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { fileURLToPath, URL } from 'node:url'

// https://vite.dev/config/
export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url))
    }
  },
  server: {
    host: '0.0.0.0', // 监听所有网络接口,允许外部访问
    port: 5173,
    allowedHosts: true, // 允许所有域名访问 (开发环境,生产环境请指定具体域名)
    proxy: {
      '/api': {
        target: 'http://localhost:5409',
        changeOrigin: true
      },
      '/upload': {
        target: 'http://localhost:5409',
        changeOrigin: true
      },
      '/uploadSave': {
        target: 'http://localhost:5409',
        changeOrigin: true
      },
      '/getFiles': {
        target: 'http://localhost:5409',
        changeOrigin: true
      },
      '/getFile': {
        target: 'http://localhost:5409',
        changeOrigin: true
      },
      '/deleteFile': {
        target: 'http://localhost:5409',
        changeOrigin: true
      },
      '/renameFile': {
        target: 'http://localhost:5409',
        changeOrigin: true
      },
      '/getAccounts': {
        target: 'http://localhost:5409',
        changeOrigin: true
      },
      '/getValidAccounts': {
        target: 'http://localhost:5409',
        changeOrigin: true
      },
      '/deleteAccount': {
        target: 'http://localhost:5409',
        changeOrigin: true
      },
      '/updateUserinfo': {
        target: 'http://localhost:5409',
        changeOrigin: true
      },
      '/login': {
        target: 'http://localhost:5409',
        changeOrigin: true
      },
      '/postVideo': {
        target: 'http://localhost:5409',
        changeOrigin: true
      },
      '/uploadCookie': {
        target: 'http://localhost:5409',
        changeOrigin: true
      },
      '/downloadCookie': {
        target: 'http://localhost:5409',
        changeOrigin: true
      },
      '/verificationCodeNotify': {
        target: 'http://localhost:5409',
        changeOrigin: true
      },
      '/submitVerificationCode': {
        target: 'http://localhost:5409',
        changeOrigin: true
      }
    }
  }
})
