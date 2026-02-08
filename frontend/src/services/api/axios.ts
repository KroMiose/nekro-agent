import axios, { AxiosError } from 'axios'
import i18n from '../../config/i18n'
import { useAuthStore } from '../../stores/auth'
import { config } from '../../config/env'
import type { ApiErrorResponse } from './types'

/**
 * 自定义 API 错误类
 *
 * 封装后端返回的错误信息，提供统一的错误处理接口
 */
export class ApiError extends Error {
  /** 错误类型（后端错误类名） */
  public readonly type: string
  /** 技术细节（可选） */
  public readonly detail?: string | null
  /** 附加数据（可选） */
  public readonly data?: unknown

  constructor(
    type: string,
    message: string,
    detail?: string | null,
    data?: unknown
  ) {
    super(message)
    this.name = 'ApiError'
    this.type = type
    this.detail = detail
    this.data = data
  }

  /**
   * 检查是否为特定类型的错误
   */
  isType(errorType: string): boolean {
    return this.type === errorType
  }
}

// 创建 axios 实例
const axiosInstance = axios.create({
  baseURL: config.apiBaseUrl,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
    Accept: 'application/json',
  },
})

// 请求拦截器
axiosInstance.interceptors.request.use(
  requestConfig => {
    // 添加认证 Token
    const token = useAuthStore.getState().token
    if (token) {
      requestConfig.headers.Authorization = `Bearer ${token}`
    }

    // 添加语言偏好头，后端根据此头返回对应语言的错误消息
    requestConfig.headers['Accept-Language'] = i18n.language

    return requestConfig
  },
  error => {
    return Promise.reject(error)
  }
)

// 响应拦截器
axiosInstance.interceptors.response.use(
  // 成功响应：直接返回
  response => response,

  // 错误响应：统一处理
  async (error: AxiosError<ApiErrorResponse>) => {
    // 网络错误
    if (!error.response) {
      if (error.message === 'Network Error') {
        throw new ApiError('NetworkError', i18n.t('networkError', { ns: 'errors', defaultValue: '网络连接失败，请检查网络设置' }))
      }
      throw new ApiError('UnknownError', error.message)
    }

    const { status, data } = error.response

    // 401 未授权
    if (status === 401) {
      // 非登录接口的 401，执行登出
      if (!error.config?.url?.includes('/user/login')) {
        const sessionMessage =
          data?.message || i18n.t('sessionExpired', { ns: 'errors', defaultValue: '登录已过期，请重新登录' })
        try {
          sessionStorage.setItem('auth_error', sessionMessage)
        } catch {
          // ignore storage errors
        }
        useAuthStore.getState().logout()
        window.location.href = '/#/login'
      }
      // 使用后端返回的本地化消息，或使用前端翻译
      throw new ApiError(
        data?.error || 'UnauthorizedError',
        data?.message || i18n.t('unauthorized', { ns: 'errors', defaultValue: '未授权访问' }),
        data?.detail
      )
    }

    // 后端返回了标准错误格式
    if (data?.error && data?.message) {
      throw new ApiError(data.error, data.message, data.detail, data.data)
    }

    // 兜底处理
    throw new ApiError(
      'UnknownError',
      i18n.t('serverError', { ns: 'errors', defaultValue: '服务器内部错误' }),
      error.message
    )
  }
)

export default axiosInstance
