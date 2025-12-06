// 环境变量配置
export const config = {
  // API 基础路径
<<<<<<< HEAD
  apiBaseUrl: '/api',
=======
<<<<<<< HEAD
  apiBaseUrl: '/api',
=======
<<<<<<< HEAD
  apiBaseUrl: '/api',
=======
  apiBaseUrl: import.meta.env.VITE_API_BASE_URL || '/api',
>>>>>>> 6cf9d37 (增加PYPI源自定义和代理功能)
>>>>>>> a776096 (增加PYPI源自定义和代理功能)
>>>>>>> e26199f (增加PYPI源自定义和代理功能)

  // 是否是开发环境
  isDev: import.meta.env.DEV,

  // 是否是生产环境
  isProd: import.meta.env.PROD,
} as const
