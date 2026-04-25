import type { ReactNode } from 'react'
import { ChannelDirectoryContext } from '../../contexts/ChannelDirectoryContext'
import { useChannelDirectory } from '../../hooks/useChannelDirectory'

export default function ChannelDirectoryProvider({ children }: { children: ReactNode }) {
  const channelDirectory = useChannelDirectory()

  return (
    <ChannelDirectoryContext.Provider
      value={{
        ...channelDirectory,
        getChannel: (chatKey) => (chatKey ? channelDirectory.channelMap.get(chatKey) : undefined),
        getChannelName: (chatKey) => {
          if (!chatKey) return null
          return channelDirectory.channelMap.get(chatKey)?.channel_name || chatKey
        },
      }}
    >
      {children}
    </ChannelDirectoryContext.Provider>
  )
}
