import axios from './axios'
import { useAuthStore } from '../../stores/auth'
import { config } from '../../config/env'

export interface NapCatStatus {
  running: boolean
  started_at: string
}

export const napCatApi = {
  /**
   * 获取容器状态
   */
  getStatus: async () => {
    const { data } = await axios.get<{ data: NapCatStatus }>('/napcat/status')
    return data.data
  },

  /**
   * 获取历史日志
   */
  getLogs: async (tail = 500) => {
    const { data } = await axios.get<{ data: string[] }>('/napcat/logs', {
      params: { tail },
    })
    return data.data
  },

  /**
   * 获取实时日志流
   */
  streamLogs: () => {
    const token = useAuthStore.getState().token
    if (!token) throw new Error('未登录')

    const apiBaseUrl = config.apiBaseUrl
    if (!apiBaseUrl) throw new Error('API 基础 URL 未配置')

    try {
      let baseUrl = apiBaseUrl
      if (!baseUrl.startsWith('http://') && !baseUrl.startsWith('https://')) {
        baseUrl = `http://${baseUrl}`
      }
      baseUrl = baseUrl.replace(/\/$/, '')

      const url = new URL(`${baseUrl}/napcat/logs/stream`)
      url.searchParams.set('token', token)
      
      return new EventSource(url.toString())
    } catch (error) {
      console.error('构造 URL 失败:', error)
      throw new Error('无法连接到日志流服务')
    }
  },

  /**
   * 重启容器
   */
  restart: async () => {
    const { data } = await axios.post<{ data: boolean }>('/napcat/restart')
    return data.data
  },

  getOneBotToken: async () => {
    const { data } = await axios.get<{ data: string | null }>('/napcat/onebot-token')
    return data.data
  },
}
