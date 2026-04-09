/**
 * useSystemEvents — 全局系统事件 SSE 订阅 hook（Snapshot + Delta 模式）
 *
 * 订阅 GET /api/events/stream，连接建立时后端先推送 type=snapshot 全量快照，
 * 之后持续推送增量 delta 事件。断线重连时同样先收到 snapshot，自动恢复状态。
 */

import { useEffect, useRef, useState } from 'react'
import { createSharedEventStreamManager } from '../services/api/utils/stream'

export type SystemEventWorkspaceStatus = 'active' | 'stopped' | 'failed' | 'deleting'

interface WorkspaceStatusPayload {
  workspace_id: number
  status: SystemEventWorkspaceStatus
  name: string
  container_name?: string | null
  host_port?: number | null
}

interface WorkspaceCcActivePayload {
  workspace_id: number
  active: boolean
  name?: string | null
  started_at: number
  max_duration_ms: number
}

interface WorkspaceCcRuntimeStatusPayload {
  workspace_id: number
  active: boolean
  name?: string | null
  started_at: number
  updated_at: number
  phase: 'queued' | 'running' | 'responding' | 'completed' | 'failed' | 'cancelled'
  current_tool?: string | null
  source_chat_key?: string | null
  queue_length: number
  operation_block_count: number
  last_block_kind?: 'tool_call' | 'tool_result' | 'text_chunk' | null
  last_block_summary?: string | null
  error_summary?: string | null
}

interface AgentActivePayload {
  chat_key: string
  active: boolean
  channel_name?: string | null
  chat_type?: string | null
  preset_id?: number | null
  preset_name?: string | null
  started_at: number
  max_duration_ms: number
}

interface AgentRuntimePhasePayload {
  chat_key: string
  active: boolean
  channel_name?: string | null
  chat_type?: string | null
  preset_id?: number | null
  preset_name?: string | null
  started_at: number
  updated_at: number
  phase: 'llm_generating' | 'llm_retrying' | 'sandbox_running' | 'sandbox_stopped' | 'iterating' | 'completed' | 'failed'
  iteration_index: number
  iteration_total: number
  llm_retry_index: number
  llm_retry_total: number
  sandbox_stop_type?: number | null
  model_name?: string | null
  error_summary?: string | null
}

interface MemoryRecallMatchedNode {
  memory_type: 'paragraph' | 'relation' | 'episode'
  id: number
  score: number
}

interface MemoryRecallActivityPayload {
  workspace_id: number
  chat_key: string
  active: boolean
  phase: 'query_built' | 'retrieving' | 'compiled' | 'applied'
  request_id: string
  target_kind: 'na_history' | 'cc_handshake'
  focus_text: string
  query_text: string
  channel_name?: string | null
  started_at: number
  expires_in_ms: number
  hit_count: number
  applied_count: number
  matched_nodes: MemoryRecallMatchedNode[]
  query_embedding_time_ms: number
  search_time_ms: number
}

interface KbIndexProgressPayload {
  workspace_id: number
  document_id: number
  active: boolean
  title: string
  source_path: string
  phase: 'queued' | 'extracting' | 'chunking' | 'embedding' | 'upserting' | 'ready' | 'failed'
  started_at: number
  updated_at: number
  progress_percent: number
  total_chunks: number
  processed_chunks: number
  expires_in_ms: number
  error_summary: string
}

interface WorkspaceStatusEvent extends WorkspaceStatusPayload {
  type: 'workspace_status'
}

interface WorkspaceCcActiveEvent extends WorkspaceCcActivePayload {
  type: 'workspace_cc_active'
}

interface WorkspaceCcRuntimeStatusEvent extends WorkspaceCcRuntimeStatusPayload {
  type: 'workspace_cc_runtime_status'
}

interface AgentActiveEvent extends AgentActivePayload {
  type: 'agent_active'
}

interface AgentRuntimeStatusEvent extends AgentRuntimePhasePayload {
  type: 'agent_runtime_status'
}

interface MemoryRecallActivityEvent extends MemoryRecallActivityPayload {
  type: 'memory_recall_activity'
}

interface KbIndexProgressEvent extends KbIndexProgressPayload {
  type: 'kb_index_progress'
}

interface SnapshotData {
  workspace_status?: Record<string, WorkspaceStatusPayload>
  workspace_cc_active?: Record<string, WorkspaceCcActivePayload>
  workspace_cc_runtime_status?: Record<string, WorkspaceCcRuntimeStatusPayload>
  agent_active?: Record<string, AgentActivePayload>
  agent_runtime_status?: Record<string, AgentRuntimePhasePayload>
  memory_recall_activity?: Record<string, MemoryRecallActivityPayload>
  kb_index_progress?: Record<string, KbIndexProgressPayload>
}

interface SnapshotEvent {
  type: 'snapshot'
  data: SnapshotData
}

type SystemEvent =
  | WorkspaceStatusEvent
  | WorkspaceCcActiveEvent
  | WorkspaceCcRuntimeStatusEvent
  | AgentActiveEvent
  | AgentRuntimeStatusEvent
  | MemoryRecallActivityEvent
  | KbIndexProgressEvent
  | SnapshotEvent

export interface WorkspaceStatusSnapshot {
  status: SystemEventWorkspaceStatus
  name: string
  container_name?: string | null
  host_port?: number | null
}

export interface WorkspaceCcActiveInfo {
  active: true
  name?: string | null
  started_at: number
  max_duration_ms: number
}

export interface WorkspaceCcRuntimeStatusInfo {
  workspace_id: number
  name?: string | null
  started_at: number
  updated_at: number
  phase: 'queued' | 'running' | 'responding' | 'completed' | 'failed' | 'cancelled'
  current_tool?: string | null
  source_chat_key?: string | null
  queue_length: number
  operation_block_count: number
  last_block_kind?: 'tool_call' | 'tool_result' | 'text_chunk' | null
  last_block_summary?: string | null
  error_summary?: string | null
}

export interface AgentActiveInfo {
  chat_key: string
  channel_name?: string | null
  chat_type?: string | null
  preset_id?: number | null
  preset_name?: string | null
  started_at: number
  max_duration_ms: number
}

export interface AgentRuntimeStatusInfo {
  chat_key: string
  channel_name?: string | null
  chat_type?: string | null
  preset_id?: number | null
  preset_name?: string | null
  started_at: number
  updated_at: number
  phase: 'llm_generating' | 'llm_retrying' | 'sandbox_running' | 'sandbox_stopped' | 'iterating' | 'completed' | 'failed'
  iteration_index: number
  iteration_total: number
  llm_retry_index: number
  llm_retry_total: number
  sandbox_stop_type?: number | null
  model_name?: string | null
  error_summary?: string | null
}

export interface MemoryRecallActivityInfo {
  workspace_id: number
  chat_key: string
  phase: 'query_built' | 'retrieving' | 'compiled' | 'applied'
  request_id: string
  target_kind: 'na_history' | 'cc_handshake'
  focus_text: string
  query_text: string
  channel_name?: string | null
  started_at: number
  expires_in_ms: number
  hit_count: number
  applied_count: number
  matched_nodes: MemoryRecallMatchedNode[]
  query_embedding_time_ms: number
  search_time_ms: number
}

export interface KbIndexProgressInfo {
  workspace_id: number
  document_id: number
  title: string
  source_path: string
  phase: 'queued' | 'extracting' | 'chunking' | 'embedding' | 'upserting' | 'ready' | 'failed'
  started_at: number
  updated_at: number
  progress_percent: number
  total_chunks: number
  processed_chunks: number
  expires_in_ms: number
  error_summary: string
}

export interface SystemEvents {
  workspaceStatuses: Map<number, WorkspaceStatusSnapshot>
  workspaceCcActive: Map<number, WorkspaceCcActiveInfo>
  workspaceCcRuntimeStatuses: Map<number, WorkspaceCcRuntimeStatusInfo>
  agentActives: Map<string, AgentActiveInfo>
  agentRuntimeStatuses: Map<string, AgentRuntimeStatusInfo>
  memoryRecallActivities: Map<string, MemoryRecallActivityInfo>
  kbIndexProgresses: Map<string, KbIndexProgressInfo>
}

export const EMPTY_SYSTEM_EVENTS: SystemEvents = {
  workspaceStatuses: new Map(),
  workspaceCcActive: new Map(),
  workspaceCcRuntimeStatuses: new Map(),
  agentActives: new Map(),
  agentRuntimeStatuses: new Map(),
  memoryRecallActivities: new Map(),
  kbIndexProgresses: new Map(),
}

const DEFAULT_TTL = 300_000
const DEFAULT_MEMORY_RECALL_TTL = 8000
const systemEventsStreamManager = createSharedEventStreamManager({
  endpoint: '/events/stream',
  closeDelayMs: 1500,
})

function normalizeStartedAt(startedAt: number | undefined, fallbackNow: number): number {
  return typeof startedAt === 'number' && startedAt > 0 ? startedAt : fallbackNow
}

function getRemainingMs(startedAt: number, ttlMs: number, now: number): number {
  return startedAt + ttlMs - now
}

export function useSystemEvents(): SystemEvents {
  const [workspaceStatuses, setWorkspaceStatuses] = useState<Map<number, WorkspaceStatusSnapshot>>(new Map())
  const [workspaceCcActive, setWorkspaceCcActive] = useState<Map<number, WorkspaceCcActiveInfo>>(new Map())
  const [workspaceCcRuntimeStatuses, setWorkspaceCcRuntimeStatuses] = useState<Map<number, WorkspaceCcRuntimeStatusInfo>>(new Map())
  const [agentActives, setAgentActives] = useState<Map<string, AgentActiveInfo>>(new Map())
  const [agentRuntimeStatuses, setAgentRuntimeStatuses] = useState<Map<string, AgentRuntimeStatusInfo>>(new Map())
  const [memoryRecallActivities, setMemoryRecallActivities] = useState<Map<string, MemoryRecallActivityInfo>>(new Map())
  const [kbIndexProgresses, setKbIndexProgresses] = useState<Map<string, KbIndexProgressInfo>>(new Map())

  const ccTimers = useRef<Map<number, ReturnType<typeof setTimeout>>>(new Map())
  const agentTimers = useRef<Map<string, ReturnType<typeof setTimeout>>>(new Map())
  const recallTimers = useRef<Map<string, ReturnType<typeof setTimeout>>>(new Map())
  const kbIndexTimers = useRef<Map<string, ReturnType<typeof setTimeout>>>(new Map())

  useEffect(() => {
    const clearTimers = <T,>(timers: Map<T, ReturnType<typeof setTimeout>>) => {
      for (const timer of timers.values()) clearTimeout(timer)
      timers.clear()
    }

    const scheduleWorkspaceCcExpiry = (workspaceId: number, info: WorkspaceCcActiveInfo, now: number) => {
      const remaining = getRemainingMs(info.started_at, info.max_duration_ms, now)
      if (remaining <= 0) {
        return false
      }
      const timer = setTimeout(() => {
        setWorkspaceCcActive(prev => {
          const next = new Map(prev)
          next.delete(workspaceId)
          return next
        })
        ccTimers.current.delete(workspaceId)
      }, remaining)
      ccTimers.current.set(workspaceId, timer)
      return true
    }

    const scheduleAgentExpiry = (chatKey: string, info: AgentActiveInfo, now: number) => {
      const remaining = getRemainingMs(info.started_at, info.max_duration_ms, now)
      if (remaining <= 0) {
        return false
      }
      const timer = setTimeout(() => {
        setAgentActives(prev => {
          const next = new Map(prev)
          next.delete(chatKey)
          return next
        })
        agentTimers.current.delete(chatKey)
      }, remaining)
      agentTimers.current.set(chatKey, timer)
      return true
    }

    const scheduleRecallExpiry = (key: string, startedAt: number, ttlMs: number, requestId: string, now: number) => {
      const remaining = getRemainingMs(startedAt, ttlMs, now)
      if (remaining <= 0) {
        return false
      }
      const timer = setTimeout(() => {
        setMemoryRecallActivities(prev => {
          const next = new Map(prev)
          const current = next.get(key)
          if (current?.request_id === requestId) {
            next.delete(key)
          }
          return next
        })
        recallTimers.current.delete(key)
      }, remaining)
      recallTimers.current.set(key, timer)
      return true
    }

    const applySnapshotStatuses = (entries: Record<string, WorkspaceStatusPayload>) => {
      const next = new Map<number, WorkspaceStatusSnapshot>()
      for (const value of Object.values(entries)) {
        next.set(value.workspace_id, {
          status: value.status,
          name: value.name,
          container_name: value.container_name,
          host_port: value.host_port,
        })
      }
      setWorkspaceStatuses(next)
    }

    const applySnapshotCcActive = (entries: Record<string, WorkspaceCcActivePayload>) => {
      clearTimers(ccTimers.current)
      const next = new Map<number, WorkspaceCcActiveInfo>()
      const now = Date.now()
      for (const value of Object.values(entries)) {
        if (!value.active) continue
        const startedAt = normalizeStartedAt(value.started_at, now)
        const info: WorkspaceCcActiveInfo = {
          active: true,
          name: value.name,
          started_at: startedAt,
          max_duration_ms: value.max_duration_ms ?? DEFAULT_TTL,
        }
        if (scheduleWorkspaceCcExpiry(value.workspace_id, info, now)) {
          next.set(value.workspace_id, info)
        }
      }
      setWorkspaceCcActive(next)
    }

    const applySnapshotCcRuntimeStatuses = (entries: Record<string, WorkspaceCcRuntimeStatusPayload>) => {
      const next = new Map<number, WorkspaceCcRuntimeStatusInfo>()
      const now = Date.now()
      for (const value of Object.values(entries)) {
        if (!value.active) continue
        next.set(value.workspace_id, {
          workspace_id: value.workspace_id,
          name: value.name,
          started_at: normalizeStartedAt(value.started_at, now),
          updated_at: value.updated_at,
          phase: value.phase,
          current_tool: value.current_tool,
          source_chat_key: value.source_chat_key,
          queue_length: value.queue_length ?? 0,
          operation_block_count: value.operation_block_count ?? 0,
          last_block_kind: value.last_block_kind,
          last_block_summary: value.last_block_summary,
          error_summary: value.error_summary,
        })
      }
      setWorkspaceCcRuntimeStatuses(next)
    }

    const applySnapshotAgentActives = (entries: Record<string, AgentActivePayload>) => {
      clearTimers(agentTimers.current)
      const next = new Map<string, AgentActiveInfo>()
      const now = Date.now()
      for (const value of Object.values(entries)) {
        if (!value.active) continue
        const info: AgentActiveInfo = {
          chat_key: value.chat_key,
          channel_name: value.channel_name,
          chat_type: value.chat_type,
          preset_id: value.preset_id,
          preset_name: value.preset_name,
          started_at: normalizeStartedAt(value.started_at, now),
          max_duration_ms: value.max_duration_ms ?? DEFAULT_TTL,
        }
        if (scheduleAgentExpiry(value.chat_key, info, now)) {
          next.set(value.chat_key, info)
        }
      }
      setAgentActives(next)
    }

    const applySnapshotAgentRuntimeStatuses = (entries: Record<string, AgentRuntimePhasePayload>) => {
      const next = new Map<string, AgentRuntimeStatusInfo>()
      for (const value of Object.values(entries)) {
        if (!value.active) continue
        next.set(value.chat_key, {
          chat_key: value.chat_key,
          channel_name: value.channel_name,
          chat_type: value.chat_type,
          preset_id: value.preset_id,
          preset_name: value.preset_name,
          started_at: value.started_at,
          updated_at: value.updated_at,
          phase: value.phase,
          iteration_index: value.iteration_index,
          iteration_total: value.iteration_total,
          llm_retry_index: value.llm_retry_index,
          llm_retry_total: value.llm_retry_total,
          sandbox_stop_type: value.sandbox_stop_type,
          model_name: value.model_name,
          error_summary: value.error_summary,
        })
      }
      setAgentRuntimeStatuses(next)
    }

    const applySnapshotMemoryRecall = (entries: Record<string, MemoryRecallActivityPayload>) => {
      clearTimers(recallTimers.current)
      const next = new Map<string, MemoryRecallActivityInfo>()
      const now = Date.now()
      for (const value of Object.values(entries)) {
        if (!value.active) continue
        const ttlMs = value.expires_in_ms ?? DEFAULT_MEMORY_RECALL_TTL
        const startedAt = normalizeStartedAt(value.started_at, now)
        const key = `${value.workspace_id}:${value.chat_key}`
        const info: MemoryRecallActivityInfo = {
          workspace_id: value.workspace_id,
          chat_key: value.chat_key,
          phase: value.phase,
          request_id: value.request_id,
          target_kind: value.target_kind,
          focus_text: value.focus_text,
          query_text: value.query_text,
          channel_name: value.channel_name,
          started_at: startedAt,
          expires_in_ms: ttlMs,
          hit_count: value.hit_count ?? 0,
          applied_count: value.applied_count ?? 0,
          matched_nodes: value.matched_nodes ?? [],
          query_embedding_time_ms: value.query_embedding_time_ms ?? 0,
          search_time_ms: value.search_time_ms ?? 0,
        }
        if (scheduleRecallExpiry(key, startedAt, ttlMs, value.request_id, now)) {
          next.set(key, info)
        }
      }
      setMemoryRecallActivities(next)
    }

    const scheduleKbIndexExpiry = (key: string, startedAt: number, ttlMs: number, now: number) => {
      const remaining = getRemainingMs(startedAt, ttlMs, now)
      if (remaining <= 0) {
        return false
      }
      const timer = setTimeout(() => {
        setKbIndexProgresses(prev => {
          const next = new Map(prev)
          next.delete(key)
          return next
        })
        kbIndexTimers.current.delete(key)
      }, remaining)
      kbIndexTimers.current.set(key, timer)
      return true
    }

    const applySnapshotKbIndexProgress = (entries: Record<string, KbIndexProgressPayload>) => {
      clearTimers(kbIndexTimers.current)
      const next = new Map<string, KbIndexProgressInfo>()
      const now = Date.now()
      for (const value of Object.values(entries)) {
        if (!value.active) continue
        const key = `${value.workspace_id}:${value.document_id}`
        const ttlMs = value.expires_in_ms ?? DEFAULT_MEMORY_RECALL_TTL
        const startedAt = normalizeStartedAt(value.started_at, now)
        const info: KbIndexProgressInfo = {
          workspace_id: value.workspace_id,
          document_id: value.document_id,
          title: value.title,
          source_path: value.source_path,
          phase: value.phase,
          started_at: startedAt,
          updated_at: value.updated_at,
          progress_percent: value.progress_percent ?? 0,
          total_chunks: value.total_chunks ?? 0,
          processed_chunks: value.processed_chunks ?? 0,
          expires_in_ms: ttlMs,
          error_summary: value.error_summary ?? '',
        }
        if (value.phase === 'ready' || value.phase === 'failed') {
          if (scheduleKbIndexExpiry(key, startedAt, ttlMs, now)) {
            next.set(key, info)
          }
        } else {
          next.set(key, info)
        }
      }
      setKbIndexProgresses(next)
    }

    const handleWorkspaceCcActiveDelta = (event: WorkspaceCcActiveEvent) => {
      const workspaceId = event.workspace_id
      const oldTimer = ccTimers.current.get(workspaceId)
      if (oldTimer !== undefined) clearTimeout(oldTimer)
      ccTimers.current.delete(workspaceId)

      if (!event.active) {
        setWorkspaceCcActive(prev => {
          const next = new Map(prev)
          next.delete(workspaceId)
          return next
        })
        return
      }

      const now = Date.now()
      const info: WorkspaceCcActiveInfo = {
        active: true,
        name: event.name,
        started_at: normalizeStartedAt(event.started_at, now),
        max_duration_ms: event.max_duration_ms ?? DEFAULT_TTL,
      }
      if (!scheduleWorkspaceCcExpiry(workspaceId, info, now)) {
        setWorkspaceCcActive(prev => {
          const next = new Map(prev)
          next.delete(workspaceId)
          return next
        })
        return
      }
      setWorkspaceCcActive(prev => new Map(prev).set(workspaceId, info))
    }

    const handleWorkspaceCcRuntimeStatusDelta = (event: WorkspaceCcRuntimeStatusEvent) => {
      const workspaceId = event.workspace_id
      if (!event.active) {
        setWorkspaceCcRuntimeStatuses(prev => {
          const next = new Map(prev)
          next.delete(workspaceId)
          return next
        })
        return
      }
      const now = Date.now()
      setWorkspaceCcRuntimeStatuses(prev => new Map(prev).set(workspaceId, {
        workspace_id: workspaceId,
        name: event.name,
        started_at: normalizeStartedAt(event.started_at, now),
        updated_at: event.updated_at,
        phase: event.phase,
        current_tool: event.current_tool,
        source_chat_key: event.source_chat_key,
        queue_length: event.queue_length ?? 0,
        operation_block_count: event.operation_block_count ?? 0,
        last_block_kind: event.last_block_kind,
        last_block_summary: event.last_block_summary,
        error_summary: event.error_summary,
      }))
    }

    const handleAgentActiveDelta = (event: AgentActiveEvent) => {
      const chatKey = event.chat_key
      const oldTimer = agentTimers.current.get(chatKey)
      if (oldTimer !== undefined) clearTimeout(oldTimer)
      agentTimers.current.delete(chatKey)

      if (!event.active) {
        setAgentActives(prev => {
          const next = new Map(prev)
          next.delete(chatKey)
          return next
        })
        return
      }

      const now = Date.now()
      const info: AgentActiveInfo = {
        chat_key: chatKey,
        channel_name: event.channel_name,
        chat_type: event.chat_type,
        preset_id: event.preset_id,
        preset_name: event.preset_name,
        started_at: normalizeStartedAt(event.started_at, now),
        max_duration_ms: event.max_duration_ms ?? DEFAULT_TTL,
      }
      if (!scheduleAgentExpiry(chatKey, info, now)) {
        setAgentActives(prev => {
          const next = new Map(prev)
          next.delete(chatKey)
          return next
        })
        return
      }
      setAgentActives(prev => new Map(prev).set(chatKey, info))
    }

    const handleAgentRuntimeStatusDelta = (event: AgentRuntimeStatusEvent) => {
      const chatKey = event.chat_key
      if (!event.active) {
        setAgentRuntimeStatuses(prev => {
          const next = new Map(prev)
          next.delete(chatKey)
          return next
        })
        return
      }
      setAgentRuntimeStatuses(prev => new Map(prev).set(chatKey, {
        chat_key: chatKey,
        channel_name: event.channel_name,
        chat_type: event.chat_type,
        preset_id: event.preset_id,
        preset_name: event.preset_name,
        started_at: event.started_at,
        updated_at: event.updated_at,
        phase: event.phase,
        iteration_index: event.iteration_index,
        iteration_total: event.iteration_total,
        llm_retry_index: event.llm_retry_index,
        llm_retry_total: event.llm_retry_total,
        sandbox_stop_type: event.sandbox_stop_type,
        model_name: event.model_name,
        error_summary: event.error_summary,
      }))
    }

    const handleMemoryRecallDelta = (event: MemoryRecallActivityEvent) => {
      const key = `${event.workspace_id}:${event.chat_key}`
      const oldTimer = recallTimers.current.get(key)
      if (oldTimer !== undefined) clearTimeout(oldTimer)
      recallTimers.current.delete(key)

      if (!event.active) {
        setMemoryRecallActivities(prev => {
          const next = new Map(prev)
          next.delete(key)
          return next
        })
        return
      }

      const now = Date.now()
      const ttlMs = event.expires_in_ms ?? DEFAULT_MEMORY_RECALL_TTL
      const startedAt = normalizeStartedAt(event.started_at, now)
      const info: MemoryRecallActivityInfo = {
        workspace_id: event.workspace_id,
        chat_key: event.chat_key,
        phase: event.phase,
        request_id: event.request_id,
        target_kind: event.target_kind,
        focus_text: event.focus_text,
        query_text: event.query_text,
        channel_name: event.channel_name,
        started_at: startedAt,
        expires_in_ms: ttlMs,
        hit_count: event.hit_count ?? 0,
        applied_count: event.applied_count ?? 0,
        matched_nodes: event.matched_nodes ?? [],
        query_embedding_time_ms: event.query_embedding_time_ms ?? 0,
        search_time_ms: event.search_time_ms ?? 0,
      }
      if (!scheduleRecallExpiry(key, startedAt, ttlMs, event.request_id, now)) {
        setMemoryRecallActivities(prev => {
          const next = new Map(prev)
          next.delete(key)
          return next
        })
        return
      }
      setMemoryRecallActivities(prev => new Map(prev).set(key, info))
    }

    const handleKbIndexProgressDelta = (event: KbIndexProgressEvent) => {
      const key = `${event.workspace_id}:${event.document_id}`
      const oldTimer = kbIndexTimers.current.get(key)
      if (oldTimer !== undefined) clearTimeout(oldTimer)
      kbIndexTimers.current.delete(key)

      if (!event.active) {
        setKbIndexProgresses(prev => {
          const next = new Map(prev)
          next.delete(key)
          return next
        })
        return
      }

      const now = Date.now()
      const ttlMs = event.expires_in_ms ?? DEFAULT_MEMORY_RECALL_TTL
      const startedAt = normalizeStartedAt(event.started_at, now)
      const info: KbIndexProgressInfo = {
        workspace_id: event.workspace_id,
        document_id: event.document_id,
        title: event.title,
        source_path: event.source_path,
        phase: event.phase,
        started_at: startedAt,
        updated_at: event.updated_at,
        progress_percent: event.progress_percent ?? 0,
        total_chunks: event.total_chunks ?? 0,
        processed_chunks: event.processed_chunks ?? 0,
        expires_in_ms: ttlMs,
        error_summary: event.error_summary ?? '',
      }
      if (event.phase === 'ready' || event.phase === 'failed') {
        if (!scheduleKbIndexExpiry(key, startedAt, ttlMs, now)) {
          setKbIndexProgresses(prev => {
            const next = new Map(prev)
            next.delete(key)
            return next
          })
          return
        }
      }
      setKbIndexProgresses(prev => new Map(prev).set(key, info))
    }

    const cancel = systemEventsStreamManager.subscribe({
      onMessage: (data: string) => {
        if (!data || data === ': ping') return
        try {
          const event = JSON.parse(data) as SystemEvent
          if (!event.type) return

          if (event.type === 'snapshot') {
            const snapshot = event.data
            applySnapshotStatuses(snapshot.workspace_status ?? {})
            applySnapshotCcActive(snapshot.workspace_cc_active ?? {})
            applySnapshotCcRuntimeStatuses(snapshot.workspace_cc_runtime_status ?? {})
            applySnapshotAgentActives(snapshot.agent_active ?? {})
            applySnapshotAgentRuntimeStatuses(snapshot.agent_runtime_status ?? {})
            applySnapshotMemoryRecall(snapshot.memory_recall_activity ?? {})
            applySnapshotKbIndexProgress(snapshot.kb_index_progress ?? {})
            return
          }

          if (event.type === 'workspace_status') {
            const workspaceId = event.workspace_id
            setWorkspaceStatuses(prev => new Map(prev).set(workspaceId, {
              status: event.status,
              name: event.name,
              container_name: event.container_name ?? prev.get(workspaceId)?.container_name,
              host_port: event.host_port ?? prev.get(workspaceId)?.host_port,
            }))
            return
          }

          if (event.type === 'workspace_cc_active') {
            handleWorkspaceCcActiveDelta(event)
            return
          }

          if (event.type === 'workspace_cc_runtime_status') {
            handleWorkspaceCcRuntimeStatusDelta(event)
            return
          }

          if (event.type === 'agent_active') {
            handleAgentActiveDelta(event)
            return
          }

          if (event.type === 'agent_runtime_status') {
            handleAgentRuntimeStatusDelta(event)
            return
          }

          if (event.type === 'memory_recall_activity') {
            handleMemoryRecallDelta(event)
            return
          }

          if (event.type === 'kb_index_progress') {
            handleKbIndexProgressDelta(event)
          }
        } catch {
          // 忽略 keep-alive 等非 JSON 数据
        }
      },
      onError: () => {
        // 共享流统一重连；当前 hook 无需额外错误处理
      },
    })

    const ccTimersRef = ccTimers.current
    const agentTimersRef = agentTimers.current
    const recallTimersRef = recallTimers.current
    const kbIndexTimersRef = kbIndexTimers.current
    return () => {
      cancel()
      clearTimers(ccTimersRef)
      clearTimers(agentTimersRef)
      clearTimers(recallTimersRef)
      clearTimers(kbIndexTimersRef)
    }
  }, [])

  return {
    workspaceStatuses,
    workspaceCcActive,
    workspaceCcRuntimeStatuses,
    agentActives,
    agentRuntimeStatuses,
    memoryRecallActivities,
    kbIndexProgresses,
  }
}
