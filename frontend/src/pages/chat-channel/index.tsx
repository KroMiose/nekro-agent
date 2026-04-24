import { useDeferredValue, useMemo, useState, useEffect } from 'react'
import {
  Box,
  Typography,
  Stack,
  Divider,
  useTheme,
  useMediaQuery,
  Drawer,
  Fab,
  Card,
} from '@mui/material'
import {
  List as ListIcon,
  Info as InfoIcon,
} from '@mui/icons-material'
import { useNavigate, useParams, useSearchParams } from 'react-router-dom'
import ChatChannelList from './components/ChatChannelList'
import ChatChannelDetail from './components/ChatChannelDetail'
import { CARD_VARIANTS } from '../../theme/variants'
import { useTranslation } from 'react-i18next'
import SearchField from '../../components/common/SearchField'
import FilterSelect from '../../components/common/FilterSelect'
import ActionButton from '../../components/common/ActionButton'
import {
  chatChannelPath,
  DEFAULT_CHAT_CHANNEL_DETAIL_TAB,
  isChatChannelDetailTab,
  type ChatChannelDetailTab,
} from '../../router/routes'
import { useChannelDirectoryContext } from '../../contexts/ChannelDirectoryContext'

export default function ChatChannelPage() {
  const [drawerOpen, setDrawerOpen] = useState(false)

  const theme = useTheme()
  const isMobile = useMediaQuery(theme.breakpoints.down('md'))
  const isSmall = useMediaQuery(theme.breakpoints.down('sm'))
  const { t } = useTranslation('chat-channel')
  const navigate = useNavigate()
  const { chatKey, tab } = useParams<{ chatKey: string; tab: string }>()
  const [searchParams] = useSearchParams()
  const selectedChatKey = chatKey ?? null
  const selectedTab = isChatChannelDetailTab(tab) ? tab : null

  // 本地搜索 / 筛选状态（从 sessionStorage 恢复，保证路由重挂载后不丢失）
  const [search, setSearch] = useState(() => sessionStorage.getItem('chatChannel.search') ?? '')
  const [chatType, setChatType] = useState(() => sessionStorage.getItem('chatChannel.chatType') ?? '')
  const [status, setStatus] = useState(() => sessionStorage.getItem('chatChannel.status') ?? '')

  useEffect(() => { sessionStorage.setItem('chatChannel.search', search) }, [search])
  useEffect(() => { sessionStorage.setItem('chatChannel.chatType', chatType) }, [chatType])
  useEffect(() => { sessionStorage.setItem('chatChannel.status', status) }, [status])

  // 使用全局频道目录
  const { channels, isLoading } = useChannelDirectoryContext()

  // 延迟搜索值，避免每次按键都触发全量过滤
  const deferredSearch = useDeferredValue(search)

  // 前端过滤
  const filteredChannels = useMemo(() => {
    let result = channels
    if (deferredSearch) {
      const lower = deferredSearch.toLowerCase()
      result = result.filter(
        ch =>
          ch.chat_key.toLowerCase().includes(lower) ||
          (ch.channel_name ?? '').toLowerCase().includes(lower),
      )
    }
    if (chatType) {
      result = result.filter(ch => ch.chat_type === chatType)
    }
    if (status) {
      result = result.filter(ch => ch.status === status)
    }
    return result
  }, [channels, deferredSearch, chatType, status])

  useEffect(() => {
    const legacyChatKey = searchParams.get('chat_key')
    if (!legacyChatKey) return

    const nextParams = new URLSearchParams(searchParams)
    nextParams.delete('chat_key')
    const nextQuery = nextParams.toString()
    navigate(`${chatChannelPath(legacyChatKey, DEFAULT_CHAT_CHANNEL_DETAIL_TAB)}${nextQuery ? `?${nextQuery}` : ''}`, { replace: true })
  }, [navigate, searchParams])

  useEffect(() => {
    if (!selectedChatKey || selectedTab) return
    const nextQuery = searchParams.toString()
    navigate(
      `${chatChannelPath(selectedChatKey, DEFAULT_CHAT_CHANNEL_DETAIL_TAB)}${nextQuery ? `?${nextQuery}` : ''}`,
      { replace: true },
    )
  }, [navigate, searchParams, selectedChatKey, selectedTab])

  const buildChannelUrl = (
    nextChatKey?: string | null,
    nextTab?: ChatChannelDetailTab | null,
  ) => {
    const basePath = chatChannelPath(nextChatKey, nextChatKey ? (nextTab ?? DEFAULT_CHAT_CHANNEL_DETAIL_TAB) : null)
    return basePath
  }

  const handleDetailTabChange = (nextTab: ChatChannelDetailTab) => {
    if (!selectedChatKey) return
    navigate(buildChannelUrl(selectedChatKey, nextTab))
  }

  // 处理选择聊天
  const handleSelectChannel = (chatKey: string) => {
    navigate(buildChannelUrl(chatKey, selectedTab ?? DEFAULT_CHAT_CHANNEL_DETAIL_TAB))
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
      <Box sx={{ p: { xs: 1.25, sm: 1.5 }, flexShrink: 0, bgcolor: 'background.paper' }}>
        <Stack spacing={1.5}>
          {/* 搜索框 */}
          <SearchField
            fullWidth
            size={isSmall ? 'small' : 'medium'}
            placeholder={t('search.placeholder')}
            value={search}
            onChange={setSearch}
            onClear={() => setSearch('')}
          />

          {/* 筛选选项 */}
          <Stack direction={isSmall ? 'column' : 'row'} spacing={1}>
            <FilterSelect
              label={t('filters.type')}
              value={chatType}
              onChange={setChatType}
              options={[
                { value: '', label: t('filters.all') },
                { value: 'group', label: t('filters.group') },
                { value: 'private', label: t('filters.private') },
              ]}
            />
            <FilterSelect
              label={t('filters.status')}
              value={status}
              onChange={setStatus}
              options={[
                { value: '', label: t('filters.all') },
                { value: 'active', label: t('filters.active') },
                { value: 'observe', label: t('filters.observe') },
                { value: 'disabled', label: t('filters.inactive') },
              ]}
            />
          </Stack>
        </Stack>
      </Box>

      <Divider />

      {/* 聊天列表 */}
      <Box sx={{ flex: 1, minHeight: 0, overflow: 'auto', bgcolor: 'background.paper' }}>
        <ChatChannelList
          channels={filteredChannels}
          selectedChatKey={selectedChatKey}
          onSelectChannel={handleSelectChannel}
          isLoading={isLoading}
        />
      </Box>
    </>
  )

  // 渲染聊天详情组件
  const renderChannelDetail = () => (
    <>
      {selectedChatKey ? (
        <ChatChannelDetail
          chatKey={selectedChatKey}
          currentTab={selectedTab ?? DEFAULT_CHAT_CHANNEL_DETAIL_TAB}
          onTabChange={handleDetailTabChange}
          onBack={handleBackToList}
        />
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
            <ActionButton
              onClick={() => setDrawerOpen(true)}
              variant="outlined"
              startIcon={<ListIcon />}
              sx={{ mt: 2 }}
            >
              {t('actions.viewList')}
            </ActionButton>
          )}
        </Card>
      )}
    </>
  )

  return (
    <Box className="h-full flex gap-2 overflow-hidden p-2 box-border">
      {isMobile ? (
        // 移动端布局
        <>
          {/* 主内容区 - 根据是否选择聊天，显示详情或提示 */}
          <Box className="w-full flex-1 overflow-hidden">
            {selectedChatKey ? (
              <ChatChannelDetail
                chatKey={selectedChatKey}
                currentTab={selectedTab ?? DEFAULT_CHAT_CHANNEL_DETAIL_TAB}
                onTabChange={handleDetailTabChange}
                onBack={handleBackToList}
              />
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
                <ActionButton
                  onClick={() => setDrawerOpen(true)}
                  variant="outlined"
                  startIcon={<ListIcon />}
                  sx={{ mt: 2 }}
                >
                  {t('actions.viewList')}
                </ActionButton>
              </Card>
            )}
          </Box>

          {/* 抽屉式侧边栏 - 聊天列表 */}
          <Drawer
            anchor="left"
            open={drawerOpen}
            onClose={() => setDrawerOpen(false)}
            ModalProps={{
              keepMounted: true,
            }}
            PaperProps={{
              sx: {
                width: isSmall ? 'min(88vw, 360px)' : '360px',
                maxWidth: '100vw',
                backgroundColor: 'background.paper',
                backgroundImage: 'none',
                borderRight: `1px solid ${theme.palette.divider}`,
                display: 'flex',
                flexDirection: 'column',
                overflow: 'hidden',
                boxShadow: theme.shadows[12],
              },
            }}
          >
            {renderChannelList()}
          </Drawer>

          {/* 浮动按钮 - 打开聊天列表 */}
          {!drawerOpen && (
            <Fab
              color="primary"
              size={isSmall ? 'medium' : 'large'}
              onClick={() => setDrawerOpen(true)}
              sx={{
                position: 'fixed',
                bottom: 16,
                right: 16,
                zIndex: theme.zIndex.drawer - 1,
              }}
            >
              <ListIcon />
            </Fab>
          )}
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
