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
  favoriteCount?: number
  isFavorited?: boolean
}

export interface CloudPresetListResponse {
  total: number
  items: CloudPreset[]
  page: number
  page_size: number
  total_pages: number
}

export interface UserPreset {
  id: string
  name: string
  title: string
  avatar?: string
}

export interface UserPresetListResponse {
  items: UserPreset[]
  total: number
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
   * 获取用户上传的人设列表
   */
  getUserPresets: async (): Promise<UserPresetListResponse> => {
    const response = await axios.get<UserPresetListResponse>('/cloud/presets-market/user-presets')
    return response.data
  },

  /**
   * 获取人设详情
   */
  getPresetDetail: async (remote_id: string): Promise<CloudPreset> => {
    const response = await axios.get<CloudPreset>(`/cloud/presets-market/detail/${remote_id}`)
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
