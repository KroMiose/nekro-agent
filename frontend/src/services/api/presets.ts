import axios from './axios'

export interface Preset {
  id: number
  remote_id: string | null
  name: string
  title: string
  avatar: string
  description: string
  tags: string
  author: string
  is_remote: boolean
  on_shared: boolean
  create_time: string
  update_time: string
}

export interface PresetDetail extends Preset {
  content: string
}

export interface ApiResponse<T> {
  code: number
  msg: string
  data: T
}

interface ShareResponse {
  remote_id: string
}

interface RefreshStatusResponse {
  updated_count: number
  total_cloud_presets: number
}

export const presetsApi = {
  getList: async (params: {
    page: number
    page_size: number
    search?: string
    tag?: string
    remote_only?: boolean
  }) => {
    const response = await axios.get<{
      data: { total: number; items: Preset[] }
    }>('/presets/list', { params })
    return response.data.data
  },

  getDetail: async (id: number) => {
    const response = await axios.get<{ data: PresetDetail }>(`/presets/${id}`)
    return response.data.data
  },

  create: async (data: {
    name: string
    title?: string
    avatar: string
    content: string
    description?: string
    tags?: string
    author?: string
  }) => {
    const response = await axios.post<{ code: number; msg: string; data: { id: number } }>(
      '/presets',
      data
    )
    return response.data
  },

  update: async (
    id: number,
    data: {
      name: string
      title?: string
      avatar: string
      content: string
      description?: string
      tags?: string
      author?: string
      remove_remote?: boolean
    }
  ) => {
    const response = await axios.put<{ code: number; msg: string }>(`/presets/${id}`, data)
    return response.data
  },

  delete: async (id: number) => {
    const response = await axios.delete<{ code: number; msg: string }>(`/presets/${id}`)
    return response.data
  },

  sync: async (id: number) => {
    try {
      const response = await axios.post<ApiResponse<null>>(`/presets/${id}/sync`)
      return response.data
    } catch (error) {
      console.error('同步失败:', error)
      throw error
    }
  },

  uploadAvatar: async (file: File) => {
    const formData = new FormData()
    formData.append('file', file)
    const response = await axios.post<{ code: number; msg: string; data: { avatar: string } }>(
      '/presets/upload-avatar',
      formData,
      {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      }
    )
    return response.data
  },

  shareToCloud: async (id: number | string, is_sfw: boolean = true) => {
    try {
      const response = await axios.post<ApiResponse<ShareResponse>>(
        `/presets/${id}/share`, 
        null, 
        { params: { is_sfw } }
      )
      return response.data
    } catch (error) {
      console.error('共享人设失败:', error)
      throw error
    }
  },

  unshare: async (id: number) => {
    try {
      const response = await axios.post<ApiResponse<null>>(`/presets/${id}/unshare`)
      return response.data
    } catch (error) {
      console.error('撤回共享失败:', error)
      throw error
    }
  },

  syncToCloud: async (id: number, is_sfw: boolean = true) => {
    try {
      const response = await axios.post<ApiResponse<null>>(
        `/presets/${id}/sync-to-cloud`, 
        null, 
        { params: { is_sfw } }
      )
      return response.data
    } catch (error) {
      console.error('同步到云端失败:', error)
      throw error
    }
  },
  
  refreshSharedStatus: async () => {
    try {
      const response = await axios.post<ApiResponse<RefreshStatusResponse>>('/presets/refresh-shared-status')
      return response.data
    } catch (error) {
      console.error('刷新共享状态失败:', error)
      throw error
    }
  },
}
