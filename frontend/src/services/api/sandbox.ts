import axios from './axios'

export interface SandboxCodeExtData {
  message_cnt: number
  token_consumption: number
  token_input: number
  token_output: number
  chars_count_input: number
  chars_count_output: number
  chars_count_total: number
  use_model: string
  speed_tokens_per_second: number
  speed_chars_per_second: number
  first_token_cost_ms: number
  generation_time_ms: number
  stream_mode: boolean
  log_path: string
}

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
  use_model: string
  extra_data: string | null
}

// 停止类型枚举
export enum ExecStopType {
  NORMAL = 0, // 正常结束
  ERROR = 1, // 错误停止
  TIMEOUT = 2, // 超时停止
  AGENT = 8, // 代理停止
  MANUAL = 9, // 手动停止
  MULTIMODAL_AGENT = 11, // 多模态代理停止
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

  getLogContent: async (log_path: string) => {
    const response = await axios.get('/sandbox/log-content', {
      params: { log_path },
    })
    return response.data
  },

  getStats: async () => {
    const response = await axios.get<{ data: SandboxStats }>('/sandbox/stats')
    return response.data.data
  },
}
