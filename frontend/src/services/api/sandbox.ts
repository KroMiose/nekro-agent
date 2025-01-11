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
}

export interface SandboxStats {
  total: number
  success: number
  failed: number
  success_rate: number
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
