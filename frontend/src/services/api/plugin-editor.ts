import axios from './axios'
import { createEventStream } from './utils/stream'

export interface PluginEditorApi {
  // 获取插件文件列表
  getPluginFiles: () => Promise<string[]>
  // 获取插件文件内容
  getPluginFileContent: (filePath: string) => Promise<string | null>
  // 保存插件文件
  savePluginFile: (filePath: string, content: string) => Promise<boolean>
  // 删除插件文件
  deletePluginFile: (filePath: string) => Promise<boolean>
  // 导出插件文件
  exportPluginFile: (filePath: string) => Promise<boolean>
  // 生成插件代码
  generatePluginCode: (
    filePath: string,
    prompt: string,
    currentCode?: string
  ) => Promise<string | null>
  // 应用生成的代码
  applyGeneratedCode: (
    filePath: string,
    prompt: string,
    currentCode: string
  ) => Promise<string | null>
  // 生成插件模板
  generatePluginTemplate: (name: string, description: string) => Promise<string | null>
}

export const pluginEditorApi: PluginEditorApi = {
  // 获取插件文件列表
  getPluginFiles: async (): Promise<string[]> => {
    try {
      const response = await axios.get<string[]>('/plugin-editor/files')
      return response.data
    } catch (error) {
      return []
    }
  },

  // 获取插件文件内容
  getPluginFileContent: async (filePath: string): Promise<string | null> => {
    try {
      const response = await axios.get<{ content: string }>(`/plugin-editor/file/${filePath}`)
      return response.data.content
    } catch (error) {
      return null
    }
  },

  // 保存插件文件
  savePluginFile: async (filePath: string, content: string): Promise<boolean> => {
    try {
      const response = await axios.post<{ ok: boolean }>(`/plugin-editor/file/${filePath}`, content, {
        headers: {
          'Content-Type': 'text/plain',
        },
      })
      return response.data.ok
    } catch (error) {
      return false
    }
  },

  // 删除插件文件
  deletePluginFile: async (filePath: string): Promise<boolean> => {
    try {
      const response = await axios.delete<{ ok: boolean }>(`/plugin-editor/files/${filePath}`)
      return response.data.ok
    } catch (error) {
      return false
    }
  },

  // 导出插件文件
  exportPluginFile: async (filePath: string): Promise<boolean> => {
    try {
      // 获取文件内容
      const content = await pluginEditorApi.getPluginFileContent(filePath)
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
      const response = await axios.post<{ code: string }>('/plugin-editor/generate', {
        file_path: filePath,
        prompt,
        current_code: currentCode,
      })
      return response.data.code
    } catch (error) {
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
      const response = await axios.post<{ code: string }>(
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
    } catch (error) {
      return null
    }
  },

  // 生成插件模板
  generatePluginTemplate: async (name: string, description: string): Promise<string | null> => {
    try {
      const response = await axios.post<{ template: string }>('/plugin-editor/template', {
        name,
        description,
      })
      return response.data.template
    } catch (error) {
      return null
    }
  },
}

// 为了支持直接导入这些方法，我们也单独导出它们
export const getPluginFiles = pluginEditorApi.getPluginFiles
export const getPluginFileContent = pluginEditorApi.getPluginFileContent
export const savePluginFile = pluginEditorApi.savePluginFile
export const deletePluginFile = pluginEditorApi.deletePluginFile
export const exportPluginFile = pluginEditorApi.exportPluginFile
export const generatePluginCode = pluginEditorApi.generatePluginCode
export const generatePluginTemplate = pluginEditorApi.generatePluginTemplate
export const applyGeneratedCode = pluginEditorApi.applyGeneratedCode

// 流式生成代码
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
