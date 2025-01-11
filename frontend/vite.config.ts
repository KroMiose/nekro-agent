import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react-swc'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  base: '/',  // 使用根路径
  server: {
    proxy: {
      '/api': {
        target: 'http://localhost:8021',
        changeOrigin: true,
      }
    }
  }
})
