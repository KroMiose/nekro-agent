import axios from './axios'
import { createEventStream } from './utils/stream'

export interface LogEntry {
  timestamp: string
  level: string
  message: string
  source: string
  function: string
  line: number
  subsystem?: string
  plugin_key?: string
}

export interface LogsResponse {
  logs: LogEntry[]
  total: number
}

export const logsApi = {
  getLogs: async (params: { page: number; pageSize: number; source?: string }) => {
    const response = await axios.get<LogsResponse>('/logs', { params })
    return response.data
  },

  getSources: async () => {
    const response = await axios.get<string[]>('/logs/sources')
    return response.data
  },

  streamLogs: (onMessage: (data: string) => void, onError?: (error: Error) => void) => {
    return createEventStream({
      endpoint: '/logs/stream',
      onMessage,
      onError,
    })
  },

  downloadLogs: async (params: { lines?: number; source?: string }) => {
    const response = await axios.get('/logs/download', {
      params,
      responseType: 'blob',
    })

    let filename = 'nekro_agent_logs.txt'
    const contentDisposition = response.headers['content-disposition']
    if (contentDisposition) {
      const filenameMatch = contentDisposition.match(/filename=(.*?)(;|$)/)
      if (filenameMatch && filenameMatch[1]) {
        filename = filenameMatch[1].replace(/"/g, '')
      }
    }

    const blob = new Blob([response.data], { type: 'text/plain' })
    const url = window.URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.setAttribute('download', filename)
    document.body.appendChild(link)
    link.click()

    window.URL.revokeObjectURL(url)
    document.body.removeChild(link)
  },
}
