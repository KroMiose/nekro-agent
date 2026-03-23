import React, { useState, useEffect } from 'react'
import {
  Box,
  Typography,
  TextField,
  InputAdornment,
  IconButton,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Stack,
  Divider,
  SelectChangeEvent,
  useTheme,
  useMediaQuery,
  Drawer,
  Fab,
  Card,
  Button,
} from '@mui/material'
import {
  Search as SearchIcon,
  Clear as ClearIcon,
  List as ListIcon,
  Info as InfoIcon,
} from '@mui/icons-material'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { useNavigate, useParams, useSearchParams } from 'react-router-dom'
import { chatChannelApi, type ChatChannelListResponse } from '../../services/api/chat-channel'
import ChatChannelList from './components/ChatChannelList'
import ChatChannelDetail from './components/ChatChannelDetail'
import TablePaginationStyled from '../../components/common/TablePaginationStyled'
import { CARD_VARIANTS } from '../../theme/variants'
import { useTranslation } from 'react-i18next'
import { chatChannelPath } from '../../router/routes'

const DEFAULT_PAGE = 1
const DEFAULT_PAGE_SIZE = 25

const parsePositiveInt = (value: string | null, fallback: number) => {
  if (!value) return fallback
  const parsed = Number(value)
  return Number.isInteger(parsed) && parsed > 0 ? parsed : fallback
}

export default function ChatChannelPage() {
  const [drawerOpen, setDrawerOpen] = useState(false)

  const theme = useTheme()
  const isMobile = useMediaQuery(theme.breakpoints.down('md'))
  const isSmall = useMediaQuery(theme.breakpoints.down('sm'))
  const { t } = useTranslation('chat-channel')
  const queryClient = useQueryClient()
  const navigate = useNavigate()
  const { chatKey } = useParams<{ chatKey: string }>()
  const [searchParams] = useSearchParams()
  const selectedChatKey = chatKey ?? null
  const search = searchParams.get('search') ?? ''
  const chatType = searchParams.get('chat_type') ?? ''
  const isActive = searchParams.get('is_active') ?? ''
  const page = parsePositiveInt(searchParams.get('page'), DEFAULT_PAGE)
  const pageSize = parsePositiveInt(searchParams.get('page_size'), DEFAULT_PAGE_SIZE)

  useEffect(() => {
    const legacyChatKey = searchParams.get('chat_key')
    if (!legacyChatKey) return

    const nextParams = new URLSearchParams(searchParams)
    nextParams.delete('chat_key')
    const nextQuery = nextParams.toString()
    navigate(`${chatChannelPath(legacyChatKey)}${nextQuery ? `?${nextQuery}` : ''}`, { replace: true })
  }, [navigate, searchParams])

  const buildChannelUrl = (nextChatKey?: string | null, overrides?: Record<string, string | null>) => {
    const nextParams = new URLSearchParams(searchParams)
    if (overrides) {
      Object.entries(overrides).forEach(([key, value]) => {
        if (value === null || value === '') {
          nextParams.delete(key)
        } else {
          nextParams.set(key, value)
        }
      })
    }
    const query = nextParams.toString()
    const basePath = chatChannelPath(nextChatKey)
    return query ? `${basePath}?${query}` : basePath
  }

  // 查询聊天列表
  const { data: channelList, isLoading } = useQuery({
    queryKey: ['chat-channels', search, chatType, isActive, page, pageSize],
    queryFn: () =>
      chatChannelApi.getList({
        page,
        page_size: pageSize,
        search: search || undefined,
        chat_type: chatType || undefined,
        is_active: isActive === '' ? undefined : isActive === 'true',
      }),
  })

  // 实时频道列表更新订阅 (SSE)
  useEffect(() => {
    const handleChannelUpdate = (event: { event_type: string; chat_key: string; channel_name?: string | null; is_active?: boolean | null }) => {
      const { event_type, chat_key } = event

      // 更新频道列表缓存
      queryClient.setQueryData<ChatChannelListResponse | undefined>(['chat-channels', search, chatType, isActive, page, pageSize], (oldData) => {
        if (!oldData?.items) return oldData

        const newItems = [...oldData.items]
        const idx = newItems.findIndex((ch) => ch.chat_key === chat_key)

        if (event_type === 'deleted' && idx >= 0) {
          // 删除频道
          newItems.splice(idx, 1)
        } else if (event_type === 'created' && idx < 0) {
          // 新建频道（添加到列表顶部）
          newItems.unshift({
            id: 0,
            chat_key,
            channel_name: event.channel_name ?? null,
            is_active: event.is_active ?? true,
            chat_type: '',
            message_count: 0,
            create_time: new Date().toISOString(),
            update_time: new Date().toISOString(),
            last_message_time: null,
          })
        } else if ((event_type === 'updated' || event_type === 'activated' || event_type === 'deactivated')) {
          if (idx >= 0) {
            // 从原位置移除，创建新对象（保持不可变性）
            const channel = { ...newItems[idx] }
            newItems.splice(idx, 1)

            if (event.channel_name != null) {
              channel.channel_name = event.channel_name
            }
            if (event.is_active != null) {
              channel.is_active = event.is_active
            }
            channel.update_time = new Date().toISOString()
            channel.last_message_time = new Date().toISOString()

            // 移到列表顶部（最新活动的频道）
            newItems.unshift(channel)
          }
        }

        return { ...oldData, items: newItems }
      })
    }

    // 订阅频道列表更新
    const cleanup = chatChannelApi.streamChannels(handleChannelUpdate, (error) => {
      console.error('Channel stream error:', error)
    })

    return () => cleanup?.()
  }, [queryClient, search, chatType, isActive, page, pageSize])

  // 处理搜索
  const handleSearch = (event: React.ChangeEvent<HTMLInputElement>) => {
    navigate(buildChannelUrl(selectedChatKey, { search: event.target.value, page: String(DEFAULT_PAGE) }), {
      replace: true,
    })
  }

  // 处理清除搜索
  const handleClearSearch = () => {
    navigate(buildChannelUrl(selectedChatKey, { search: null, page: String(DEFAULT_PAGE) }), {
      replace: true,
    })
  }

  // 处理类型筛选
  const handleChatTypeChange = (event: SelectChangeEvent) => {
    navigate(
      buildChannelUrl(selectedChatKey, { chat_type: event.target.value, page: String(DEFAULT_PAGE) }),
      { replace: true }
    )
  }

  // 处理状态筛选
  const handleActiveChange = (event: SelectChangeEvent) => {
    navigate(
      buildChannelUrl(selectedChatKey, { is_active: event.target.value, page: String(DEFAULT_PAGE) }),
      { replace: true }
    )
  }

  // 处理选择聊天
  const handleSelectChannel = (chatKey: string) => {
    navigate(buildChannelUrl(chatKey))
    if (isMobile) {
      setDrawerOpen(false)
    }
  }

  // 返回聊天列表（移动端）
  const handleBackToList = () => {
    navigate(buildChannelUrl())
  }

  // 渲染聊天列表组件
  const renderChannelList = () => (
    <>
      <Box className="p-2 flex-shrink-0">
        <Stack spacing={1.5}>
          {/* 搜索框 */}
          <TextField
            fullWidth
            size={isSmall ? 'small' : 'medium'}
            placeholder={t('search.placeholder')}
            value={search}
            onChange={handleSearch}
            InputProps={{
              startAdornment: (
                <InputAdornment position="start">
                  <SearchIcon fontSize="small" />
                </InputAdornment>
              ),
              endAdornment: search && (
                <InputAdornment position="end">
                  <IconButton size="small" onClick={handleClearSearch}>
                    <ClearIcon fontSize="small" />
                  </IconButton>
                </InputAdornment>
              ),
            }}
          />

          {/* 筛选选项 */}
          <Stack direction={isSmall ? 'column' : 'row'} spacing={1}>
            <FormControl size="small" fullWidth>
              <InputLabel>{t('filters.type')}</InputLabel>
              <Select value={chatType} label={t('filters.type')} onChange={handleChatTypeChange}>
                <MenuItem value="">{t('filters.all')}</MenuItem>
                <MenuItem value="group">{t('filters.group')}</MenuItem>
                <MenuItem value="private">{t('filters.private')}</MenuItem>
              </Select>
            </FormControl>
            <FormControl size="small" fullWidth>
              <InputLabel>{t('filters.status')}</InputLabel>
              <Select value={isActive} label={t('filters.status')} onChange={handleActiveChange}>
                <MenuItem value="">{t('filters.all')}</MenuItem>
                <MenuItem value="true">{t('filters.active')}</MenuItem>
                <MenuItem value="false">{t('filters.inactive')}</MenuItem>
              </Select>
            </FormControl>
          </Stack>
        </Stack>
      </Box>

      <Divider />

      {/* 聊天列表 */}
      <Box className="flex-1 overflow-auto">
        <ChatChannelList
          channels={channelList?.items || []}
          selectedChatKey={selectedChatKey}
          onSelectChannel={handleSelectChannel}
          isLoading={isLoading}
        />
      </Box>

      {/* 分页器 */}
      {channelList && channelList.items.length > 0 && (
        <TablePaginationStyled
          component="div"
          count={channelList.total}
          page={page - 1}
          rowsPerPage={pageSize}
          onPageChange={(_: React.MouseEvent<HTMLButtonElement> | null, newPage: number) =>
            navigate(buildChannelUrl(selectedChatKey, { page: String(newPage + 1) }), { replace: true })
          }
          onRowsPerPageChange={(
            event: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>
          ) => {
            navigate(
              buildChannelUrl(selectedChatKey, {
                page_size: event.target.value,
                page: String(DEFAULT_PAGE),
              }),
              { replace: true }
            )
          }}
          loading={isLoading}
          showFirstLastPageButtons={false}
          rowsPerPageOptions={[10, 25]}
        />
      )}
    </>
  )

  // 渲染聊天详情组件
  const renderChannelDetail = () => (
    <>
      {selectedChatKey ? (
        <ChatChannelDetail chatKey={selectedChatKey} onBack={handleBackToList} />
      ) : (
        <Card
          sx={{
            ...CARD_VARIANTS.default.styles,
            height: '100%',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            flexDirection: 'column',
          }}
        >
          <InfoIcon sx={{ fontSize: 48, color: 'text.secondary', mb: 2, opacity: 0.7 }} />
          <Typography color="textSecondary">{t('detail.selectChat')}</Typography>
          {isMobile && (
            <Button
              onClick={() => setDrawerOpen(true)}
              variant="outlined"
              startIcon={<ListIcon />}
              sx={{ mt: 2 }}
            >
              {t('actions.viewList')}
            </Button>
          )}
        </Card>
      )}
    </>
  )

  return (
    <Box className="h-full flex gap-2 overflow-hidden p-2">
      {isMobile ? (
        // 移动端布局
        <>
          {/* 主内容区 - 根据是否选择聊天，显示详情或提示 */}
          <Box className="w-full flex-1 overflow-hidden">
            {selectedChatKey ? (
              <ChatChannelDetail chatKey={selectedChatKey} onBack={handleBackToList} />
            ) : (
              <Card
                sx={{
                  ...CARD_VARIANTS.default.styles,
                  height: '100%',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  flexDirection: 'column',
                }}
              >
                <InfoIcon sx={{ fontSize: 48, color: 'text.secondary', mb: 2, opacity: 0.7 }} />
                <Typography color="textSecondary">{t('detail.selectChat')}</Typography>
                <Button
                  onClick={() => setDrawerOpen(true)}
                  variant="outlined"
                  startIcon={<ListIcon />}
                  sx={{ mt: 2 }}
                >
                  {t('actions.viewList')}
                </Button>
              </Card>
            )}
          </Box>

          {/* 抽屉式侧边栏 - 聊天列表 */}
          <Drawer
            anchor="left"
            open={drawerOpen}
            onClose={() => setDrawerOpen(false)}
            PaperProps={{
              sx: {
                width: isSmall ? '85%' : '320px',
                maxWidth: '100%',
                backgroundColor: 'transparent',
                backdropFilter: 'blur(20px)',
                borderRight: `1px solid ${theme.palette.divider}`,
                display: 'flex',
                flexDirection: 'column',
              },
            }}
          >
            {renderChannelList()}
          </Drawer>

          {/* 浮动按钮 - 打开聊天列表 */}
          <Fab
            color="primary"
            size={isSmall ? 'medium' : 'large'}
            onClick={() => setDrawerOpen(true)}
            sx={{
              position: 'fixed',
              bottom: 16,
              right: 16,
              zIndex: 1099,
            }}
          >
            <ListIcon />
          </Fab>
        </>
      ) : (
        // 桌面端布局
        <>
          <Box className="flex-1 overflow-hidden">{renderChannelDetail()}</Box>
          <Card
            sx={{
              ...CARD_VARIANTS.default.styles,
              width: '360px',
              flexShrink: 0,
              display: 'flex',
              flexDirection: 'column',
              overflow: 'hidden',
            }}
          >
            {renderChannelList()}
          </Card>
        </>
      )}
    </Box>
  )
}
