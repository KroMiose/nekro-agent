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
}
