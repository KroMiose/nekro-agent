import axios from '../axios'

export interface FavoriteResource {
  id: string
  name: string
  title: string
  avatar?: string
  icon?: string
  author: string
  description: string
  moduleName?: string
  hasWebhook?: boolean
}

export interface FavoriteItem {
  id: string
  targetType: string
  targetId: string
  createdAt: number
  resource: FavoriteResource
}

export interface FavoritesListData {
  items: FavoriteItem[]
  total: number
  page: number
  pageSize: number
  totalPages: number
}

export interface FavoritesListResponse {
  success: boolean
  data: FavoritesListData
}

export interface ActionResponse {
  ok: boolean
}

export const favoritesApi = {
  /**
   * 获取收藏列表
   */
  getFavorites: async (params: {
    page: number
    page_size: number
    target_type?: string
  }): Promise<FavoritesListResponse> => {
    const response = await axios.get<FavoritesListResponse>('/cloud/favorites', { params })
    return response.data
  },

  /**
   * 添加收藏
   */
  addFavorite: async (targetType: string, targetId: string): Promise<ActionResponse> => {
    const response = await axios.post<ActionResponse>('/cloud/favorites', {
      targetType,
      targetId,
    })
    return response.data
  },

  /**
   * 取消收藏
   */
  removeFavorite: async (targetType: string, targetId: string): Promise<ActionResponse> => {
    const response = await axios.delete<ActionResponse>('/cloud/favorites', {
      params: { targetType, targetId },
    })
    return response.data
  },
}
