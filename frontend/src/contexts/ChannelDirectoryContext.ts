import { createContext, useContext } from 'react'
import type { ChannelDirectoryEntry, ChannelDirectoryState } from '../hooks/useChannelDirectory'

export interface ChannelDirectoryContextValue extends ChannelDirectoryState {
  getChannel: (chatKey: string | null | undefined) => ChannelDirectoryEntry | undefined
  getChannelName: (chatKey: string | null | undefined) => string | null
}

const EMPTY_CHANNEL_MAP = new Map<string, ChannelDirectoryEntry>()

export const EMPTY_CHANNEL_DIRECTORY: ChannelDirectoryContextValue = {
  channels: [],
  channelMap: EMPTY_CHANNEL_MAP,
  isLoading: false,
  getChannel: () => undefined,
  getChannelName: (chatKey) => (chatKey ? chatKey : null),
}

export const ChannelDirectoryContext = createContext<ChannelDirectoryContextValue>(EMPTY_CHANNEL_DIRECTORY)

export function useChannelDirectoryContext(): ChannelDirectoryContextValue {
  return useContext(ChannelDirectoryContext)
}
