import axios from './axios'

export interface CommandState {
  name: string
  namespace: string
  aliases: string[]
  description: string
  usage: string
  permission: string
  category: string
  source: string
  enabled: boolean
  has_channel_override: boolean
  params_schema?: Record<string, unknown>
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
}
