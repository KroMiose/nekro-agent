import React from 'react'
import {
  Box,
  Typography,
  Tabs,
  Tab,
  Stack,
  Chip,
  Button,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  CircularProgress,
  IconButton,
  Tooltip,
  Card,
  CardContent,
  useTheme,
  FormControl,
  Select,
  MenuItem,
  type SelectChangeEvent,
} from '@mui/material'
import {
  Group as GroupIcon,
  Person as PersonIcon,
  Refresh as RefreshIcon,
  Circle as CircleIcon,
  Sync as SyncIcon,
  ArrowBack as ArrowBackIcon,
} from '@mui/icons-material'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { chatChannelApi } from '../../../services/api/chat-channel'
import BasicInfo from './detail-tabs/BasicInfo'
import MessageHistory from './detail-tabs/MessageHistory'
import OverrideSettings from './detail-tabs/OverrideSettings'
import PluginData from './detail-tabs/PluginData'
import { CARD_VARIANTS } from '../../../theme/variants'
import { useMediaQuery } from '@mui/material'
import { useTranslation } from 'react-i18next'
import { type ChatChannelDetailTab } from '../../../router/routes'

interface ChatChannelDetailProps {
  chatKey: string
  currentTab: ChatChannelDetailTab
  onTabChange: (tab: ChatChannelDetailTab) => void
  onBack?: () => void
}

const CHAT_CHANNEL_TAB_ORDER: ChatChannelDetailTab[] = [
  'message-history',
  'override-settings',
  'basic-info',
  'plugin-data',
]

export default function ChatChannelDetail({ chatKey, currentTab, onTabChange, onBack }: ChatChannelDetailProps) {
  const [resetDialogOpen, setResetDialogOpen] = React.useState(false)
  const [isRefreshing, setIsRefreshing] = React.useState(false)
  const queryClient = useQueryClient()
  const theme = useTheme()
  const isMobile = useMediaQuery(theme.breakpoints.down('md'))
  const { t } = useTranslation('chat-channel')

  // 查询聊天详情
  const { data: channel, isLoading } = useQuery({
    queryKey: ['chat-channel-detail', chatKey],
    queryFn: () => chatChannelApi.getDetail(chatKey),
    staleTime: 30_000,
  })

  // 设置频道状态
  const { mutate: setChannelStatus, isPending: isToggling } = useMutation({
    mutationFn: (status: 'active' | 'observe' | 'disabled') => chatChannelApi.setStatus(chatKey, status),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['chat-channel-detail', chatKey] })
      queryClient.invalidateQueries({ queryKey: ['chat-channels'] })
    },
  })

  // 重置聊天
  const { mutate: resetChannel, isPending: isResetting } = useMutation({
    mutationFn: () => chatChannelApi.reset(chatKey),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['chat-channel-detail', chatKey] })
      setResetDialogOpen(false)
    },
  })

  // 刷新聊天信息
  const handleRefresh = async () => {
    setIsRefreshing(true)
    try {
      await queryClient.invalidateQueries({ queryKey: ['chat-channel-detail', chatKey] })
      await queryClient.invalidateQueries({ queryKey: ['chat-channels'] })
    } finally {
      setIsRefreshing(false)
    }
  }

  // 处理标签切换
  const handleTabChange = (_: React.SyntheticEvent, newValue: number) => {
    const nextTab = CHAT_CHANNEL_TAB_ORDER[newValue]
    if (nextTab) onTabChange(nextTab)
  }

  const currentTabIndex = Math.max(CHAT_CHANNEL_TAB_ORDER.indexOf(currentTab), 0)
  const statusOptions: Array<{
    value: 'active' | 'observe' | 'disabled'
    label: string
    color: 'success' | 'warning' | 'disabled'
  }> = [
    { value: 'active', label: t('channelDetail.activate'), color: 'success' },
    { value: 'observe', label: t('channelDetail.observe'), color: 'warning' },
    { value: 'disabled', label: t('channelDetail.deactivate'), color: 'disabled' },
  ]

  const handleStatusChange = (event: SelectChangeEvent<'active' | 'observe' | 'disabled'>) => {
    const nextStatus = event.target.value as 'active' | 'observe' | 'disabled'
    if (nextStatus === channel.status) return
    setChannelStatus(nextStatus)
  }

  if (isLoading || !channel) {
    return (
      <Card sx={{ ...CARD_VARIANTS.default.styles, height: '100%' }}>
        <Box className="h-full flex items-center justify-center">
          <CircularProgress />
        </Box>
      </Card>
    )
  }

  return (
    <Box className="h-full flex flex-col overflow-hidden gap-2">
      {/* 头部信息 */}
      <Card sx={CARD_VARIANTS.default.styles}>
        <CardContent sx={{ p: { xs: 1.5, md: 2 } }}>
          <Stack
            direction={{ xs: 'column', lg: 'row' }}
            spacing={1.5}
            alignItems={{ xs: 'stretch', lg: 'center' }}
            justifyContent="space-between"
          >
            <Stack
              direction="row"
              spacing={2}
              alignItems="flex-start"
              sx={{ minWidth: 0, flex: 1 }}
            >
              {isMobile && onBack && (
                <IconButton onClick={onBack} edge="start">
                  <ArrowBackIcon />
                </IconButton>
              )}
              {channel.chat_type === 'group' ? (
                <GroupIcon color="primary" sx={{ fontSize: 32, mt: 0.5 }} />
              ) : (
                <PersonIcon color="info" sx={{ fontSize: 32, mt: 0.5 }} />
              )}
              <Box className="flex-1 overflow-hidden">
                <Stack direction="row" spacing={1} alignItems="center" sx={{ minWidth: 0 }}>
                  <Typography variant="h6" className="font-medium truncate">
                    {channel.channel_name || t('channelDetail.unnamedChat')}
                  </Typography>
                  <Chip
                    size="small"
                    icon={channel.chat_type === 'group' ? <GroupIcon /> : <PersonIcon />}
                    label={
                      channel.chat_type === 'group'
                        ? t('channelDetail.group')
                        : t('channelDetail.private')
                    }
                    color={channel.chat_type === 'group' ? 'primary' : 'info'}
                    variant="outlined"
                    sx={{ flexShrink: 0 }}
                  />
                  <Tooltip title={t('channelDetail.refreshInfo')}>
                    <IconButton
                      size="small"
                      onClick={handleRefresh}
                      disabled={isRefreshing}
                      sx={{ ml: 0.25 }}
                    >
                      {isRefreshing ? <CircularProgress size={16} /> : <SyncIcon fontSize="small" />}
                    </IconButton>
                  </Tooltip>
                </Stack>
              </Box>
            </Stack>

            <Stack
              direction="row"
              spacing={0.75}
              alignItems="center"
              justifyContent={{ xs: 'space-between', lg: 'flex-end' }}
              useFlexGap
              sx={{ flexWrap: 'nowrap', flexShrink: 0 }}
            >
              <Button
                variant="text"
                size="small"
                color="warning"
                onClick={() => setResetDialogOpen(true)}
                startIcon={<RefreshIcon />}
                sx={{ px: 0.5, minWidth: 'auto', whiteSpace: 'nowrap' }}
              >
                重置上下文
              </Button>
              <FormControl size="small" sx={{ minWidth: 96 }}>
                <Select
                  value={channel.status}
                  onChange={handleStatusChange}
                  disabled={isToggling}
                  sx={{
                    '& .MuiSelect-select': {
                      py: 0.625,
                      pl: 1,
                      pr: 3,
                    },
                  }}
                  renderValue={value => {
                    const current = statusOptions.find(option => option.value === value)
                    if (!current) return value

                    return (
                      <Stack direction="row" spacing={0.75} alignItems="center">
                        {isToggling ? (
                          <CircularProgress size={14} />
                        ) : (
                          <CircleIcon
                            sx={{
                              fontSize: 10,
                              color: current.color === 'disabled' ? 'text.disabled' : `${current.color}.main`,
                            }}
                          />
                        )}
                        <Typography variant="body2" sx={{ fontWeight: 600 }}>
                          {current.label}
                        </Typography>
                      </Stack>
                    )
                  }}
                >
                  {statusOptions.map(option => (
                    <MenuItem key={option.value} value={option.value}>
                      <Stack direction="row" spacing={1} alignItems="center">
                        <CircleIcon
                          sx={{
                            fontSize: 10,
                            color: option.color === 'disabled' ? 'text.disabled' : `${option.color}.main`,
                          }}
                        />
                        <Typography variant="body2">{option.label}</Typography>
                      </Stack>
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>
            </Stack>
          </Stack>
        </CardContent>
      </Card>

      {/* 标签页 */}
      <Card sx={CARD_VARIANTS.default.styles}>
        <Tabs
          value={currentTabIndex}
          onChange={handleTabChange}
          variant="fullWidth"
          sx={{
            minHeight: 56,
            '& .MuiTab-root': {
              minHeight: 56,
              fontSize: '0.875rem',
              fontWeight: 600,
              textTransform: 'none',
            },
          }}
        >
          <Tab label={t('channelDetail.tabs.messageHistory')} />
          <Tab label={t('channelDetail.tabs.overrideSettings')} />
          <Tab label={t('channelDetail.tabs.basicInfo')} />
          <Tab label={t('channelDetail.tabs.pluginData')} />
        </Tabs>
      </Card>

      {/* 标签内容 */}
      <Box className="flex-1 overflow-hidden">
        {currentTab === 'basic-info' && (
          <Card sx={{ ...CARD_VARIANTS.default.styles, height: '100%', overflow: 'auto' }}>
            <BasicInfo channel={channel} />
          </Card>
        )}
        {currentTab === 'override-settings' && (
          <Card sx={{ ...CARD_VARIANTS.default.styles, height: '100%', overflow: 'auto' }}>
            <OverrideSettings chatKey={chatKey} />
          </Card>
        )}
        {currentTab === 'message-history' && (
          <Card sx={{ ...CARD_VARIANTS.default.styles, height: '100%', p: 0, overflow: 'hidden' }}>
            <MessageHistory chatKey={chatKey} canSend={channel?.can_send ?? false} aiAlwaysIncludeMsgId={channel?.ai_always_include_msg_id ?? false} />
          </Card>
        )}
        {currentTab === 'plugin-data' && (
          <Card sx={{ ...CARD_VARIANTS.default.styles, height: '100%', overflow: 'auto' }}>
            <PluginData chatKey={chatKey} />
          </Card>
        )}
      </Box>

      {/* 重置确认对话框 */}
      <Dialog open={resetDialogOpen} onClose={() => setResetDialogOpen(false)}>
        <DialogTitle>{t('channelDetail.resetDialog.title')}</DialogTitle>
        <DialogContent>
          <Typography>{t('channelDetail.resetDialog.content')}</Typography>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setResetDialogOpen(false)}>
            {t('channelDetail.resetDialog.cancel')}
          </Button>
          <Button onClick={() => resetChannel()} color="warning" disabled={isResetting}>
            {isResetting ? <CircularProgress size={20} /> : t('channelDetail.resetDialog.confirm')}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  )
}
