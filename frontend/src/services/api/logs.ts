import axios from './axios'
import { createEventStream } from './utils/stream'

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

  streamLogs: (onMessage: (data: string) => void, onError?: (error: Error) => void) => {
    return createEventStream({
      endpoint: '/logs/stream',
      onMessage,
      onError,
    })
  },

  downloadLogs: async (params: { lines?: number; source?: string }) => {
    try {
      // 使用axios发送请求获取日志内容，保持鉴权状态
      const response = await axios.get('/logs/download', {
        params,
        responseType: 'blob', // 指定响应类型为blob
      })

      // 获取文件名 (从Content-Disposition头)
      let filename = 'nekro_agent_logs.txt'
      const contentDisposition = response.headers['content-disposition']
      if (contentDisposition) {
        const filenameMatch = contentDisposition.match(/filename=(.*?)(;|$)/)
        if (filenameMatch && filenameMatch[1]) {
          filename = filenameMatch[1].replace(/"/g, '')
        }
      }

      // 创建Blob对象
      const blob = new Blob([response.data], { type: 'text/plain' })

      // 创建下载链接并触发下载
      const url = window.URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      link.setAttribute('download', filename)
      document.body.appendChild(link)
      link.click()

      // 清理
      window.URL.revokeObjectURL(url)
      document.body.removeChild(link)
    } catch (error) {
      console.error('下载日志失败:', error)
      throw error
    }
  },
}
