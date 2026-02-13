import { EventSourceMessage, fetchEventSource } from '@microsoft/fetch-event-source'
import { useAuthStore } from '../../../stores/auth'
import { config } from '../../../config/env'

export interface StreamOptions {
  onMessage: (data: string) => void
  onError?: (error: Error) => void
  endpoint: string
  baseUrl?: string
  method?: 'GET' | 'POST'
  body?: Record<string, unknown>
  signal?: AbortSignal
}

/**
 * 创建一个 EventSource 流式连接
 * @param options 配置选项
 * @returns 取消函数
 */
export const createEventStream = (options: StreamOptions) => {
  const {
    onMessage,
    onError,
    endpoint,
    baseUrl = config.apiBaseUrl,
    method = 'GET',
    body,
    signal,
  } = options

  if (!baseUrl) throw new Error('API 基础 URL 未配置')

  const controller = new AbortController()
  const token = useAuthStore.getState().token
  if (!token) {
    throw new Error('未登录')
  }

  try {
    // 创建 EventSource 连接
    fetchEventSource(`${baseUrl}${endpoint}`, {
      method,
      signal: signal || controller.signal,
      headers: {
        Authorization: `Bearer ${token}`,
        'Content-Type': 'application/json',
        Accept: 'text/event-stream',
      },
      body: body ? JSON.stringify(body) : undefined,
      openWhenHidden: true,
      onmessage(ev: EventSourceMessage) {
        onMessage(ev.data)
      },
      onerror(err: Error) {
        if (signal?.aborted || controller.signal.aborted) return
        if (onError) onError(err)
        controller.abort()
        return
      },
    }).catch(err => {
      if (onError && err instanceof Error) {
        onError(err)
      }
    })

    // 返回取消函数
    return () => {
      if (!signal) {
        controller.abort()
      }
    }
  } catch (error) {
    throw new Error('无法连接到流式服务')
  }
}
