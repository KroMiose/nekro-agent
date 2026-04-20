import axios from './axios'
import { createEventStream, createSharedEventStreamManager } from './utils/stream'

export interface ActionResponse {
  ok: boolean
  detail?: string
  error?: string
}

export interface ChatAnnouncementResultItem {
  chat_key: string
  channel_name: string | null
  ok: boolean
  error: string
}

export interface ChatAnnouncementResponse {
  ok: boolean
  total: number
  success_count: number
  failure_count: number
  results: ChatAnnouncementResultItem[]
}

export interface ChatChannel {
  id: number
  chat_key: string
  channel_name: string | null
  is_active: boolean
  status: 'active' | 'observe' | 'disabled'
  chat_type: string
  message_count: number
  create_time: string
  update_time: string
  last_message_time: string | null
}

export interface ChannelDirectoryEntry {
  id: number
  chat_key: string
  channel_name: string | null
  is_active: boolean
  status: 'active' | 'observe' | 'disabled'
  chat_type: string
}

export interface ChatChannelDetail extends ChatChannel {
  unique_users: number
  conversation_start_time: string
  preset_id?: number | null
  can_send?: boolean
  ai_always_include_msg_id?: boolean
}

export interface ChatMessageSegment {
  type: 'text' | 'image' | 'file' | 'voice' | 'video' | 'at' | 'json_card' | 'poke' | 'forward'
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
  // forward
  forward_content?: ForwardMessageItem[]
  // poke
  action_img_url?: string
  poke_style?: string
  poke_style_suffix?: string
  target_id?: string
}

export interface ForwardMessageItem {
  sender: string
  content: string
  images: string[]
  forward_content?: ForwardMessageItem[]
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

export interface ChatPluginData {
  id: number
  plugin_key: string
  data_key: string
  data_value: string
  target_user_id: string
  create_time: string
  update_time: string
}

export interface ChatPluginDataResponse {
  total: number
  items: ChatPluginData[]
  plugin_keys: string[]
  plugin_names: Record<string, string>
}

export interface ChannelDeletePreview {
  message_count: number
  timer_job_count: number
  plugin_data_count: number
  mem_paragraph_count: number
  mem_episode_count: number
  upload_dir_exists: boolean
  sandbox_dir_exists: boolean
}

export interface ChannelListStreamEvent {
  event_type: string
  chat_key: string
  channel_name?: string | null
  is_active?: boolean | null
  status?: string | null
}

const channelListStreamManager = createSharedEventStreamManager({
  endpoint: '/chat-channel/list/stream',
  closeDelayMs: 1500,
})

export const chatChannelApi = {
  getList: async (params: {
    page: number
    page_size: number
    search?: string
    chat_type?: string
    status?: 'active' | 'observe' | 'disabled'
    is_active?: boolean
  }): Promise<ChatChannelListResponse> => {
    const response = await axios.get<ChatChannelListResponse>('/chat-channel/list', { params })
    return response.data
  },

  getDetail: async (chatKey: string): Promise<ChatChannelDetail> => {
    const response = await axios.get<ChatChannelDetail>(`/chat-channel/detail/${chatKey}`)
    return response.data
  },

  getDirectory: async (): Promise<ChannelDirectoryEntry[]> => {
    const response = await axios.get<{ items: ChannelDirectoryEntry[] }>('/chat-channel/directory')
    return response.data.items
  },

  setActive: async (chatKey: string, isActive: boolean): Promise<ActionResponse> => {
    const response = await axios.post<ActionResponse>(`/chat-channel/${chatKey}/active`, null, {
      params: { is_active: isActive },
    })
    return response.data
  },

  setStatus: async (chatKey: string, status: 'active' | 'observe' | 'disabled'): Promise<ActionResponse> => {
    const response = await axios.post<ActionResponse>(`/chat-channel/${chatKey}/status`, null, {
      params: { status },
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

  sendAnnouncementMessage: async (payload: {
    chat_keys: string[]
    message: string
  }): Promise<ChatAnnouncementResponse> => {
    const response = await axios.post<ChatAnnouncementResponse>(
      '/chat-channel/announcement/send',
      payload
    )
    return response.data
  },

  getUsers: async (chatKey: string): Promise<ChatChannelUsersResponse> => {
    const response = await axios.get<ChatChannelUsersResponse>(`/chat-channel/${chatKey}/users`)
    return response.data
  },

  sendPoke: async (chatKey: string, targetUserId: string): Promise<ActionResponse> => {
    const response = await axios.post<ActionResponse>(`/chat-channel/${chatKey}/poke`, {
      target_user_id: targetUserId,
    })
    return response.data
  },

  streamMessages: (chatKey: string, onMessage: (msg: ChatMessage) => void, onError?: (error: Error) => void): (() => void) => {
    /**
     * Subscribe to real-time messages for a chat channel using SSE
     * @param chatKey - The chat channel key
     * @param onMessage - Callback when a new message is received
     * @param onError - Optional error callback
     * @returns Cleanup function to unsubscribe
     */
    return createEventStream({
      endpoint: `/chat-channel/${chatKey}/stream`,
      onMessage: (data: string) => {
        const trimmedData = data.trim()
        if (!trimmedData || !trimmedData.startsWith('{')) return
        try {
          const message = JSON.parse(trimmedData) as ChatMessage
          onMessage(message)
        } catch (error) {
          console.error('Failed to parse message:', error)
        }
      },
      onError,
    })
  },

  getPluginData: async (chatKey: string, params?: {
    plugin_key?: string
    page?: number
    page_size?: number
  }): Promise<ChatPluginDataResponse> => {
    const response = await axios.get<ChatPluginDataResponse>(`/chat-channel/${chatKey}/plugin-data`, { params })
    return response.data
  },

  updatePluginData: async (chatKey: string, dataId: number, dataValue: string): Promise<ActionResponse> => {
    const response = await axios.put<ActionResponse>(`/chat-channel/${chatKey}/plugin-data/${dataId}`, {
      data_value: dataValue,
    })
    return response.data
  },

  deletePluginData: async (chatKey: string, dataId: number): Promise<ActionResponse> => {
    const response = await axios.delete<ActionResponse>(`/chat-channel/${chatKey}/plugin-data/${dataId}`)
    return response.data
  },

  getDeletePreview: async (chatKey: string): Promise<ChannelDeletePreview> => {
    const response = await axios.get<ChannelDeletePreview>(`/chat-channel/${encodeURIComponent(chatKey)}/delete-preview`)
    return response.data
  },

  deleteChannel: async (chatKey: string): Promise<ActionResponse> => {
    const response = await axios.delete<ActionResponse>(`/chat-channel/${encodeURIComponent(chatKey)}`)
    return response.data
  },

  streamChannels: (onMessage: (event: ChannelListStreamEvent) => void, onError?: (error: Error) => void): (() => void) => {
    /**
     * Subscribe to real-time channel list updates using SSE
     * @param onMessage - Callback when a channel event is received (created, updated, deleted, activated, deactivated)
     * @param onError - Optional error callback
     * @returns Cleanup function to unsubscribe
     */
    return channelListStreamManager.subscribe({
      onMessage: (data: string) => {
        const trimmedData = data.trim()
        if (!trimmedData || !trimmedData.startsWith('{')) return
        try {
          const event = JSON.parse(trimmedData)
          onMessage(event)
        } catch (error) {
          console.error('Failed to parse channel event:', error)
        }
      },
      onError,
    })
  },
} 
