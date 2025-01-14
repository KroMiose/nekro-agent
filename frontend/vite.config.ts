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
  },
  build: {
    cssMinify: true,  // CSS 压缩
    cssCodeSplit: true,  // CSS 代码分割
    rollupOptions: {
      output: {
        manualChunks: {
          'react-vendor': ['react', 'react-dom'],
          'mui-vendor': ['@mui/material', '@mui/icons-material'],
        }
      }
    }
  },
  css: {
    postcss: './postcss.config.js',  // 指定配置文件路径
    devSourcemap: true,  // 开发时的 sourcemap
  }
})
