import axios from './axios'
import { createEventStream } from './utils/stream'
import { I18nDict } from './types'

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
  id: string
  version: string
  description: string
  author: string
  url: string
  methods: Method[]
  webhooks: Webhook[]
  enabled: boolean
  hasConfig: boolean
  isBuiltin: boolean
  isPackage: boolean
  i18n_name?: I18nDict
  i18n_description?: I18nDict
  loadFailed?: boolean
  errorMessage?: string
  errorType?: string
  filePath?: string
  stackTrace?: string
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
  model_type?: string
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

export interface ActionResponse {
  ok: boolean
}

export interface PluginDocsResponse {
  docs: string | null
  exists: boolean
}

export interface GeneratedCodeResponse {
  code: string
}

export interface PluginTemplateResponse {
  template: string
}

export interface ReloadResult {
  success: boolean
  errorMsg?: string
}

export const pluginsApi = {
  getPlugins: async (): Promise<Plugin[]> => {
    const response = await axios.get<Plugin[]>('/plugins/list')
    return response.data
  },

  getPluginDetail: async (pluginId: string): Promise<Plugin> => {
    const response = await axios.get<Plugin>(`/plugins/detail/${pluginId}`)
    return response.data
  },

  togglePluginEnabled: async (pluginId: string, enabled: boolean): Promise<boolean> => {
    const response = await axios.post<ActionResponse>(`/plugins/toggle/${pluginId}`, { enabled })
    return response.data.ok
  },

  getPluginConfig: async (pluginId: string): Promise<PluginConfig[]> => {
    const response = await axios.get<PluginConfig[]>(`/config/list/plugin_${pluginId}`)
    return response.data
  },

  savePluginConfig: async (pluginId: string, configs: Record<string, string>): Promise<boolean> => {
    const response = await axios.post<ActionResponse>(`/config/batch/plugin_${pluginId}`, { configs })
    return response.data.ok
  },

  reloadPlugins: async (module_name: string): Promise<ReloadResult> => {
    if (!module_name) {
      return { success: false, errorMsg: 'module_name不能为空' }
    }
    try {
      await axios.post('/plugins/reload', {}, { params: { module_name } })
      return { success: true }
    } catch (error: unknown) {
      const err = error as {
        response?: { data?: { message?: string; detail?: unknown } }
        message?: string
      }
      const errorMsg =
        err.response?.data?.message ||
        (err.response?.data?.detail ? JSON.stringify(err.response.data.detail) : '') ||
        err.message ||
        '未知错误'
      return { success: false, errorMsg }
    }
  },

  getPluginFiles: async (): Promise<string[]> => {
    const response = await axios.get<string[]>('/plugin-editor/files')
    return response.data
  },

  getPluginFileContent: async (filePath: string): Promise<string> => {
    const response = await axios.get<{ content: string }>(`/plugin-editor/file/${filePath}`)
    return response.data.content
  },

  savePluginFile: async (filePath: string, content: string): Promise<boolean> => {
    const response = await axios.post<ActionResponse>(`/plugin-editor/file/${filePath}`, content, {
      headers: {
        'Content-Type': 'text/plain',
      },
    })
    return response.data.ok
  },

  deletePluginFile: async (filePath: string): Promise<boolean> => {
    const response = await axios.delete<ActionResponse>(`/plugin-editor/files/${filePath}`)
    return response.data.ok
  },

  exportPluginFile: async (filePath: string): Promise<boolean> => {
    const content = await pluginsApi.getPluginFileContent(filePath)
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
  },

  generatePluginCode: async (
    filePath: string,
    prompt: string,
    currentCode?: string
  ): Promise<string> => {
    const response = await axios.post<GeneratedCodeResponse>('/plugin-editor/generate', {
      file_path: filePath,
      prompt,
      current_code: currentCode,
    })
    return response.data.code
  },

  generatePluginTemplate: async (name: string, description: string): Promise<string> => {
    const response = await axios.post<PluginTemplateResponse>('/plugin-editor/template', {
      name,
      description,
    })
    return response.data.template
  },

  getPluginDocs: async (pluginId: string): Promise<PluginDocsResponse> => {
    const response = await axios.get<PluginDocsResponse>(`/plugins/docs/${pluginId}`)
    return response.data
  },

  applyGeneratedCode: async (
    filePath: string,
    prompt: string,
    currentCode: string
  ): Promise<string> => {
    const response = await axios.post<GeneratedCodeResponse>(
      '/plugin-editor/apply',
      {
        file_path: filePath,
        prompt,
        current_code: currentCode,
      },
      {
        timeout: 60000,
      }
    )
    return response.data.code
  },

  getPluginData: async (pluginId: string): Promise<PluginData[]> => {
    const response = await axios.get<PluginData[]>(`/plugins/data/${pluginId}`)
    return response.data
  },

  deletePluginData: async (pluginId: string, dataId: number): Promise<boolean> => {
    const response = await axios.delete<ActionResponse>(`/plugins/data/${pluginId}/${dataId}`)
    return response.data.ok
  },

  async resetPluginData(pluginId: string): Promise<boolean> {
    const response = await axios.delete<ActionResponse>(`/plugins/data/${pluginId}`)
    return response.data.ok
  },

  getModelGroups: async () => {
    const { unifiedConfigApi } = await import('./unified-config')
    return unifiedConfigApi.getModelGroups()
  },

  removePackage: async (moduleName: string, clearData: boolean = false): Promise<boolean> => {
    const response = await axios.delete<ActionResponse>(`/plugins/package/${moduleName}`, {
      params: { clear_data: clearData },
    })
    return response.data.ok
  },

  updatePackage: async (moduleName: string): Promise<ReloadResult> => {
    try {
      const response = await axios.post<ActionResponse>(`/plugins/package/update/${moduleName}`)
      if (!response.data.ok) {
        return { success: false, errorMsg: '更新失败' }
      }
      return { success: true }
    } catch (error: unknown) {
      const err = error as {
        response?: { data?: { message?: string; detail?: unknown } }
        message?: string
      }
      const errorMsg =
        err.response?.data?.message ||
        (err.response?.data?.detail ? JSON.stringify(err.response.data.detail) : '') ||
        err.message ||
        '未知错误'
      return { success: false, errorMsg }
    }
  },
}

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
export const getPluginDocs = pluginsApi.getPluginDocs

export const streamGenerateCode = (
  filePath: string,
  prompt: string,
  currentCode: string,
  onMessage: (data: string) => void,
  onError?: (error: Error) => void,
  signal?: AbortSignal
) => {
  return createEventStream({
    endpoint: '/plugin-editor/generate/stream',
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
