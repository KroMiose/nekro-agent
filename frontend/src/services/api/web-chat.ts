import axios from './axios'

export interface WebSession {
  chat_key: string
  channel_id: string
  channel_name: string | null
  custom_channel_name: string | null
  status: 'active' | 'observe' | 'disabled'
  message_count: number
  update_time: string
}

export interface WebSessionListResponse {
  total: number
  items: WebSession[]
}

export interface WebSessionResponse {
  chat_key: string
  channel_id: string
  channel_name: string
  status: 'active' | 'observe' | 'disabled'
}

export interface WebMessageResponse {
  ok: boolean
  chat_key: string
  message_id: string
}

export interface WebActionResponse {
  ok: boolean
}

export const getWebSessionDisplayName = (
  session: Pick<WebSession, 'chat_key' | 'channel_name' | 'custom_channel_name'>,
): string => session.custom_channel_name?.trim() || session.channel_name?.trim() || session.chat_key

export const webChatApi = {
  getSessions: async (params?: {
    page?: number
    page_size?: number
    search?: string
  }): Promise<WebSessionListResponse> => {
    const response = await axios.get<WebSessionListResponse>('/adapters/web/sessions', { params })
    return response.data
  },

  createSession: async (name?: string): Promise<WebSessionResponse> => {
    const response = await axios.post<WebSessionResponse>('/adapters/web/sessions', { name: name ?? '' })
    return response.data
  },

  updateSession: async (chatKey: string, name: string): Promise<WebActionResponse> => {
    const response = await axios.put<WebActionResponse>(`/adapters/web/sessions/${encodeURIComponent(chatKey)}`, { name })
    return response.data
  },

  deleteSession: async (chatKey: string): Promise<WebActionResponse> => {
    const response = await axios.delete<WebActionResponse>(`/adapters/web/sessions/${encodeURIComponent(chatKey)}`)
    return response.data
  },

  sendMessage: async (chatKey: string, content: string): Promise<WebMessageResponse> => {
    const response = await axios.post<WebMessageResponse>(`/adapters/web/sessions/${encodeURIComponent(chatKey)}/messages`, {
      content,
    })
    return response.data
  },

  sendUploadMessage: async (chatKey: string, content: string, file: File): Promise<WebMessageResponse> => {
    const formData = new FormData()
    formData.append('content', content)
    formData.append('file', file)
    const response = await axios.post<WebMessageResponse>(
      `/adapters/web/sessions/${encodeURIComponent(chatKey)}/messages/upload`,
      formData,
      {
        headers: { 'Content-Type': 'multipart/form-data' },
      },
    )
    return response.data
  },
}
