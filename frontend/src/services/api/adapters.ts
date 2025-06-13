import axios from './axios'

export interface AdapterInfo {
  key: string
  name: string
  description: string
  status: string // loaded, failed, disabled
  config_class: string
  chat_key_rules: string[]
  has_config: boolean
  version: string
  author: string
  tags: string[]
}

export interface AdapterDetailInfo extends AdapterInfo {
  config_path: string
  has_router: boolean
  router_prefix: string
}

export interface AdapterStatus {
  status: string
  loaded: boolean
  initialized: boolean
  has_config: boolean
  config_file_exists?: boolean
  error_message?: string
}

export interface AdapterDocs {
  content: string
  exists: boolean
}

export const adaptersApi = {
  // 获取所有适配器列表
  getAdaptersList: async (): Promise<AdapterInfo[]> => {
    const response = await axios.get<{ data: AdapterInfo[] }>('/adapters/list')
    return response.data.data
  },

  // 获取指定适配器详细信息
  getAdapterInfo: async (adapterKey: string): Promise<AdapterDetailInfo> => {
    const response = await axios.get<{ data: AdapterDetailInfo }>(`/adapters/${adapterKey}/info`)
    return response.data.data
  },

  // 获取适配器状态
  getAdapterStatus: async (adapterKey: string): Promise<AdapterStatus> => {
    const response = await axios.get<{ data: AdapterStatus }>(`/adapters/${adapterKey}/status`)
    return response.data.data
  },

  // 获取适配器文档
  getAdapterDocs: async (adapterKey: string): Promise<AdapterDocs> => {
    const response = await axios.get<{ data: AdapterDocs }>(`/adapters/${adapterKey}/docs`)
    return response.data.data
  },
}
