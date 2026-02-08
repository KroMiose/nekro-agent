import axios from '../axios'

export interface CloudPreset {
  remote_id: string
  is_local: boolean
  name: string
  title: string
  avatar: string
  content: string
  description: string
  tags: string
  author: string
  create_time: string
  update_time: string
}

export interface CloudPresetListResponse {
  total: number
  items: CloudPreset[]
  page: number
  page_size: number
  total_pages: number
}

export interface ActionResponse {
  ok: boolean
}

export const presetsMarketApi = {
  /**
   * 获取云端人设列表
   */
  getList: async (params: {
    page: number
    page_size: number
    keyword?: string
    tag?: string
  }): Promise<CloudPresetListResponse> => {
    const response = await axios.get<CloudPresetListResponse>('/cloud/presets-market/list', { params })
    return response.data
  },

  /**
   * 下载云端人设到本地
   */
  downloadPreset: async (remote_id: string): Promise<ActionResponse> => {
    const response = await axios.post<ActionResponse>(`/cloud/presets-market/download/${remote_id}`)
    return response.data
  },
}
