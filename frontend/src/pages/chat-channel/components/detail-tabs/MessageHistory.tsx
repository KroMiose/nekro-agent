import { useState, useEffect, useRef, useCallback } from 'react'
import {
  Box,
  Typography,
  List,
  ListItem,
  ListItemText,
  ListItemAvatar,
  Avatar,
  CircularProgress,
  Stack,
  useTheme,
  Button,
} from '@mui/material'
import { useInfiniteQuery } from '@tanstack/react-query'
import { chatChannelApi, ChatMessage } from '../../../../services/api/chat-channel'

// 防抖函数
const debounce = <T extends (...args: unknown[]) => unknown>(fn: T, delay: number): (...args: Parameters<T>) => void => {
  let timeoutId: number
  return (...args: Parameters<T>) => {
    window.clearTimeout(timeoutId)
    timeoutId = window.setTimeout(() => fn(...args), delay)
  }
}

interface MessageHistoryProps {
  chatKey: string
}

interface MessageResponse {
  total: number
  items: ChatMessage[]
}

export default function MessageHistory({ chatKey }: MessageHistoryProps) {
  const theme = useTheme()
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const [autoScroll, setAutoScroll] = useState(true)
  const loadMoreRef = useRef<HTMLDivElement>(null)
  const containerRef = useRef<HTMLDivElement>(null)
  const [initialLoad, setInitialLoad] = useState(true)
  const prevScrollHeightRef = useRef<number>(0)
  const isLoadingMoreRef = useRef(false)

  // 查询消息历史
  const { data, fetchNextPage, hasNextPage, isFetchingNextPage, isLoading } = useInfiniteQuery({
    queryKey: ['chat-messages', chatKey],
    initialPageParam: undefined as number | undefined,
    queryFn: async ({ pageParam }) => {
      const response = await chatChannelApi.getMessages({
        chat_key: chatKey,
        before_id: pageParam,
      })
      return response
    },
    getNextPageParam: (lastPage: MessageResponse) => {
      if (lastPage.items.length === 0) return undefined
      return lastPage.items[lastPage.items.length - 1].id
    },
  })

  // 自动滚动到底部（仅初始加载时）
  useEffect(() => {
    if (!isLoading && initialLoad && messagesEndRef.current) {
      messagesEndRef.current.scrollIntoView()
      setInitialLoad(false)
    }
  }, [isLoading, initialLoad])

  // 处理加载更多
  const handleLoadMore = useCallback(() => {
    if (!hasNextPage || isFetchingNextPage || isLoadingMoreRef.current) return
    const container = containerRef.current
    if (!container) return

    isLoadingMoreRef.current = true
    prevScrollHeightRef.current = container.scrollHeight
    fetchNextPage().finally(() => {
      isLoadingMoreRef.current = false
    })
  }, [hasNextPage, isFetchingNextPage, fetchNextPage])

  // 处理滚动事件
  const handleScroll = useCallback(() => {
    const container = containerRef.current
    if (!container) return

    const { scrollHeight, scrollTop, clientHeight } = container
    
    // 更新自动滚动状态
    const isNearBottom = scrollHeight - scrollTop - clientHeight < 100
    setAutoScroll(isNearBottom)

    // 检测是否接近顶部
    if (scrollTop < 50 && !isFetchingNextPage && hasNextPage) {
      handleLoadMore()
    }
  }, [hasNextPage, isFetchingNextPage, handleLoadMore])

  // 监听滚动位置
  useEffect(() => {
    const container = containerRef.current
    if (!container) return

    const debouncedScroll = debounce(handleScroll, 100)
    container.addEventListener('scroll', debouncedScroll)
    return () => container.removeEventListener('scroll', debouncedScroll)
  }, [handleScroll])

  // 保持滚动位置
  useEffect(() => {
    const container = containerRef.current
    if (!container || !data?.pages) return

    if (prevScrollHeightRef.current > 0) {
      const newScrollHeight = container.scrollHeight
      const scrollDiff = newScrollHeight - prevScrollHeightRef.current
      container.scrollTop = scrollDiff
      prevScrollHeightRef.current = 0
    }
  }, [data?.pages])

  // 处理回到底部
  const handleScrollToBottom = useCallback(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
    setAutoScroll(true)
  }, [])

  if (isLoading) {
    return (
      <Box className="h-full flex items-center justify-center">
        <CircularProgress />
      </Box>
    )
  }

  // 按时间正序排列消息
  const allMessages = data?.pages
    .flatMap(page => page.items)
    .sort((a, b) => new Date(a.create_time).getTime() - new Date(b.create_time).getTime()) || []

  return (
    <Box className="h-full flex flex-col overflow-hidden relative">
      {/* 消息列表容器 */}
      <Box 
        ref={containerRef} 
        className="flex-1 overflow-y-auto"
      >
        {/* 加载更多提示 */}
        {(hasNextPage || isFetchingNextPage) && allMessages.length >= 32 && (
          <Box 
            ref={loadMoreRef} 
            className="p-2 flex justify-center"
          >
            <CircularProgress size={24} />
          </Box>
        )}

        {/* 消息列表 */}
        {allMessages.length === 0 ? (
          <Box className="p-4 flex items-center justify-center">
            <Typography color="textSecondary">暂无消息记录</Typography>
          </Box>
        ) : (
          <List>
            {allMessages.map(message => (
              <ListItem
                key={message.id}
                sx={{
                  transition: 'background-color 0.2s',
                  '&:hover': {
                    backgroundColor:
                      theme.palette.mode === 'dark'
                        ? 'rgba(255, 255, 255, 0.05)'
                        : 'rgba(0, 0, 0, 0.02)',
                  },
                  alignItems: 'flex-start',
                  paddingTop: 2,
                  paddingBottom: 2
                }}
              >
                <ListItemAvatar sx={{ mt: 0 }}>
                  <Avatar
                    sx={{
                      bgcolor:
                        theme.palette.mode === 'dark'
                          ? 'rgba(255, 255, 255, 0.1)'
                          : 'rgba(0, 0, 0, 0.08)',
                    }}
                  >
                    {message.sender_name[0]}
                  </Avatar>
                </ListItemAvatar>
                <ListItemText
                  sx={{ mt: 0 }}
                  primary={
                    <Stack direction="row" spacing={1} alignItems="center" className="mb-1">
                      <Typography variant="body1" className="font-medium">
                        {message.sender_name}
                      </Typography>
                      <Typography
                        variant="caption"
                        color="textSecondary"
                        className="flex-shrink-0"
                      >
                        {message.create_time}
                      </Typography>
                    </Stack>
                  }
                  secondary={
                    <Typography
                      variant="body2"
                      style={{ 
                        whiteSpace: 'pre-wrap',
                        wordBreak: 'break-word',
                        overflowWrap: 'break-word'
                      }}
                      color="textSecondary"
                      sx={{
                        opacity: message.content ? 1 : 0.5,
                        fontStyle: message.content ? 'normal' : 'italic'
                      }}
                    >
                      {message.content || '[无文本内容]'}
                    </Typography>
                  }
                />
              </ListItem>
            ))}
          </List>
        )}
        <div ref={messagesEndRef} />
      </Box>

      {/* 回到底部按钮 */}
      {!autoScroll && (
        <Box
          sx={{
            position: 'absolute',
            bottom: 16,
            right: 16,
            zIndex: theme.zIndex.fab
          }}
        >
          <Button
            variant="contained"
            color="primary"
            size="small"
            onClick={handleScrollToBottom}
            sx={{
              minWidth: 'auto',
              borderRadius: 20,
              boxShadow: theme.shadows[6]
            }}
          >
            回到底部
          </Button>
        </Box>
      )}
    </Box>
  )
}
