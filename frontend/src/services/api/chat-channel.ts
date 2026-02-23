import axios from './axios'

export interface ActionResponse {
  ok: boolean
  detail?: string
  error?: string
}

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
  can_send?: boolean
  ai_always_include_msg_id?: boolean
}

export interface ChatMessageSegment {
  type: 'text' | 'image' | 'file' | 'voice' | 'video' | 'at' | 'json_card'
  text: string
  // file / image / voice / video
  file_name?: string
  local_path?: string
  remote_url?: string
  // at
  target_platform_userid?: string
  target_nickname?: string
  // json_card
  json_data?: Record<string, unknown>
  card_title?: string
  card_desc?: string
  card_icon?: string
  card_preview?: string
  card_url?: string
  share_from_nick?: string
}

export interface ChatMessage {
  id: number
  sender_id: string
  sender_name: string
  sender_nickname: string
  platform_userid: string
  content: string
  content_data: ChatMessageSegment[]
  chat_key: string
  create_time: string
  message_id?: string
  ref_msg_id?: string
}

export interface ChatChannelListResponse {
  total: number
  items: ChatChannel[]
}

export interface ChatMessageListResponse {
  total: number
  items: ChatMessage[]
}

export interface ChatChannelUser {
  platform_userid: string
  nickname: string
}

export interface ChatChannelUsersResponse {
  total: number
  items: ChatChannelUser[]
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

  sendMessage: async (chatKey: string, message: string, file?: File, senderType?: 'bot' | 'system' | 'none'): Promise<ActionResponse> => {
    const formData = new FormData()
    formData.append('message', message)
    if (file) {
      formData.append('file', file)
    }
    if (senderType) {
      formData.append('sender_type', senderType)
    }
    const response = await axios.post<ActionResponse>(`/chat-channel/${chatKey}/send`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
    return response.data
  },

  getUsers: async (chatKey: string): Promise<ChatChannelUsersResponse> => {
    const response = await axios.get<ChatChannelUsersResponse>(`/chat-channel/${chatKey}/users`)
    return response.data
  },
} 
