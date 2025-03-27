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
  pageSize: number
  totalPages: number
}

export interface ApiResponse<T> {
  code: number
  msg: string
  data: T
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
    allow_nsfw?: boolean
  }): Promise<CloudPresetListResponse> => {
    try {
      const response = await axios.get<{
        code: number
        msg: string
        data: CloudPresetListResponse
      }>('/cloud/presets-market/list', { params })
      return response.data.data
    } catch (error) {
      console.error('获取云端人设列表失败:', error)
      throw error
    }
  },

  /**
   * 下载云端人设到本地
   */
  downloadPreset: async (remote_id: string): Promise<ApiResponse<null>> => {
    try {
      const response = await axios.post<ApiResponse<null>>(
        `/cloud/presets-market/download/${remote_id}`
      )
      return response.data
    } catch (error) {
      console.error('下载云端人设失败:', error)
      throw error
    }
  },
}
