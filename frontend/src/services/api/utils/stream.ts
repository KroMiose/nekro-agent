import { EventSourceMessage, fetchEventSource } from '@microsoft/fetch-event-source'
import { useAuthStore } from '../../../stores/auth'
import { config } from '../../../config/env'

export interface StreamOptions {
  onMessage?: (data: string) => void
  onEvent?: (eventName: string, data: string) => void
  onError?: (error: Error) => void
  /** SSE 连接断开后自动重连成功时触发（首次连接不触发） */
  onReconnect?: () => void
  endpoint: string
  baseUrl?: string
  method?: 'GET' | 'POST'
  body?: Record<string, unknown>
  signal?: AbortSignal
  autoReconnect?: boolean
}

export interface SharedStreamSubscriber {
  onMessage: (data: string) => void
  onError?: (error: Error) => void
}

/**
 * 创建一个 EventSource 流式连接
 * @param options 配置选项
 * @returns 取消函数
 */
export const createEventStream = (options: StreamOptions) => {
  const {
    onMessage,
    onEvent,
    onError,
    onReconnect,
    endpoint,
    baseUrl = config.apiBaseUrl,
    method = 'GET',
    body,
    signal,
    autoReconnect = true,
  } = options

  if (!baseUrl) throw new Error('API 基础 URL 未配置')

  const controller = new AbortController()
  const token = useAuthStore.getState().token
  if (!token) {
    throw new Error('未登录')
  }

  let isFirstOpen = true
  let retryDelayMs = 1000
  let errorReported = false

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
      openWhenHidden: false,
      async onopen() {
        retryDelayMs = 1000
        if (isFirstOpen) {
          isFirstOpen = false
        } else {
          // 重连成功：通知调用方补发丢失的消息
          onReconnect?.()
        }
      },
      onmessage(ev: EventSourceMessage) {
        onEvent?.(ev.event || 'message', ev.data)
        onMessage?.(ev.data)
      },
      onerror(err: Error) {
        if (signal?.aborted || controller.signal.aborted) return
        errorReported = true
        if (onError) onError(err)
        if (!autoReconnect) throw err
        const currentDelay = retryDelayMs
        retryDelayMs = Math.min(retryDelayMs * 2, 5000)
        return currentDelay
      },
      onclose() {
        if (signal?.aborted || controller.signal.aborted || autoReconnect) return
        throw new Error('SSE connection closed')
      },
    }).catch(err => {
      if (signal?.aborted || controller.signal.aborted) return
      if (!errorReported && onError && err instanceof Error) {
        onError(err)
      }
    })

    // 返回取消函数
    return () => {
      if (!signal) {
        controller.abort()
      }
    }
  } catch (_error) {
    throw new Error('无法连接到流式服务')
  }
}

interface SharedEventStreamManager {
  subscribe: (subscriber: SharedStreamSubscriber) => () => void
}

interface SharedEventStreamOptions {
  endpoint: string
  baseUrl?: string
  method?: 'GET' | 'POST'
  body?: Record<string, unknown>
  closeDelayMs?: number
}

export const createSharedEventStreamManager = (options: SharedEventStreamOptions): SharedEventStreamManager => {
  const {
    endpoint,
    baseUrl,
    method,
    body,
    closeDelayMs = 1000,
  } = options

  const subscribers = new Set<SharedStreamSubscriber>()
  let closeTimer: ReturnType<typeof setTimeout> | null = null
  let cleanup: (() => void) | null = null

  const ensureConnected = () => {
    if (cleanup !== null) return
    cleanup = createEventStream({
      endpoint,
      baseUrl,
      method,
      body,
      onMessage: (data) => {
        for (const subscriber of subscribers) {
          subscriber.onMessage(data)
        }
      },
      onError: (error) => {
        for (const subscriber of subscribers) {
          subscriber.onError?.(error)
        }
      },
    })
  }

  const scheduleClose = () => {
    if (closeTimer !== null) clearTimeout(closeTimer)
    closeTimer = setTimeout(() => {
      if (subscribers.size > 0) return
      cleanup?.()
      cleanup = null
      closeTimer = null
    }, closeDelayMs)
  }

  return {
    subscribe(subscriber) {
      if (closeTimer !== null) {
        clearTimeout(closeTimer)
        closeTimer = null
      }
      subscribers.add(subscriber)
      ensureConnected()

      return () => {
        subscribers.delete(subscriber)
        if (subscribers.size === 0) {
          scheduleClose()
        }
      }
    },
  }
}
