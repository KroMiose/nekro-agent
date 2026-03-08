import axios from './axios'

export type TimerTaskType = 'one_shot' | 'recurring'
export type TimerTaskStatus = 'active' | 'paused' | 'error'
export type TimerTaskSource = 'agent' | 'system' | 'unknown'
export type TimerTimeRange = 'all' | 'today' | '24h' | '7d' | 'overdue'
export type TimerSortBy = 'next_run_asc' | 'recent_update' | 'recent_run' | 'error_first'

export interface TimerTaskItem {
  id: string
  task_type: TimerTaskType
  title: string
  event_desc: string
  status: TimerTaskStatus
  workspace_id: number | null
  workspace_name: string | null
  chat_key: string
  channel_name: string | null
  is_primary_channel: boolean
  trigger_at: string | null
  cron_expr: string | null
  timezone: string | null
  workday_mode: string | null
  next_run_at: string | null
  last_run_at: string | null
  consecutive_failures: number
  last_error: string | null
  source: TimerTaskSource
  is_temporary: boolean
  create_time: string | null
  update_time: string | null
  actionable: boolean
}

export interface TimerTaskListResponse {
  total: number
  items: TimerTaskItem[]
}

export interface TimerTaskSummary {
  total: number
  active_recurring: number
  paused: number
  upcoming_24h: number
  errors: number
  workspace_count: number
}

export interface ActionResponse {
  ok: boolean
  message?: string | null
}

export const timersApi = {
  getSummary: async (): Promise<TimerTaskSummary> => {
    const response = await axios.get<TimerTaskSummary>('/timers/summary')
    return response.data
  },

  getList: async (params: {
    search?: string
    workspace_id?: number
    task_type?: TimerTaskType
    status?: TimerTaskStatus
    time_range?: TimerTimeRange
    sort_by?: TimerSortBy
  }): Promise<TimerTaskListResponse> => {
    const response = await axios.get<TimerTaskListResponse>('/timers/list', { params })
    return response.data
  },

  getDetail: async (taskType: TimerTaskType, taskId: string): Promise<TimerTaskItem> => {
    const response = await axios.get<TimerTaskItem>(`/timers/${taskType}/${taskId}`)
    return response.data
  },

  runNow: async (taskType: TimerTaskType, taskId: string): Promise<ActionResponse> => {
    const response = await axios.post<ActionResponse>(`/timers/${taskType}/${taskId}/run-now`)
    return response.data
  },

  pause: async (taskId: string): Promise<ActionResponse> => {
    const response = await axios.post<ActionResponse>(`/timers/recurring/${taskId}/pause`)
    return response.data
  },

  resume: async (taskId: string): Promise<ActionResponse> => {
    const response = await axios.post<ActionResponse>(`/timers/recurring/${taskId}/resume`)
    return response.data
  },

  delete: async (taskType: TimerTaskType, taskId: string): Promise<ActionResponse> => {
    const response = await axios.delete<ActionResponse>(`/timers/${taskType}/${taskId}`)
    return response.data
  },
}
