import axios from './axios'
import { ConfigItem, ModelGroupConfig, ModelTypeOption } from '../../components/common/ConfigTable'

export interface BatchUpdateConfigRequest {
  configs: Record<string, string>
}

export interface ConfigInfo {
  config_key: string
  config_class: string
  config_file_path?: string
  config_type: string
  field_count: number
}

export const unifiedConfigApi = {
  // 获取所有配置键
  getConfigKeys: async (): Promise<string[]> => {
    const response = await axios.get<string[]>('/config/keys')
    return response.data
  },

  // 获取配置基本信息
  getConfigInfo: async (configKey: string): Promise<ConfigInfo> => {
    const response = await axios.get<ConfigInfo>(`/config/info/${configKey}`)
    return response.data
  },

  // 获取指定配置的配置列表
  getConfigList: async (configKey: string): Promise<ConfigItem[]> => {
    const response = await axios.get<ConfigItem[]>(`/config/list/${configKey}`)
    return response.data
  },

  // 获取指定配置的配置项
  getConfigItem: async (configKey: string, itemKey: string): Promise<ConfigItem> => {
    const response = await axios.get<ConfigItem>(`/config/get/${configKey}/${itemKey}`)
    return response.data
  },

  // 设置指定配置的配置项值
  setConfigValue: async (configKey: string, itemKey: string, value: string): Promise<void> => {
    await axios.post(`/config/set/${configKey}/${itemKey}`, null, {
      params: { value },
    })
  },

  // 批量更新指定配置
  batchUpdateConfig: async (configKey: string, configs: Record<string, string>): Promise<void> => {
    await axios.post(`/config/batch/${configKey}`, { configs })
  },

  // 保存指定配置
  saveConfig: async (configKey: string): Promise<void> => {
    await axios.post(`/config/save/${configKey}`)
  },

  // 重载指定配置
  reloadConfig: async (configKey: string): Promise<void> => {
    await axios.post(`/config/reload/${configKey}`)
  },

  // 获取模型组列表（兼容性API）
  getModelGroups: async (): Promise<Record<string, ModelGroupConfig>> => {
    const response = await axios.get<Record<string, ModelGroupConfig>>('/config/model-groups')
    return response.data
  },

  // 获取模型类型列表（兼容性API）
  getModelTypes: async (): Promise<ModelTypeOption[]> => {
    const response = await axios.get<ModelTypeOption[]>('/config/model-types')
    return response.data
  },

  // 插件配置相关API - 使用统一配置系统
  getPluginConfig: async (pluginId: string): Promise<ConfigItem[]> => {
    return unifiedConfigApi.getConfigList(`plugin_${pluginId}`)
  },

  savePluginConfig: async (pluginId: string, configs: Record<string, string>): Promise<void> => {
    await unifiedConfigApi.batchUpdateConfig(`plugin_${pluginId}`, configs)
  },

  // 模型组管理API - 保持与原有API兼容
  updateModelGroup: async (groupName: string, config: ModelGroupConfig): Promise<void> => {
    await axios.post(`/config/model-groups/${groupName}`, config)
  },

  deleteModelGroup: async (groupName: string): Promise<void> => {
    await axios.delete(`/config/model-groups/${groupName}`)
  },
}

// 创建配置服务适配器，用于适配ConfigTable组件的接口
export const createConfigService = (configKey: string) => ({
  getConfigList: (key: string = configKey) => unifiedConfigApi.getConfigList(key),
  getModelGroups: unifiedConfigApi.getModelGroups,
  getModelTypes: unifiedConfigApi.getModelTypes,
  batchUpdateConfig: (key: string, configs: Record<string, string>) =>
    unifiedConfigApi.batchUpdateConfig(key || configKey, configs),
  saveConfig: (key: string = configKey) => unifiedConfigApi.saveConfig(key),
  reloadConfig: (key: string = configKey) => unifiedConfigApi.reloadConfig(key),
})

export default unifiedConfigApi
