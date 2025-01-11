import axios from './axios'
import { config } from '../../config/env'
import { useAuthStore } from '../../stores/auth'

export interface LogEntry {
  timestamp: string
  level: string
  message: string
  source: string
  function: string
  line: number
}

export interface LogsResponse {
  logs: LogEntry[]
  total: number
}

export const logsApi = {
  getLogs: async (params: { page: number; pageSize: number; source?: string }) => {
    const response = await axios.get<{ data: LogsResponse }>('/logs', { params })
    return response.data.data
  },

  getSources: async () => {
    const response = await axios.get<{ data: string[] }>('/logs/sources')
    return response.data.data
  },

  streamLogs: () => {
    // 获取认证token
    const token = useAuthStore.getState().token
    if (!token) {
      throw new Error('No authentication token found')
    }

    // 创建带token的URL
    const url = new URL(`${config.apiBaseUrl}/logs/stream`, window.location.origin)
    url.searchParams.set('token', token)

    // 创建 EventSource 连接
    const eventSource = new EventSource(url.toString())

    // 添加错误处理
    eventSource.onerror = error => {
      console.error('EventSource error:', error)
    }

    return eventSource
  },
}
