import axios from './axios'

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
}
