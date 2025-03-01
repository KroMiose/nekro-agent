import axios from './axios'
import { PresetNote, PresetStatus } from '../../types/chat'

export interface ChatChannel {
  id: number
  chat_key: string
  channel_name: string | null
  is_active: boolean
  chat_type: string
  message_count: number
  current_preset: PresetStatus | null
  create_time: string
  update_time: string
  last_message_time: string | null
}

export interface ChatChannelDetail extends ChatChannel {
  unique_users: number
  preset_status_list: PresetStatus[]
  preset_notes: PresetNote[]
  conversation_start_time: string
  max_preset_status_refer_size: number
}

export interface ChatMessage {
  id: number
  sender_id: number
  sender_name: string
  content: string
  create_time: string
}

export const chatChannelApi = {
  getList: async (params: {
    page: number
    page_size: number
    search?: string
    chat_type?: string
    is_active?: boolean
  }) => {
    const response = await axios.get<{
      data: { total: number; items: ChatChannel[] }
    }>('/chat-channel/list', { params })
    return response.data.data
  },

  getDetail: async (chatKey: string) => {
    const response = await axios.get<{ data: ChatChannelDetail }>(
      `/chat-channel/detail/${chatKey}`,
    )
    return response.data.data
  },

  setActive: async (chatKey: string, isActive: boolean) => {
    const response = await axios.post<{ code: number; msg: string }>(
      `/chat-channel/${chatKey}/active`,
      null,
      { params: { is_active: isActive } },
    )
    return response.data
  },

  reset: async (chatKey: string) => {
    const response = await axios.post<{ code: number; msg: string }>(
      `/chat-channel/${chatKey}/reset`,
    )
    return response.data
  },

  getMessages: async (params: {
    chat_key: string
    before_id?: number
    page_size?: number
  }) => {
    const response = await axios.get<{
      data: { total: number; items: ChatMessage[] }
    }>(`/chat-channel/${params.chat_key}/messages`, {
      params: { 
        before_id: params.before_id,
        page_size: params.page_size || 32,
      },
    })
    return response.data.data
  },
} 