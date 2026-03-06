/**
 * useSystemEvents — 全局系统事件 SSE 订阅 hook（Snapshot + Delta 模式）
 *
 * 订阅 GET /api/events/stream，连接建立时后端先推送 type=snapshot 全量快照，
 * 之后持续推送增量 delta 事件。断线重连时同样先收到 snapshot，自动恢复状态。
 *
 * 事件类型：
 * - snapshot: {type, data: {domain: {key: value}}}  — 全量状态快照
 * - workspace_status: {type, workspace_id, status, name, ...}
 * - workspace_cc_active: {type, workspace_id, active, max_duration_ms}
 *
 * 返回值保持稳定接口，新增 domain 只需在本 hook 中扩展 handler 即可。
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

/** 后端 snapshot 事件的 data 结构：domain → key → value */
interface SnapshotData {
  workspace_status?: Record<string, {
    workspace_id: number
    status: SystemEventWorkspaceStatus
    name: string
    container_name?: string | null
    host_port?: number | null
  }>
  workspace_cc_active?: Record<string, {
    workspace_id: number
    active: boolean
    max_duration_ms: number
  }>
  // 未来新增 domain 在此扩展
  [domain: string]: Record<string, Record<string, unknown>> | undefined
}

interface SnapshotEvent {
  type: 'snapshot'
  data: SnapshotData
}

type SystemEvent = WorkspaceStatusEvent | WorkspaceCcActiveEvent | SnapshotEvent

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

  const ccTimers = useRef<Map<number, ReturnType<typeof setTimeout>>>(new Map())

  useEffect(() => {
    /**
     * 从 snapshot 的 workspace_status domain 恢复 workspaceStatuses Map
     */
    const applySnapshotStatuses = (entries: NonNullable<SnapshotData['workspace_status']>) => {
      const next = new Map<number, WorkspaceStatusSnapshot>()
      for (const val of Object.values(entries)) {
        next.set(val.workspace_id, {
          status: val.status,
          container_name: val.container_name,
          host_port: val.host_port,
        })
      }
      setWorkspaceStatuses(next)
    }

    /**
     * 从 snapshot 的 workspace_cc_active domain 恢复 workspaceCcActive Map，
     * 并为所有 active=true 的工作区重建 TTL timer。
     */
    const applySnapshotCcActive = (entries: NonNullable<SnapshotData['workspace_cc_active']>) => {
      // 清除所有旧 timer
      for (const timer of ccTimers.current.values()) clearTimeout(timer)
      ccTimers.current.clear()

      const next = new Map<number, boolean>()
      for (const val of Object.values(entries)) {
        next.set(val.workspace_id, val.active)
        if (val.active) {
          const ttl = val.max_duration_ms ?? DEFAULT_CC_ACTIVE_TTL
          const wsId = val.workspace_id
          const timer = setTimeout(() => {
            setWorkspaceCcActive(prev => new Map(prev).set(wsId, false))
            ccTimers.current.delete(wsId)
          }, ttl)
          ccTimers.current.set(wsId, timer)
        }
      }
      setWorkspaceCcActive(next)
    }

    const cancel = createEventStream({
      endpoint: '/events/stream',
      onMessage: (data: string) => {
        if (!data || data === ': ping') return
        try {
          const event = JSON.parse(data) as SystemEvent
          if (!event.type) return

          // ── snapshot：全量状态恢复 ──
          if (event.type === 'snapshot') {
            const snapData = event.data
            if (snapData.workspace_status) {
              applySnapshotStatuses(snapData.workspace_status)
            }
            if (snapData.workspace_cc_active) {
              applySnapshotCcActive(snapData.workspace_cc_active)
            }
            return
          }

          // ── delta：增量更新（原有逻辑） ──
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

            const oldTimer = ccTimers.current.get(wsId)
            if (oldTimer !== undefined) clearTimeout(oldTimer)

            setWorkspaceCcActive(prev => new Map(prev).set(wsId, active))

            if (active) {
              const timer = setTimeout(() => {
                setWorkspaceCcActive(prev => new Map(prev).set(wsId, false))
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
        // 重连后后端会自动推送 snapshot 全量快照，无需额外处理
      },
    })

    const timersRef = ccTimers.current
    return () => {
      cancel()
      for (const timer of timersRef.values()) clearTimeout(timer)
      timersRef.clear()
    }
  }, [])

  return { workspaceStatuses, workspaceCcActive }
}
