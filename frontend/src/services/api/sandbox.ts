import axios from './axios'

export interface SandboxLog {
  id: number
  chat_key: string
  trigger_user_id: number
  trigger_user_name: string
  success: boolean
  code_text: string
  outputs: string
  create_time: string

  // 新增字段
  thought_chain: string | null
  stop_type: number
  exec_time_ms: number
  generation_time_ms: number
  total_time_ms: number
}

// 停止类型枚举
export enum ExecStopType {
  NORMAL = 0,  // 正常结束
  ERROR = 1,   // 错误停止
  TIMEOUT = 2, // 超时停止
  AGENT = 8,   // 代理停止
  MANUAL = 9,  // 手动停止
}

export interface SandboxStats {
  total: number
  success: number
  failed: number
  success_rate: number
  agent_count: number
}

export const sandboxApi = {
  getLogs: async (params: {
    page: number
    page_size: number
    chat_key?: string
    success?: boolean
  }) => {
    const response = await axios.get<{
      data: { total: number; items: SandboxLog[] }
    }>('/sandbox/logs', { params })
    return response.data.data
  },

  getStats: async () => {
    const response = await axios.get<{ data: SandboxStats }>('/sandbox/stats')
    return response.data.data
  },
}
