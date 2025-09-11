import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react-swc'

// https://vite.dev/config/
export default defineConfig(({ mode }) => {
  // 加载环境变量
  const env = loadEnv(mode, '.', '')

  // 获取后端地址，默认为 http://127.0.0.1:8021
  const backendUrl = env.VITE_API_BASE_URL || 'http://127.0.0.1:8021'

  return {
    plugins: [react()],
    base: '/webui/', // 配置为webui路径，与后端静态文件挂载路径一致
    optimizeDeps: {
      include: ['@monaco-editor/react'], // 预构建Monaco Editor
    },
    server: {
      proxy: {
        // API 请求代理
        '/api': {
          target: backendUrl,
          changeOrigin: true,
        },
        // 插件路由代理 - 用于访问插件的 Web 界面和 API
        '/plugins': {
          target: backendUrl,
          changeOrigin: true,
        },
      },
    },
    build: {
      cssMinify: true, // CSS 压缩
      cssCodeSplit: true, // CSS 代码分割
      rollupOptions: {
        output: {
          manualChunks: {
            'react-vendor': ['react', 'react-dom'],
            'mui-vendor': ['@mui/material', '@mui/icons-material'],
            'monaco-editor': ['@monaco-editor/react'], // Monaco Editor 单独分chunk
          },
        },
      },
    },
    css: {
      postcss: './postcss.config.js', // 指定配置文件路径
      devSourcemap: true, // 开发时的 sourcemap
    },
  }
})
