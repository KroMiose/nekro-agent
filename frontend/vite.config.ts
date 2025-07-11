import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react-swc'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  base: '/webui/',  // 配置为webui路径，与后端静态文件挂载路径一致
  optimizeDeps: {
    include: ['@monaco-editor/react'],  // 预构建Monaco Editor
  },
  server: {
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8021',
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
          'monaco-editor': ['@monaco-editor/react'],  // Monaco Editor 单独分chunk
        }
      }
    }
  },
  css: {
    postcss: './postcss.config.js',  // 指定配置文件路径
    devSourcemap: true,  // 开发时的 sourcemap
  }
})
