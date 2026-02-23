import axios from './axios'

export interface CCModelPresetInfo {
  id: number
  name: string
  description: string
  base_url: string
  auth_token: string
  api_timeout_ms: string
  model_type: 'preset' | 'manual'
  preset_model: string
  anthropic_model: string
  small_fast_model: string
  default_sonnet: string
  default_opus: string
  default_haiku: string
  extra_env: Record<string, string>
  is_default: boolean
  create_time: string
  update_time: string
  config_json: Record<string, unknown>
}

export interface CCModelPresetCreate {
  name: string
  description?: string
  base_url?: string
  auth_token?: string
  api_timeout_ms?: string
  model_type?: 'preset' | 'manual'
  preset_model?: string
  anthropic_model?: string
  small_fast_model?: string
  default_sonnet?: string
  default_opus?: string
  default_haiku?: string
  extra_env?: Record<string, string>
}

export type CCModelPresetUpdate = Partial<CCModelPresetCreate>

export const ccModelPresetApi = {
  getList: async (): Promise<CCModelPresetInfo[]> => {
    const res = await axios.get<{ total: number; items: CCModelPresetInfo[] }>('/cc-model-presets/list')
    return res.data.items
  },
  create: async (body: CCModelPresetCreate): Promise<CCModelPresetInfo> => {
    const res = await axios.post<CCModelPresetInfo>('/cc-model-presets', body)
    return res.data
  },
  update: async (id: number, body: CCModelPresetUpdate): Promise<CCModelPresetInfo> => {
    const res = await axios.patch<CCModelPresetInfo>(`/cc-model-presets/${id}`, body)
    return res.data
  },
  delete: async (id: number): Promise<void> => {
    await axios.delete(`/cc-model-presets/${id}`)
  },
}
