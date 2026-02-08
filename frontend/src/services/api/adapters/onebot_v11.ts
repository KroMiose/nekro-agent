import axios from '../axios'
import { createEventStream } from '../utils/stream'

export interface ContainerStatus {
  running: boolean
  started_at: string
}

export interface TokenResponse {
  token: string | null
}

export interface ActionResponse {
  ok: boolean
}

export const oneBotV11Api = {
  /**
   * 获取容器状态
   */
  getContainerStatus: async () => {
    const { data } = await axios.get<ContainerStatus>('/adapters/onebot_v11/container/status')
    return data
  },

  /**
   * 获取历史日志
   */
  getContainerLogs: async (tail = 500) => {
    const { data } = await axios.get<string[]>('/adapters/onebot_v11/container/logs', {
      params: { tail },
    })
    return data
  },

  /**
   * 获取实时日志流
   */
  streamContainerLogs: (onMessage: (data: string) => void, onError?: (error: Error) => void) => {
    return createEventStream({
      endpoint: '/adapters/onebot_v11/container/logs/stream',
      onMessage,
      onError,
    })
  },

  /**
   * 重启容器
   */
  restartContainer: async () => {
    const { data } = await axios.post<ActionResponse>('/adapters/onebot_v11/container/restart')
    return data.ok
  },

  /**
   * 获取OneBot访问令牌
   */
  getOneBotToken: async () => {
    const { data } = await axios.get<TokenResponse>('/adapters/onebot_v11/container/onebot-token')
    return data.token
  },

  /**
   * 获取NapCat WebUI访问令牌
   */
  getNapcatToken: async () => {
    const { data } = await axios.get<TokenResponse>('/adapters/onebot_v11/container/napcat-token')
    return data.token
  },
}
