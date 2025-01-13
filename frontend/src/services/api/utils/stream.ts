import { EventSourceMessage, fetchEventSource } from '@microsoft/fetch-event-source'
import { useAuthStore } from '../../../stores/auth'
import { config } from '../../../config/env'

export interface StreamOptions {
  onMessage: (data: string) => void
  onError?: (error: Error) => void
  endpoint: string
  baseUrl?: string
}

/**
 * 创建一个 EventSource 流式连接
 * @param options 配置选项
 * @returns 取消函数
 */
export const createEventStream = (options: StreamOptions) => {
  const { onMessage, onError, endpoint, baseUrl = config.apiBaseUrl } = options

  if (!baseUrl) throw new Error('API 基础 URL 未配置')

  const controller = new AbortController()
  const token = useAuthStore.getState().token
  if (!token) {
    throw new Error('未登录')
  }

  try {
    // 处理基础 URL
    let normalizedBaseUrl = baseUrl
    if (!normalizedBaseUrl.startsWith('http://') && !normalizedBaseUrl.startsWith('https://')) {
      normalizedBaseUrl = `http://${normalizedBaseUrl}`
    }
    normalizedBaseUrl = normalizedBaseUrl.replace(/\/$/, '')

    // 构造完整 URL
    const url = new URL(`${normalizedBaseUrl}${endpoint}`)
    url.searchParams.set('token', `Bearer ${token}`)

    // 创建 EventSource 连接
    fetchEventSource(url.toString(), {
      signal: controller.signal,
      headers: {
        'Content-Type': 'text/event-stream',
        Accept: 'text/event-stream',
      },
      onmessage(ev: EventSourceMessage) {
        onMessage(ev.data)
      },
      onerror(err: Error) {
        console.error('EventSource error:', err)
        if (onError) onError(err)
        throw err // 重试连接
      },
    }).catch(console.error)

    // 返回取消函数
    return () => {
      controller.abort()
    }
  } catch (error) {
    console.error('构造 URL 失败:', error)
    throw new Error('无法连接到流式服务')
  }
}
