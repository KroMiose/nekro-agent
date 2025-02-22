import axios from './axios'
import { createEventStream } from './utils/stream'

export type MethodType = 'tool' | 'behavior' | 'agent'

export interface Method {
  name: string
  type: MethodType
  description: string
}

export interface Extension {
  name: string
  version: string
  description: string
  author: string
  methods: Method[]
  is_enabled: boolean
}

export const extensionsApi = {
  getExtensions: async (): Promise<Extension[]> => {
    try {
      const response = await axios.get<{ data: Extension[] }>('/extensions')
      return response.data.data
    } catch (error) {
      console.error('Failed to fetch extensions:', error)
      return []
    }
  },

  getExtensionFiles: async (filePath?: string): Promise<string[] | string> => {
    try {
      if (filePath) {
        const response = await axios.get<{ data: { content: string } }>(
          `/extensions/file/${filePath}`
        )
        return response.data.data.content
      } else {
        const response = await axios.get<{ data: string[] }>('/extensions/files')
        return response.data.data
      }
    } catch (error) {
      console.error('Failed to fetch extension files:', error)
      throw error
    }
  },

  saveExtensionFile: async (filePath: string, content: string): Promise<void> => {
    try {
      await axios.post(`/extensions/file/${filePath}`, content, {
        headers: {
          'Content-Type': 'text/plain',
        },
      })
    } catch (error) {
      console.error('Failed to save extension file:', error)
      throw error
    }
  },

  generateExtensionCode: async (
    filePath: string,
    prompt: string,
    currentCode?: string
  ): Promise<{ code: string }> => {
    try {
      const response = await axios.post<{ data: { code: string } }>('/extensions/generate', {
        file_path: filePath,
        prompt,
        current_code: currentCode,
      })
      return response.data.data
    } catch (error) {
      console.error('Failed to generate extension code:', error)
      throw error
    }
  },

  generateExtensionTemplate: async (name: string, description: string): Promise<string> => {
    try {
      const response = await axios.post<{ data: { template: string } }>('/extensions/template', {
        name,
        description,
      })
      return response.data.data.template
    } catch (error) {
      console.error('Failed to generate extension template:', error)
      throw error
    }
  },

  async applyGeneratedCode(filePath: string, prompt: string, currentCode: string): Promise<string> {
    try {
      const response = await axios.post<{ data: { code: string } }>(
        '/extensions/apply',
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
      console.error('Failed to apply generated code:', error)
      throw error
    }
  },

  async reloadExtensions(): Promise<void> {
    try {
      await axios.post('/extensions/reload')
    } catch (error) {
      console.error('Failed to reload extensions:', error)
      throw error
    }
  },
}

export const streamGenerateCode = (
  filePath: string,
  prompt: string,
  currentCode: string,
  onMessage: (data: string) => void,
  onError?: (error: Error) => void,
  signal?: AbortSignal
) => {
  return createEventStream({
    endpoint: '/extensions/generate/stream',
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

export const {
  getExtensions,
  getExtensionFiles,
  saveExtensionFile,
  generateExtensionCode,
  generateExtensionTemplate,
} = extensionsApi

export async function deleteExtensionFile(filePath: string): Promise<void> {
  await axios.delete(`/extensions/files/${filePath}`)
}

export async function listExtensionFiles(): Promise<string[]> {
  const response = await axios.get('/extensions/files')
  return response.data
}

export async function readExtensionFile(filePath: string): Promise<string> {
  const response = await axios.get(`/extensions/files/${filePath}`)
  return response.data
}

export const exportExtensionFile = async (filePath: string) => {
  try {
    // 获取文件内容
    const content = (await extensionsApi.getExtensionFiles(filePath)) as string

    // 创建 Blob 对象
    const blob = new Blob([content], { type: 'text/x-python' })

    // 创建下载链接
    const url = window.URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url

    // 设置文件名（如果是禁用状态的扩展，去掉 .disabled 后缀）
    link.download = filePath.endsWith('.disabled')
      ? filePath.replace('.disabled', '')
      : filePath.split('/').pop() || filePath

    // 触发下载
    document.body.appendChild(link)
    link.click()

    // 清理
    document.body.removeChild(link)
    window.URL.revokeObjectURL(url)
  } catch (error) {
    console.error('Failed to export extension file:', error)
    throw error
  }
}
