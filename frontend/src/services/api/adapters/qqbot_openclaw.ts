import axios from '../axios'

export interface QQBotOpenClawStatus {
  configured: boolean
  running: boolean
  connected: boolean
  app_id: string
  session_id: string | null
  last_seq: number | null
  self_user_id: string | null
  last_connected_at: number | null
  last_error: string | null
  ref_index_entries: number
  onboarding_url: string
  onboarding_qr_url: string
}

export interface QQBotOpenClawActionResult {
  success: boolean
  message: string
  detail: Record<string, unknown> | null
}

export const qqbotOpenClawApi = {
  getStatus: async () => {
    const { data } = await axios.get<QQBotOpenClawStatus>('/adapters/qqbot_openclaw/maintenance/status')
    return data
  },
  restartGateway: async () => {
    const { data } = await axios.post<QQBotOpenClawActionResult>('/adapters/qqbot_openclaw/maintenance/restart')
    return data
  },
  clearRefIndex: async () => {
    const { data } = await axios.post<QQBotOpenClawActionResult>('/adapters/qqbot_openclaw/maintenance/clear-ref-index')
    return data
  },
  clearSession: async () => {
    const { data } = await axios.post<QQBotOpenClawActionResult>('/adapters/qqbot_openclaw/maintenance/clear-session')
    return data
  },
  testToken: async () => {
    const { data } = await axios.post<QQBotOpenClawActionResult>('/adapters/qqbot_openclaw/maintenance/test-token')
    return data
  },
}
