import type { ReactNode } from 'react'
import { ChannelDirectoryContext } from '../../contexts/ChannelDirectoryContext'
import { useChannelDirectory } from '../../hooks/useChannelDirectory'
import { getChannelDisplayName } from '../../services/api/chat-channel'

export default function ChannelDirectoryProvider({ children }: { children: ReactNode }) {
  const channelDirectory = useChannelDirectory()

  return (
    <ChannelDirectoryContext.Provider
      value={{
        ...channelDirectory,
        getChannel: (chatKey) => (chatKey ? channelDirectory.channelMap.get(chatKey) : undefined),
        getChannelName: (chatKey) => {
          if (!chatKey) return null
          const channel = channelDirectory.channelMap.get(chatKey)
          return channel ? getChannelDisplayName(channel) : chatKey
        },
      }}
    >
      {children}
    </ChannelDirectoryContext.Provider>
  )
}
