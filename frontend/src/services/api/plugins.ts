import axios from './axios'
import { createEventStream } from './utils/stream'
import { configApi } from './config'

export type MethodType = 'tool' | 'behavior' | 'agent' | 'multimodal_agent'

export interface Method {
  name: string
  type: MethodType
  description: string
}

export interface Webhook {
  endpoint: string
  name: string
  description: string
}

export interface Plugin {
  name: string
  moduleName: string
  id: string // 插件唯一标识
  version: string
  description: string
  author: string
  url: string
  methods: Method[]
  webhooks: Webhook[]
  enabled: boolean
  hasConfig: boolean
  isBuiltin: boolean // 是否为内置插件
  isPackage: boolean // 是否为市场插件（包）
}

export interface PluginConfig {
  key: string
  value: unknown
  title: string
  description?: string
  type: string
  element_type?: string
  enum?: string[]
  is_secret?: boolean
  is_textarea?: boolean
  required?: boolean
  placeholder?: string
  is_hidden?: boolean
  ref_model_groups?: boolean
}

export interface PluginData {
  id: number
  target_chat_key: string
  target_user_id: string
  data_key: string
  data_value: string
  create_time: string
  update_time: string
}

export const pluginsApi = {
  // 获取插件列表
  getPlugins: async (): Promise<Plugin[]> => {
    try {
      const response = await axios.get<{ data: Plugin[] }>('/plugins/list')
      return response.data.data
    } catch (error) {
      console.error('获取插件列表失败:', error)
      return []
    }
  },

  // 获取插件详情
  getPluginDetail: async (pluginId: string): Promise<Plugin | null> => {
    try {
      const response = await axios.get<{ data: Plugin }>(`/plugins/detail/${pluginId}`)
      return response.data.data
    } catch (error) {
      console.error(`获取插件 ${pluginId} 详情失败:`, error)
      return null
    }
  },

  // 启用/禁用插件
  togglePluginEnabled: async (pluginId: string, enabled: boolean): Promise<boolean> => {
    try {
      await axios.post(`/plugins/toggle/${pluginId}`, { enabled })
      return true
    } catch (error) {
      console.error(`切换插件 ${pluginId} 状态失败:`, error)
      return false
    }
  },

  // 获取插件配置
  getPluginConfig: async (pluginId: string): Promise<PluginConfig[]> => {
    try {
      const response = await axios.get<{ data: PluginConfig[] }>(`/plugins/configs/${pluginId}`)
      return response.data.data
    } catch (error) {
      console.error(`获取插件 ${pluginId} 配置失败:`, error)
      return []
    }
  },

  // 保存插件配置
  savePluginConfig: async (pluginId: string, configs: Record<string, string>): Promise<boolean> => {
    try {
      await axios.post(`/plugins/configs/${pluginId}`, { configs })
      return true
    } catch (error) {
      console.error(`保存插件 ${pluginId} 配置失败:`, error)
      return false
    }
  },

  // 重载插件
  reloadPlugins: async (module_name: string): Promise<{ success: boolean; errorMsg?: string }> => {
    try {
      if (!module_name) {
        return { success: false, errorMsg: 'module_name不能为空' }
      }
      const response = await axios.post(
        '/plugins/reload',
        {},
        {
          params: { module_name },
        }
      )
      // 检查返回的结果
      if (response.data.code !== 200) {
        return { success: false, errorMsg: response.data.msg || '重载失败' }
      }
      return { success: true }
    } catch (error: unknown) {
      // 捕获并返回后端的详细错误信息
      const err = error as {
        response?: {
          data?: {
            msg?: string
            detail?: unknown
          }
        }
        message?: string
      }

      const errorMsg =
        err.response?.data?.msg ||
        (err.response?.data?.detail ? JSON.stringify(err.response.data.detail) : '') ||
        err.message ||
        '未知错误'
      console.error(errorMsg)
      return { success: false, errorMsg }
    }
  },

  // 获取插件文件列表
  getPluginFiles: async (): Promise<string[]> => {
    try {
      const response = await axios.get<{ data: string[] }>('/plugins/files')
      return response.data.data
    } catch (error) {
      console.error('获取插件文件列表失败:', error)
      return []
    }
  },

  // 获取插件文件内容
  getPluginFileContent: async (filePath: string): Promise<string | null> => {
    try {
      const response = await axios.get<{ data: { content: string } }>(`/plugins/file/${filePath}`)
      return response.data.data.content
    } catch (error) {
      console.error(`获取插件文件 ${filePath} 内容失败:`, error)
      return null
    }
  },

  // 保存插件文件
  savePluginFile: async (filePath: string, content: string): Promise<boolean> => {
    try {
      await axios.post(`/plugins/file/${filePath}`, content, {
        headers: {
          'Content-Type': 'text/plain',
        },
      })
      return true
    } catch (error) {
      console.error(`保存插件文件 ${filePath} 失败:`, error)
      return false
    }
  },

  // 删除插件文件
  deletePluginFile: async (filePath: string): Promise<boolean> => {
    try {
      await axios.delete(`/plugins/files/${filePath}`)
      return true
    } catch (error) {
      console.error(`删除插件文件 ${filePath} 失败:`, error)
      return false
    }
  },

  // 导出插件文件
  exportPluginFile: async (filePath: string): Promise<boolean> => {
    try {
      // 获取文件内容
      const content = await pluginsApi.getPluginFileContent(filePath)
      if (!content) {
        throw new Error('无法获取文件内容')
      }

      // 创建一个下载链接
      const blob = new Blob([content], { type: 'text/plain' })
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = filePath.split('/').pop() || 'plugin_file.txt'
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
      URL.revokeObjectURL(url)

      return true
    } catch (error) {
      console.error(`导出插件文件 ${filePath} 失败:`, error)
      return false
    }
  },

  // 生成插件代码
  generatePluginCode: async (
    filePath: string,
    prompt: string,
    currentCode?: string
  ): Promise<string | null> => {
    try {
      const response = await axios.post<{ data: { code: string } }>('/plugins/generate', {
        file_path: filePath,
        prompt,
        current_code: currentCode,
      })
      return response.data.data.code
    } catch (error) {
      console.error('生成插件代码失败:', error)
      return null
    }
  },

  // 生成插件模板
  generatePluginTemplate: async (name: string, description: string): Promise<string | null> => {
    try {
      const response = await axios.post<{ data: { template: string } }>('/plugins/template', {
        name,
        description,
      })
      return response.data.data.template
    } catch (error) {
      console.error('生成插件模板失败:', error)
      return null
    }
  },

  // 应用生成的代码
  applyGeneratedCode: async (
    filePath: string,
    prompt: string,
    currentCode: string
  ): Promise<string | null> => {
    try {
      const response = await axios.post<{ data: { code: string } }>(
        '/plugins/apply',
        {
          file_path: filePath,
          prompt,
          current_code: currentCode,
        },
        {
          timeout: 60000,
        }
      )
      return response.data.data.code
    } catch (error) {
      console.error('应用生成代码失败:', error)
      return null
    }
  },

  // 获取插件数据列表
  getPluginData: async (pluginId: string): Promise<PluginData[]> => {
    const response = await axios.get<{ data: PluginData[] }>(`/plugins/data/${pluginId}`)
    return response.data.data
  },

  // 删除插件数据
  deletePluginData: async (pluginId: string, dataId: number): Promise<void> => {
    await axios.delete<{ data: void }>(`/plugins/data/${pluginId}/${dataId}`)
  },

  async resetPluginData(pluginId: string) {
    const res = await axios.delete(`/plugins/data/${pluginId}`)
    return res.data
  },

  // 获取模型组列表
  getModelGroups: async () => {
    return configApi.getModelGroups()
  },

  // 删除插件包（市场插件）
  removePackage: async (moduleName: string): Promise<boolean> => {
    try {
      await axios.delete(`/plugins/package/${moduleName}`)
      return true
    } catch (error) {
      console.error(`删除插件包 ${moduleName} 失败:`, error)
      return false
    }
  },

  // 更新插件包（市场插件）
  updatePackage: async (moduleName: string): Promise<{ success: boolean; errorMsg?: string }> => {
    try {
      const response = await axios.post(`/plugins/package/update/${moduleName}`)
      // 检查返回的结果
      if (response.data.code !== 200) {
        return { success: false, errorMsg: response.data.msg || '更新失败' }
      }
      return { success: true }
    } catch (error: unknown) {
      const err = error as {
        response?: {
          data?: {
            msg?: string
            detail?: unknown
          }
        }
        message?: string
      }

      const errorMsg =
        err.response?.data?.msg ||
        (err.response?.data?.detail ? JSON.stringify(err.response.data.detail) : '') ||
        err.message ||
        '未知错误'
      console.error(errorMsg)
      return { success: false, errorMsg }
    }
  },
}

// 为了支持直接导入这些方法，我们也单独导出它们
export const getPlugins = pluginsApi.getPlugins
export const getPluginDetail = pluginsApi.getPluginDetail
export const togglePluginEnabled = pluginsApi.togglePluginEnabled
export const getPluginConfig = pluginsApi.getPluginConfig
export const savePluginConfig = pluginsApi.savePluginConfig
export const reloadPlugins = pluginsApi.reloadPlugins
export const getPluginFiles = pluginsApi.getPluginFiles
export const getPluginFileContent = pluginsApi.getPluginFileContent
export const savePluginFile = pluginsApi.savePluginFile
export const deletePluginFile = pluginsApi.deletePluginFile
export const generatePluginCode = pluginsApi.generatePluginCode
export const generatePluginTemplate = pluginsApi.generatePluginTemplate
export const applyGeneratedCode = pluginsApi.applyGeneratedCode
export const exportPluginFile = pluginsApi.exportPluginFile
export const getPluginData = pluginsApi.getPluginData
export const deletePluginData = pluginsApi.deletePluginData
export const resetPluginData = pluginsApi.resetPluginData
export const getModelGroups = pluginsApi.getModelGroups
export const removePackage = pluginsApi.removePackage
export const updatePackage = pluginsApi.updatePackage

export const streamGenerateCode = (
  filePath: string,
  prompt: string,
  currentCode: string,
  onMessage: (data: string) => void,
  onError?: (error: Error) => void,
  signal?: AbortSignal
) => {
  return createEventStream({
    endpoint: '/plugins/generate/stream',
    method: 'POST',
    body: {
      file_path: filePath,
      prompt,
      current_code: currentCode,
    },
    onMessage,
    onError,
    signal,
  })
}
