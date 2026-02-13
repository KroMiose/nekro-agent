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

export interface PresetListResponse {
  total: number
  items: Preset[]
}

export interface ShareResponse {
  remote_id: string
}

export interface RefreshStatusResponse {
  updated_count: number
  total_cloud_presets: number
}

export interface TagInfo {
  tag: string
  count: number
}

export interface ActionResponse {
  ok: boolean
}

export interface AvatarUploadResponse {
  avatar: string
}

export const presetsApi = {
  getList: async (params: {
    page: number
    page_size: number
    search?: string
    tag?: string
    tags?: string
    remote_only?: boolean
  }): Promise<PresetListResponse> => {
    const response = await axios.get<PresetListResponse>('/presets/list', { params })
    return response.data
  },

  getDetail: async (id: number): Promise<PresetDetail> => {
    const response = await axios.get<PresetDetail>(`/presets/${id}`)
    return response.data
  },

  create: async (data: {
    name: string
    title?: string
    avatar: string
    content: string
    description?: string
    tags?: string
    author?: string
  }): Promise<ActionResponse> => {
    const response = await axios.post<ActionResponse>('/presets', data)
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
  ): Promise<ActionResponse> => {
    const response = await axios.put<ActionResponse>(`/presets/${id}`, data)
    return response.data
  },

  delete: async (id: number): Promise<ActionResponse> => {
    const response = await axios.delete<ActionResponse>(`/presets/${id}`)
    return response.data
  },

  sync: async (id: number): Promise<ActionResponse> => {
    const response = await axios.post<ActionResponse>(`/presets/${id}/sync`)
    return response.data
  },

  uploadAvatar: async (file: File): Promise<AvatarUploadResponse> => {
    const formData = new FormData()
    formData.append('file', file)
    const response = await axios.post<AvatarUploadResponse>('/presets/upload-avatar', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    })
    return response.data
  },

  shareToCloud: async (id: number | string, is_sfw: boolean = true): Promise<ShareResponse> => {
    const response = await axios.post<ShareResponse>(`/presets/${id}/share`, null, {
      params: { is_sfw },
    })
    return response.data
  },

  unshare: async (id: number): Promise<ActionResponse> => {
    const response = await axios.post<ActionResponse>(`/presets/${id}/unshare`)
    return response.data
  },

  syncToCloud: async (id: number, is_sfw: boolean = true): Promise<ActionResponse> => {
    const response = await axios.post<ActionResponse>(`/presets/${id}/sync-to-cloud`, null, {
      params: { is_sfw },
    })
    return response.data
  },

  refreshSharedStatus: async (): Promise<RefreshStatusResponse> => {
    const response = await axios.post<RefreshStatusResponse>('/presets/refresh-shared-status')
    return response.data
  },

  getTags: async (): Promise<TagInfo[]> => {
    const response = await axios.get<TagInfo[]>('/presets/tags')
    return response.data
  },
}
