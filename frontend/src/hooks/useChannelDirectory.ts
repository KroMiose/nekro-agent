import { useEffect, useMemo, useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import {
  chatChannelApi,
  type ChannelDirectoryEntry,
  type ChannelListStreamEvent,
} from '../services/api/chat-channel'

export type { ChannelDirectoryEntry }

export interface ChannelDirectoryState {
  channels: ChannelDirectoryEntry[]
  channelMap: Map<string, ChannelDirectoryEntry>
  isLoading: boolean
}

function applyChannelStreamEvent(
  channels: ChannelDirectoryEntry[],
  event: ChannelListStreamEvent,
): ChannelDirectoryEntry[] {
  const next = [...channels]
  const index = next.findIndex(channel => channel.chat_key === event.chat_key)

  if (event.event_type === 'deleted') {
    if (index >= 0) {
      next.splice(index, 1)
    }
    return next
  }

  if (index >= 0) {
    const updated = {
      ...next[index],
      channel_name: event.channel_name ?? next[index].channel_name,
      is_active: event.is_active ?? next[index].is_active,
      status: event.status ?? next[index].status,
    }
    next.splice(index, 1)
    next.unshift(updated)
    return next
  }

  if (event.event_type === 'created') {
    next.unshift({
      id: 0,
      chat_key: event.chat_key,
      channel_name: event.channel_name ?? null,
      is_active: event.is_active ?? true,
      status: event.status ?? 'active',
      chat_type: '',
    })
    return next
  }

  return next
}

export function useChannelDirectory(): ChannelDirectoryState {
  const queryClient = useQueryClient()
  const [channels, setChannels] = useState<ChannelDirectoryEntry[]>([])

  const { data, isLoading } = useQuery({
    queryKey: ['channel-directory'],
    queryFn: () => chatChannelApi.getDirectory(),
    staleTime: 5 * 60 * 1000,
  })

  useEffect(() => {
    if (!data) return
    setChannels(data)
  }, [data])

  useEffect(() => {
    const cancel = chatChannelApi.streamChannels((event) => {
      setChannels(prev => applyChannelStreamEvent(prev, event))
      queryClient.invalidateQueries({ queryKey: ['channel-directory'] })
    })
    return () => cancel()
  }, [queryClient])

  const channelMap = useMemo(() => {
    const map = new Map<string, ChannelDirectoryEntry>()
    for (const channel of channels) {
      map.set(channel.chat_key, channel)
    }
    return map
  }, [channels])

  return {
    channels,
    channelMap,
    isLoading: isLoading && channels.length === 0,
  }
}
