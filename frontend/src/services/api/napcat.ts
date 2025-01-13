import axios from './axios'
import { createEventStream } from './utils/stream'

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
  streamLogs: (onMessage: (data: string) => void, onError?: (error: Error) => void) => {
    return createEventStream({
      endpoint: '/napcat/logs/stream',
      onMessage,
      onError,
    })
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
