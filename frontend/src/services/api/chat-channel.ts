import axios from './axios'

export interface ChatChannel {
  id: number
  chat_key: string
  channel_name: string | null
  is_active: boolean
  chat_type: string
  message_count: number
  create_time: string
  update_time: string
  last_message_time: string | null
}

export interface ChatChannelDetail extends ChatChannel {
  unique_users: number
  conversation_start_time: string
  preset_id?: number | null
}

export interface ChatMessage {
  id: number
  sender_id: string
  sender_name: string
  content: string
  create_time: string
}

export interface ChatChannelListResponse {
  total: number
  items: ChatChannel[]
}

export interface ChatMessageListResponse {
  total: number
  items: ChatMessage[]
}

export interface ActionResponse {
  ok: boolean
}

export const chatChannelApi = {
  getList: async (params: {
    page: number
    page_size: number
    search?: string
    chat_type?: string
    is_active?: boolean
  }): Promise<ChatChannelListResponse> => {
    const response = await axios.get<ChatChannelListResponse>('/chat-channel/list', { params })
    return response.data
  },

  getDetail: async (chatKey: string): Promise<ChatChannelDetail> => {
    const response = await axios.get<ChatChannelDetail>(`/chat-channel/detail/${chatKey}`)
    return response.data
  },

  setActive: async (chatKey: string, isActive: boolean): Promise<ActionResponse> => {
    const response = await axios.post<ActionResponse>(`/chat-channel/${chatKey}/active`, null, {
      params: { is_active: isActive },
    })
    return response.data
  },

  reset: async (chatKey: string): Promise<ActionResponse> => {
    const response = await axios.post<ActionResponse>(`/chat-channel/${chatKey}/reset`)
    return response.data
  },

  getMessages: async (params: {
    chat_key: string
    before_id?: number
    page_size?: number
  }): Promise<ChatMessageListResponse> => {
    const response = await axios.get<ChatMessageListResponse>(
      `/chat-channel/${params.chat_key}/messages`,
      {
      params: { 
        before_id: params.before_id,
        page_size: params.page_size || 32,
      },

      }
    )
    return response.data
  },

  setPreset: async (chatKey: string, presetId: number | null): Promise<ActionResponse> => {
    const response = await axios.post<ActionResponse>(`/chat-channel/${chatKey}/preset`, null, {
      params: { preset_id: presetId },
    })
    return response.data
  },
} 
