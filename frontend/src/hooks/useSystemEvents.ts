/**
 * useSystemEvents — 全局系统事件 SSE 订阅 hook
 *
 * 订阅 GET /api/events/stream，解析以下事件类型：
 * - workspace_status: {type, workspace_id, status, name, container_name?, host_port?}
 * - workspace_cc_active: {type, workspace_id, active, max_duration_ms}
 *
 * 返回：
 * - workspaceStatuses: Map<workspaceId, WorkspaceStatusSnapshot> — 由 SSE 驱动的实时状态覆盖
 * - workspaceCcActive: Map<workspaceId, boolean> — CC 沙盒当前是否活跃
 */

import { useEffect, useRef, useState } from 'react'
import { createEventStream } from '../services/api/utils/stream'

export type SystemEventWorkspaceStatus = 'active' | 'stopped' | 'failed' | 'deleting'

// ── 事件 payload 接口（与后端 Pydantic 模型对应） ────────────────────────────

interface WorkspaceStatusEvent {
  type: 'workspace_status'
  workspace_id: number
  status: SystemEventWorkspaceStatus
  name: string
  container_name?: string | null
  host_port?: number | null
}

interface WorkspaceCcActiveEvent {
  type: 'workspace_cc_active'
  workspace_id: number
  active: boolean
  max_duration_ms: number
}

type SystemEvent = WorkspaceStatusEvent | WorkspaceCcActiveEvent

// ── 状态快照接口 ──────────────────────────────────────────────────────────────

export interface WorkspaceStatusSnapshot {
  status: SystemEventWorkspaceStatus
  container_name?: string | null
  host_port?: number | null
}

export interface SystemEvents {
  workspaceStatuses: Map<number, WorkspaceStatusSnapshot>
  workspaceCcActive: Map<number, boolean>
}

// TTL 用于 cc_active：若 max_duration_ms 后未收到 active=false，自动清除
const DEFAULT_CC_ACTIVE_TTL = 300_000

export function useSystemEvents(): SystemEvents {
  const [workspaceStatuses, setWorkspaceStatuses] = useState<Map<number, WorkspaceStatusSnapshot>>(new Map())
  const [workspaceCcActive, setWorkspaceCcActive] = useState<Map<number, boolean>>(new Map())

  // 用 ref 记录各工作区的 CC active TTL timer，防止内存泄漏
  const ccTimers = useRef<Map<number, ReturnType<typeof setTimeout>>>(new Map())

  useEffect(() => {
    const cancel = createEventStream({
      endpoint: '/events/stream',
      onMessage: (data: string) => {
        if (!data || data === ': ping') return
        try {
          const event = JSON.parse(data) as SystemEvent
          if (!event.type) return

          if (event.type === 'workspace_status') {
            const wsId = event.workspace_id
            setWorkspaceStatuses(prev => {
              const next = new Map(prev)
              next.set(wsId, {
                status: event.status,
                container_name: event.container_name ?? prev.get(wsId)?.container_name,
                host_port: event.host_port ?? prev.get(wsId)?.host_port,
              })
              return next
            })
          } else if (event.type === 'workspace_cc_active') {
            const wsId = event.workspace_id
            const active = event.active
            const ttl = event.max_duration_ms ?? DEFAULT_CC_ACTIVE_TTL

            // 清除旧 timer
            const oldTimer = ccTimers.current.get(wsId)
            if (oldTimer !== undefined) clearTimeout(oldTimer)

            setWorkspaceCcActive(prev => new Map(prev).set(wsId, active))

            if (active) {
              // active=true 时设置 TTL，超时后自动降为 false（防止 active=false 丢失）
              const timer = setTimeout(() => {
                setWorkspaceCcActive(prev => {
                  const next = new Map(prev)
                  next.set(wsId, false)
                  return next
                })
                ccTimers.current.delete(wsId)
              }, ttl)
              ccTimers.current.set(wsId, timer)
            } else {
              ccTimers.current.delete(wsId)
            }
          }
        } catch {
          // 忽略解析失败（keep-alive 等非 JSON 数据）
        }
      },
      onReconnect: () => {
        // 重连后状态由后续事件驱动更新，无需主动清除
      },
    })

    // 在 effect 内捕获 ref 当前值，供 cleanup 使用（避免 react-hooks/exhaustive-deps 警告）
    const timersRef = ccTimers.current
    return () => {
      cancel()
      for (const timer of timersRef.values()) clearTimeout(timer)
      timersRef.clear()
    }
  }, [])

  return { workspaceStatuses, workspaceCcActive }
}
