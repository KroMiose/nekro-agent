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

export interface UserPlugin {
  id: string
  name: string
  moduleName: string
}

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

export interface CloudPluginListResponse {
  total: number
  items: CloudPlugin[]
  page: number
  page_size: number
  total_pages: number
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

export interface ActionResponse {
  ok: boolean
}

export interface CreateResponse {
  id: string
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
    const response = await axios.get<CloudPluginListResponse>('/cloud/plugins-market/list', {
      params,
    })
    return response.data
  },

  /**
   * 获取用户上传的插件列表
   */
  getUserPlugins: async (): Promise<UserPlugin[]> => {
    const response = await axios.get<UserPlugin[]>('/cloud/plugins-market/user-plugins')
    return response.data
  },

  /**
   * 获取插件详情
   */
  getPluginDetail: async (moduleName: string): Promise<CloudPlugin> => {
    const response = await axios.get<CloudPlugin>(`/cloud/plugins-market/detail/${moduleName}`)
    return response.data
  },

  /**
   * 获取插件仓库信息
   */
  getPluginRepoInfo: async (moduleName: string): Promise<PluginRepoInfo> => {
    const response = await axios.get<PluginRepoInfo>(`/cloud/plugins-market/repo/${moduleName}`)
    return response.data
  },

  /**
   * 下载云端插件到本地
   */
  downloadPlugin: async (pluginId: string): Promise<ActionResponse> => {
    const response = await axios.post<ActionResponse>(`/cloud/plugins-market/download/${pluginId}`)
    return response.data
  },

  /**
   * 更新本地插件
   */
  updatePlugin: async (pluginId: string): Promise<ActionResponse> => {
    const response = await axios.post<ActionResponse>(`/cloud/plugins-market/update/${pluginId}`)
    return response.data
  },

  /**
   * 创建插件
   */
  createPlugin: async (data: PluginCreateRequest): Promise<CreateResponse> => {
    const response = await axios.post<CreateResponse>(`/cloud/plugins-market/create`, data)
    return response.data
  },

  /**
   * 更新用户自己的插件信息
   */
  updateUserPlugin: async (moduleName: string, data: PluginUpdateRequest): Promise<ActionResponse> => {
    const response = await axios.put<ActionResponse>(`/cloud/plugins-market/plugin/${moduleName}`, data)
    return response.data
  },

  /**
   * 删除用户自己的插件
   */
  deleteUserPlugin: async (moduleName: string): Promise<ActionResponse> => {
    const response = await axios.delete<ActionResponse>(`/cloud/plugins-market/plugin/${moduleName}`)
    return response.data
  }
} 
