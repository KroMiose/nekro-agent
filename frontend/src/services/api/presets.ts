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

<<<<<<< HEAD
=======
<<<<<<< HEAD
=======
<<<<<<< HEAD
>>>>>>> a776096 (增加PYPI源自定义和代理功能)
>>>>>>> e26199f (增加PYPI源自定义和代理功能)
export interface TagInfo {
  tag: string
  count: number
}

<<<<<<< HEAD
=======
<<<<<<< HEAD
=======
=======
>>>>>>> 6cf9d37 (增加PYPI源自定义和代理功能)
>>>>>>> a776096 (增加PYPI源自定义和代理功能)
>>>>>>> e26199f (增加PYPI源自定义和代理功能)
export const presetsApi = {
  getList: async (params: {
    page: number
    page_size: number
    search?: string
    tag?: string
<<<<<<< HEAD
    tags?: string
=======
<<<<<<< HEAD
    tags?: string
=======
<<<<<<< HEAD
    tags?: string
=======
>>>>>>> 6cf9d37 (增加PYPI源自定义和代理功能)
>>>>>>> a776096 (增加PYPI源自定义和代理功能)
>>>>>>> e26199f (增加PYPI源自定义和代理功能)
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
<<<<<<< HEAD
      const response = await axios.post<ApiResponse<ShareResponse>>(`/presets/${id}/share`, null, {
        params: { is_sfw },
      })
=======
<<<<<<< HEAD
      const response = await axios.post<ApiResponse<ShareResponse>>(`/presets/${id}/share`, null, {
        params: { is_sfw },
      })
=======
<<<<<<< HEAD
      const response = await axios.post<ApiResponse<ShareResponse>>(`/presets/${id}/share`, null, {
        params: { is_sfw },
      })
=======
      const response = await axios.post<ApiResponse<ShareResponse>>(
        `/presets/${id}/share`, 
        null, 
        { params: { is_sfw } }
      )
>>>>>>> 6cf9d37 (增加PYPI源自定义和代理功能)
>>>>>>> a776096 (增加PYPI源自定义和代理功能)
>>>>>>> e26199f (增加PYPI源自定义和代理功能)
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
<<<<<<< HEAD
      const response = await axios.post<ApiResponse<null>>(`/presets/${id}/sync-to-cloud`, null, {
        params: { is_sfw },
      })
=======
<<<<<<< HEAD
      const response = await axios.post<ApiResponse<null>>(`/presets/${id}/sync-to-cloud`, null, {
        params: { is_sfw },
      })
=======
<<<<<<< HEAD
      const response = await axios.post<ApiResponse<null>>(`/presets/${id}/sync-to-cloud`, null, {
        params: { is_sfw },
      })
=======
      const response = await axios.post<ApiResponse<null>>(
        `/presets/${id}/sync-to-cloud`, 
        null, 
        { params: { is_sfw } }
      )
>>>>>>> 6cf9d37 (增加PYPI源自定义和代理功能)
>>>>>>> a776096 (增加PYPI源自定义和代理功能)
>>>>>>> e26199f (增加PYPI源自定义和代理功能)
      return response.data
    } catch (error) {
      console.error('同步到云端失败:', error)
      throw error
    }
  },
<<<<<<< HEAD
=======
<<<<<<< HEAD
=======
<<<<<<< HEAD
>>>>>>> a776096 (增加PYPI源自定义和代理功能)
>>>>>>> e26199f (增加PYPI源自定义和代理功能)

  refreshSharedStatus: async () => {
    try {
      const response = await axios.post<ApiResponse<RefreshStatusResponse>>(
        '/presets/refresh-shared-status'
      )
<<<<<<< HEAD
=======
<<<<<<< HEAD
=======
=======
  
  refreshSharedStatus: async () => {
    try {
      const response = await axios.post<ApiResponse<RefreshStatusResponse>>('/presets/refresh-shared-status')
>>>>>>> 6cf9d37 (增加PYPI源自定义和代理功能)
>>>>>>> a776096 (增加PYPI源自定义和代理功能)
>>>>>>> e26199f (增加PYPI源自定义和代理功能)
      return response.data
    } catch (error) {
      console.error('刷新共享状态失败:', error)
      throw error
    }
  },
<<<<<<< HEAD
=======
<<<<<<< HEAD
=======
<<<<<<< HEAD
>>>>>>> a776096 (增加PYPI源自定义和代理功能)
>>>>>>> e26199f (增加PYPI源自定义和代理功能)

  getTags: async (): Promise<TagInfo[]> => {
    try {
      const response = await axios.get<ApiResponse<TagInfo[]>>('/presets/tags')
      return response.data.data
    } catch (error) {
      console.error('获取标签列表失败:', error)
      throw error
    }
  },
<<<<<<< HEAD
=======
<<<<<<< HEAD
=======
=======
>>>>>>> 6cf9d37 (增加PYPI源自定义和代理功能)
>>>>>>> a776096 (增加PYPI源自定义和代理功能)
>>>>>>> e26199f (增加PYPI源自定义和代理功能)
}
