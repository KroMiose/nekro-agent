import axios from 'axios'
import { useAuthStore } from '../../stores/auth'
import { config } from '../../config/env'

// 创建 axios 实例
const axiosInstance = axios.create({
  baseURL: config.apiBaseUrl,
  timeout: 10000,
})

// 请求拦截器
axiosInstance.interceptors.request.use(
  config => {
    const token = useAuthStore.getState().token
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  error => {
    console.error('Request error:', error)
    return Promise.reject(error)
  }
)

// 响应拦截器
axiosInstance.interceptors.response.use(
  response => response,
  async error => {
    console.error('Response error:', error)

    if (error.response?.status === 401) {
      // token 过期，清除登录状态
      useAuthStore.getState().logout()
      window.location.href = '/login'
      return Promise.reject(new Error('登录已过期，请重新登录'))
    }

    if (error.response?.data?.msg) {
      return Promise.reject(new Error(error.response.data.msg))
    }

    if (error.message === 'Network Error') {
      return Promise.reject(new Error('网络连接失败，请检查网络设置'))
    }

    return Promise.reject(error)
  }
)

export default axiosInstance
