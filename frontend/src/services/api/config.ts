import axios from './axios'

export interface ConfigItem {
  key: string
  value: string
  title: string
  placeholder?: string
  type?: string
  enum?: string[]
  is_secret?: boolean
  ref_model_groups?: boolean
  is_hidden?: boolean
}

export interface BatchUpdateConfigRequest {
  configs: Record<string, string>
}

export interface ModelGroupConfig {
  CHAT_MODEL: string
  CHAT_PROXY: string
  BASE_URL: string
  API_KEY: string
}

export const configApi = {
  getConfigList: async () => {
    const response = await axios.get<{ data: ConfigItem[] }>('/config/list')
    return response.data.data
  },

  getConfig: async (key: string) => {
    const response = await axios.get<{ data: ConfigItem }>('/config/get', { params: { key } })
    return response.data.data
  },

  setConfig: async (key: string, value: string) => {
    const response = await axios.post<{ msg: string }>('/config/set', null, {
      params: { key, value },
    })
    return response.data.msg
  },

  batchUpdateConfig: async (configs: Record<string, string>) => {
    const response = await axios.post<{ msg: string }>('/config/batch', { configs })
    return response.data.msg
  },

  reloadConfig: async () => {
    const response = await axios.post<{ msg: string }>('/config/reload')
    return response.data.msg
  },

  saveConfig: async () => {
    const response = await axios.post<{ msg: string }>('/config/save')
    return response.data.msg
  },

  getModelGroups: async () => {
    const response = await axios.get<{ data: Record<string, ModelGroupConfig> }>(
      '/config/model-groups'
    )
    return response.data.data
  },

  updateModelGroup: async (groupName: string, config: ModelGroupConfig) => {
    const response = await axios.post<{ msg: string }>(`/config/model-groups/${groupName}`, config)
    return response.data.msg
  },

  deleteModelGroup: async (groupName: string) => {
    const response = await axios.delete<{ msg: string }>(`/config/model-groups/${groupName}`)
    return response.data.msg
  },
}
