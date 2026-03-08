/**
 * useSystemEvents — 全局系统事件 SSE 订阅 hook（Snapshot + Delta 模式）
 *
 * 订阅 GET /api/events/stream，连接建立时后端先推送 type=snapshot 全量快照，
 * 之后持续推送增量 delta 事件。断线重连时同样先收到 snapshot，自动恢复状态。
 *
 * 事件类型：
 * - snapshot:            {type, data: {domain: {key: value}}}  — 全量状态快照
 * - workspace_status:    {type, workspace_id, status, name, ...}
 * - workspace_cc_active: {type, workspace_id, active, max_duration_ms}
 * - agent_active:        {type, chat_key, active, channel_name, chat_type, preset_id, preset_name, ...}
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
  name?: string | null
  max_duration_ms: number
}

interface AgentActiveEvent {
  type: 'agent_active'
  chat_key: string
  active: boolean
  channel_name?: string | null
  chat_type?: string | null
  preset_id?: number | null
  preset_name?: string | null
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
    name?: string | null
    max_duration_ms: number
  }>
  agent_active?: Record<string, {
    chat_key: string
    active: boolean
    channel_name?: string | null
    chat_type?: string | null
    preset_id?: number | null
    preset_name?: string | null
    max_duration_ms: number
  }>
  // 未来新增 domain 在此扩展
  [domain: string]: Record<string, Record<string, unknown>> | undefined
}

interface SnapshotEvent {
  type: 'snapshot'
  data: SnapshotData
}

type SystemEvent = WorkspaceStatusEvent | WorkspaceCcActiveEvent | AgentActiveEvent | SnapshotEvent

// ── 状态快照接口 ──────────────────────────────────────────────────────────────

export interface WorkspaceStatusSnapshot {
  status: SystemEventWorkspaceStatus
  name: string
  container_name?: string | null
  host_port?: number | null
}

/** Agent 活跃状态快照，附带前端计时信息 */
export interface AgentActiveInfo {
  chat_key: string
  channel_name?: string | null
  chat_type?: string | null
  preset_id?: number | null
  preset_name?: string | null
  /** 任务开始时的客户端时间戳（ms），用于计算已处理时长 */
  start_time: number
  max_duration_ms: number
}

/** CC 沙盒活跃状态快照 */
export interface WorkspaceCcActiveInfo {
  active: boolean
  name?: string | null
}

export interface SystemEvents {
  workspaceStatuses: Map<number, WorkspaceStatusSnapshot>
  workspaceCcActive: Map<number, WorkspaceCcActiveInfo>
  /** 当前活跃的 Agent 任务，key 为 chat_key */
  agentActives: Map<string, AgentActiveInfo>
}

// TTL 用于 cc_active / agent_active：若超时后未收到 active=false，自动清除
const DEFAULT_TTL = 300_000

export function useSystemEvents(): SystemEvents {
  const [workspaceStatuses, setWorkspaceStatuses] = useState<Map<number, WorkspaceStatusSnapshot>>(new Map())
  const [workspaceCcActive, setWorkspaceCcActive] = useState<Map<number, WorkspaceCcActiveInfo>>(new Map())
  const [agentActives, setAgentActives] = useState<Map<string, AgentActiveInfo>>(new Map())

  const ccTimers = useRef<Map<number, ReturnType<typeof setTimeout>>>(new Map())
  const agentTimers = useRef<Map<string, ReturnType<typeof setTimeout>>>(new Map())

  useEffect(() => {
    // ── snapshot 恢复函数 ─────────────────────────────────────────────────────

    const applySnapshotStatuses = (entries: NonNullable<SnapshotData['workspace_status']>) => {
      const next = new Map<number, WorkspaceStatusSnapshot>()
      for (const val of Object.values(entries)) {
        next.set(val.workspace_id, {
          status: val.status,
          name: val.name,
          container_name: val.container_name,
          host_port: val.host_port,
        })
      }
      setWorkspaceStatuses(next)
    }

    const applySnapshotCcActive = (entries: NonNullable<SnapshotData['workspace_cc_active']>) => {
      for (const timer of ccTimers.current.values()) clearTimeout(timer)
      ccTimers.current.clear()

      const next = new Map<number, WorkspaceCcActiveInfo>()
      for (const val of Object.values(entries)) {
        next.set(val.workspace_id, { active: val.active, name: val.name })
        if (val.active) {
          const ttl = val.max_duration_ms ?? DEFAULT_TTL
          const wsId = val.workspace_id
          const timer = setTimeout(() => {
            setWorkspaceCcActive(prev => new Map(prev).set(wsId, { active: false, name: val.name }))
            ccTimers.current.delete(wsId)
          }, ttl)
          ccTimers.current.set(wsId, timer)
        }
      }
      setWorkspaceCcActive(next)
    }

    const applySnapshotAgentActives = (entries: NonNullable<SnapshotData['agent_active']>) => {
      for (const timer of agentTimers.current.values()) clearTimeout(timer)
      agentTimers.current.clear()

      const next = new Map<string, AgentActiveInfo>()
      const now = Date.now()
      for (const val of Object.values(entries)) {
        if (!val.active) continue
        const info: AgentActiveInfo = {
          chat_key: val.chat_key,
          channel_name: val.channel_name,
          chat_type: val.chat_type,
          preset_id: val.preset_id,
          preset_name: val.preset_name,
          // snapshot 恢复时无法知道确切开始时间，用当前时间替代
          start_time: now,
          max_duration_ms: val.max_duration_ms ?? DEFAULT_TTL,
        }
        next.set(val.chat_key, info)

        const ttl = val.max_duration_ms ?? DEFAULT_TTL
        const chatKey = val.chat_key
        const timer = setTimeout(() => {
          setAgentActives(prev => { const m = new Map(prev); m.delete(chatKey); return m })
          agentTimers.current.delete(chatKey)
        }, ttl)
        agentTimers.current.set(chatKey, timer)
      }
      setAgentActives(next)
    }

    // ── delta 处理函数 ────────────────────────────────────────────────────────

    const handleAgentActiveDelta = (event: AgentActiveEvent) => {
      const chatKey = event.chat_key

      const oldTimer = agentTimers.current.get(chatKey)
      if (oldTimer !== undefined) clearTimeout(oldTimer)
      agentTimers.current.delete(chatKey)

      if (event.active) {
        const info: AgentActiveInfo = {
          chat_key: chatKey,
          channel_name: event.channel_name,
          chat_type: event.chat_type,
          preset_id: event.preset_id,
          preset_name: event.preset_name,
          start_time: Date.now(),
          max_duration_ms: event.max_duration_ms ?? DEFAULT_TTL,
        }
        setAgentActives(prev => new Map(prev).set(chatKey, info))

        const ttl = event.max_duration_ms ?? DEFAULT_TTL
        const timer = setTimeout(() => {
          setAgentActives(prev => { const m = new Map(prev); m.delete(chatKey); return m })
          agentTimers.current.delete(chatKey)
        }, ttl)
        agentTimers.current.set(chatKey, timer)
      } else {
        setAgentActives(prev => { const m = new Map(prev); m.delete(chatKey); return m })
      }
    }

    // ── SSE 主循环 ────────────────────────────────────────────────────────────

    const cancel = createEventStream({
      endpoint: '/events/stream',
      onMessage: (data: string) => {
        if (!data || data === ': ping') return
        try {
          const event = JSON.parse(data) as SystemEvent
          if (!event.type) return

          // snapshot：全量状态恢复
          if (event.type === 'snapshot') {
            const snapData = event.data
            if (snapData.workspace_status) applySnapshotStatuses(snapData.workspace_status)
            if (snapData.workspace_cc_active) applySnapshotCcActive(snapData.workspace_cc_active)
            if (snapData.agent_active) applySnapshotAgentActives(snapData.agent_active)
            return
          }

          // delta：增量更新
          if (event.type === 'workspace_status') {
            const wsId = event.workspace_id
            setWorkspaceStatuses(prev => {
              const next = new Map(prev)
              next.set(wsId, {
                status: event.status,
                name: event.name,
                container_name: event.container_name ?? prev.get(wsId)?.container_name,
                host_port: event.host_port ?? prev.get(wsId)?.host_port,
              })
              return next
            })
          } else if (event.type === 'workspace_cc_active') {
            const wsId = event.workspace_id
            const active = event.active
            const name = event.name ?? null
            const ttl = event.max_duration_ms ?? DEFAULT_TTL

            const oldTimer = ccTimers.current.get(wsId)
            if (oldTimer !== undefined) clearTimeout(oldTimer)

            setWorkspaceCcActive(prev => new Map(prev).set(wsId, { active, name }))

            if (active) {
              const timer = setTimeout(() => {
                setWorkspaceCcActive(prev => new Map(prev).set(wsId, { active: false, name }))
                ccTimers.current.delete(wsId)
              }, ttl)
              ccTimers.current.set(wsId, timer)
            } else {
              ccTimers.current.delete(wsId)
            }
          } else if (event.type === 'agent_active') {
            handleAgentActiveDelta(event)
          }
        } catch {
          // 忽略解析失败（keep-alive 等非 JSON 数据）
        }
      },
      onReconnect: () => {
        // 重连后后端会自动推送 snapshot 全量快照，无需额外处理
      },
    })

    const ccTimersRef = ccTimers.current
    const agentTimersRef = agentTimers.current
    return () => {
      cancel()
      for (const timer of ccTimersRef.values()) clearTimeout(timer)
      ccTimersRef.clear()
      for (const timer of agentTimersRef.values()) clearTimeout(timer)
      agentTimersRef.clear()
    }
  }, [])

  return { workspaceStatuses, workspaceCcActive, agentActives }
}
