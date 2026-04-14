import axios from './axios'
import type { I18nDict } from './types'
import { createEventStream } from './utils/stream'

export interface CommandOutputSegment {
  type: 'text' | 'image' | 'file'
  text?: string
  file_path?: string
  file_name?: string
  mime_type?: string
  web_url?: string
}

export interface CommandState {
  name: string
  namespace: string
  aliases: string[]
  description: string
  usage: string
  permission: string
  category: string
  source: string
  source_display_name: string
  enabled: boolean
  has_channel_override: boolean
  params_schema?: Record<string, unknown>
  i18n_description?: I18nDict
  i18n_usage?: I18nDict
  i18n_category?: I18nDict
}

export interface CommandOutputEvent {
  chat_key: string
  command_name: string
  status: string
  message: string
  output_segments?: CommandOutputSegment[] | null
  timestamp: number
}

export interface WebUIExecuteResponseItem {
  status: string
  message: string
  output_segments?: CommandOutputSegment[] | null
}

export const commandsApi = {
  listCommands: async (chatKey?: string): Promise<CommandState[]> => {
    const response = await axios.get<CommandState[]>('/commands/list', {
      params: { chat_key: chatKey || undefined },
    })
    return response.data
  },

  setCommandState: async (commandName: string, enabled: boolean, chatKey?: string): Promise<boolean> => {
    const response = await axios.post<{ ok: boolean }>('/commands/set-state', {
      command_name: commandName,
      enabled,
      chat_key: chatKey || undefined,
    })
    return response.data.ok
  },

  resetCommandState: async (commandName: string, chatKey?: string): Promise<boolean> => {
    const response = await axios.post<{ ok: boolean }>('/commands/reset-state', {
      command_name: commandName,
      chat_key: chatKey || undefined,
    })
    return response.data.ok
  },

  batchSetState: async (
    commands: Array<{ command_name: string; enabled: boolean; chat_key?: string }>
  ): Promise<boolean> => {
    const response = await axios.post<{ ok: boolean }>('/commands/batch-set-state', { commands })
    return response.data.ok
  },

  streamCommandOutput: (
    chatKey: string,
    onMessage: (event: CommandOutputEvent) => void,
    onError?: (error: Error) => void,
  ): (() => void) => {
    return createEventStream({
      endpoint: `/commands/${chatKey}/output/stream`,
      onMessage: (data: string) => {
        try {
          const event = JSON.parse(data) as CommandOutputEvent
          onMessage(event)
        } catch (error) {
          console.error('Failed to parse command output event:', error)
        }
      },
      onError,
    })
  },

  webuiExecute: async (
    commandName: string,
    chatKey: string,
    rawArgs: string = '',
  ): Promise<{ ok: boolean; responses: WebUIExecuteResponseItem[] }> => {
    const response = await axios.post<{
      ok: boolean
      responses: WebUIExecuteResponseItem[]
    }>('/commands/webui-execute', {
      command_name: commandName,
      chat_key: chatKey,
      raw_args: rawArgs,
    })
    return response.data
  },
}
