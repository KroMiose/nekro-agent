import axios from '../axios'

export interface CloudPlugin {
  id: string
  name: string
  moduleName: string
  description: string
  author: string
  hasWebhook: boolean
  homepageUrl: string
  githubUrl: string
  cloneUrl: string
  licenseType: string
  createdAt: string
  updatedAt: string
  is_local: boolean  // 标记是否已存在于本地
  version?: string   // 本地插件版本，如果有
  can_update?: boolean // 标记是否可更新，后端判断
  icon?: string // 插件图标URL或Base64
  isOwner?: boolean // 标记是否为当前用户上传的插件
}

<<<<<<< HEAD
=======
<<<<<<< HEAD
=======
<<<<<<< HEAD
>>>>>>> a776096 (增加PYPI源自定义和代理功能)
>>>>>>> e26199f (增加PYPI源自定义和代理功能)
export interface RepoUser {
  login: string
  avatarUrl: string
  htmlUrl: string
}

export interface RepoLabel {
  name: string
  color: string
}

export interface RepoIssue {
  number: number
  title: string
  state: string
  htmlUrl: string
  createdAt: string
  updatedAt: string
  user: RepoUser
  comments: number
  labels: RepoLabel[]
}

export interface PluginRepoInfo {
  // 基本信息
  fullName: string
  description: string
  htmlUrl: string
  homepage: string

  // 统计数据
  stargazersCount: number
  forksCount: number
  watchersCount: number
  openIssuesCount: number

  // 仓库属性
  language: string
  license: string
  defaultBranch: string

  // 时间信息
  createdAt: string
  updatedAt: string
  pushedAt: string

  // 动态
  recentIssues: RepoIssue[]

  // 快捷链接
  issuesUrl: string
  forksUrl: string
  stargazersUrl: string
}

<<<<<<< HEAD
=======
<<<<<<< HEAD
=======
=======
>>>>>>> 6cf9d37 (增加PYPI源自定义和代理功能)
>>>>>>> a776096 (增加PYPI源自定义和代理功能)
>>>>>>> e26199f (增加PYPI源自定义和代理功能)
export interface CloudPluginListResponse {
  total: number
  items: CloudPlugin[]
  page: number
  pageSize: number
  totalPages: number
}

export interface ApiResponse<T> {
  code: number
  msg: string
  data: T
}

export interface PluginCreateRequest {
  name: string
  moduleName: string
  description: string
  author: string
  hasWebhook: boolean
  homepageUrl?: string
  githubUrl?: string
  cloneUrl?: string
  licenseType?: string
  isSfw?: boolean
  icon?: string // 添加图标字段
}

export interface PluginUpdateRequest {
  name?: string
  description?: string
  author?: string
  hasWebhook?: boolean
  homepageUrl?: string
  githubUrl?: string
  cloneUrl?: string
  licenseType?: string
  isSfw?: boolean
  icon?: string
}

export const pluginsMarketApi = {
  /**
   * 获取云端插件列表
   */
  getList: async (params: {
    page: number
    page_size: number
    keyword?: string
    has_webhook?: boolean
  }): Promise<CloudPluginListResponse> => {
    try {
      const response = await axios.get<{
        code: number
        msg: string
        data: CloudPluginListResponse
      }>('/cloud/plugins-market/list', { params })
      return response.data.data
    } catch (error) {
      console.error('获取云端插件列表失败:', error)
      throw error
    }
  },

  /**
   * 获取用户上传的插件列表
   */
  getUserPlugins: async (): Promise<CloudPlugin[]> => {
    try {
      const response = await axios.get<{
        code: number
        msg: string
        data: CloudPlugin[]
      }>('/cloud/plugins-market/user-plugins')
      
      // 标记用户自己的插件
      const userPlugins = response.data.data.map(plugin => ({
        ...plugin,
        isOwner: true
      }));
      
      return userPlugins;
    } catch (error) {
      console.error('获取用户插件列表失败:', error)
      throw error
    }
  },

  /**
   * 获取插件详情
   */
  getPluginDetail: async (moduleName: string): Promise<CloudPlugin> => {
    try {
      const response = await axios.get<{
        code: number
        msg: string
        data: CloudPlugin
      }>(`/cloud/plugins-market/detail/${moduleName}`)
      return response.data.data
    } catch (error) {
      console.error('获取插件详情失败:', error)
      throw error
    }
  },

  /**
<<<<<<< HEAD
=======
<<<<<<< HEAD
=======
<<<<<<< HEAD
>>>>>>> a776096 (增加PYPI源自定义和代理功能)
>>>>>>> e26199f (增加PYPI源自定义和代理功能)
   * 获取插件仓库信息
   */
  getPluginRepoInfo: async (moduleName: string): Promise<PluginRepoInfo> => {
    try {
      const response = await axios.get<{
        code: number
        msg: string
        data: PluginRepoInfo
      }>(`/cloud/plugins-market/repo/${moduleName}`)
      
      if (response.data.code !== 200) {
        throw new Error(response.data.msg)
      }
      
      return response.data.data
    } catch (error) {
      console.error('获取插件仓库信息失败:', error)
      throw error
    }
  },

  /**
<<<<<<< HEAD
=======
<<<<<<< HEAD
=======
=======
>>>>>>> 6cf9d37 (增加PYPI源自定义和代理功能)
>>>>>>> a776096 (增加PYPI源自定义和代理功能)
>>>>>>> e26199f (增加PYPI源自定义和代理功能)
   * 下载云端插件到本地
   */
  downloadPlugin: async (pluginId: string): Promise<ApiResponse<null>> => {
    try {
      const response = await axios.post<ApiResponse<null>>(
        `/cloud/plugins-market/download/${pluginId}`
      )
      return response.data
    } catch (error) {
      console.error('下载云端插件失败:', error)
      throw error
    }
  },

  /**
   * 更新本地插件
   */
  updatePlugin: async (pluginId: string): Promise<ApiResponse<null>> => {
    try {
      const response = await axios.post<ApiResponse<null>>(
        `/cloud/plugins-market/update/${pluginId}`
      )
      return response.data
    } catch (error) {
      console.error('更新插件失败:', error)
      throw error
    }
  },

  /**
   * 创建插件
   */
  createPlugin: async (data: PluginCreateRequest): Promise<ApiResponse<{id: string}>> => {
    try {
      const response = await axios.post<ApiResponse<{id: string}>>(
        `/cloud/plugins-market/create`,
        data
      )
      return response.data
    } catch (error) {
      console.error('创建插件失败:', error)
      throw error
    }
  },

  /**
   * 更新用户自己的插件信息
   */
  updateUserPlugin: async (moduleName: string, data: PluginUpdateRequest): Promise<ApiResponse<null>> => {
    try {
      const response = await axios.put<ApiResponse<null>>(
        `/cloud/plugins-market/plugin/${moduleName}`,
        data
      )
      return response.data
    } catch (error) {
      console.error(`更新插件 ${moduleName} 失败:`, error)
      throw error
    }
  },

  /**
   * 删除用户自己的插件
   */
  deleteUserPlugin: async (moduleName: string): Promise<ApiResponse<null>> => {
    try {
      const response = await axios.delete<ApiResponse<null>>(
        `/cloud/plugins-market/plugin/${moduleName}`
      )
      return response.data
    } catch (error) {
      console.error(`删除插件 ${moduleName} 失败:`, error)
      throw error
    }
  }
<<<<<<< HEAD
} 
=======
<<<<<<< HEAD
} 
=======
<<<<<<< HEAD
} 
=======
} 
>>>>>>> 6cf9d37 (增加PYPI源自定义和代理功能)
>>>>>>> a776096 (增加PYPI源自定义和代理功能)
>>>>>>> e26199f (增加PYPI源自定义和代理功能)
