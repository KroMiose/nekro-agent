// 环境变量配置
export const config = {
  // API 基础路径
  apiBaseUrl: '/api',

  // 是否是开发环境
  isDev: import.meta.env.DEV,

  // 是否是生产环境
  isProd: import.meta.env.PROD,
} as const
