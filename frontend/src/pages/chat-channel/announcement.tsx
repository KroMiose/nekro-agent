import { useDeferredValue, useMemo, useState } from 'react'
import {
  Box,
  Card,
  CardContent,
  Chip,
  CircularProgress,
  Dialog,
  DialogContent,
  DialogTitle,
  Divider,
  LinearProgress,
  TextField,
  Typography,
  useTheme,
} from '@mui/material'
import SendRoundedIcon from '@mui/icons-material/SendRounded'
import CampaignIcon from '@mui/icons-material/Campaign'
import { alpha } from '@mui/material/styles'
import { useMutation, useQuery } from '@tanstack/react-query'
import {
  chatChannelApi,
  type ChatChannel,
} from '../../services/api/chat-channel'
import { CARD_VARIANTS } from '../../theme/variants'
import TablePaginationStyled from '../../components/common/TablePaginationStyled'
import { useNotification } from '../../hooks/useNotification'
import { useTranslation } from 'react-i18next'
import ChannelSelectorToolbar from './components/announcement/ChannelSelectorToolbar'
import ChannelSelectorList from './components/announcement/ChannelSelectorList'
import SelectedChannelSummary from './components/announcement/SelectedChannelSummary'
import ActionButton from '../../components/common/ActionButton'

const DEFAULT_PAGE = 1
const DEFAULT_PAGE_SIZE = 20

interface SendingState {
  total: number
  completed: number
  successCount: number
  failureCount: number
  currentChannelName: string
  phase: 'sending' | 'waiting'
}

const sleep = (ms: number) => new Promise(resolve => window.setTimeout(resolve, ms))

export default function ChatAnnouncementPage() {
  const theme = useTheme()
  const notification = useNotification()
  const { t } = useTranslation('chat-announcement')

  const [search, setSearch] = useState('')
  const [chatType, setChatType] = useState('')
  const [status, setStatus] = useState('')
  const [page, setPage] = useState(DEFAULT_PAGE)
  const [pageSize, setPageSize] = useState(DEFAULT_PAGE_SIZE)
  const [message, setMessage] = useState('')
  const [selectedChannels, setSelectedChannels] = useState<Record<string, ChatChannel>>({})
  const [sendingState, setSendingState] = useState<SendingState | null>(null)

  const deferredSearch = useDeferredValue(search)

  const { data, isLoading } = useQuery({
    queryKey: ['chat-announcement-channels', deferredSearch, chatType, status, page, pageSize],
    queryFn: () =>
      chatChannelApi.getList({
        page,
        page_size: pageSize,
        search: deferredSearch || undefined,
        chat_type: chatType || undefined,
        status: status === '' ? undefined : status as 'active' | 'observe' | 'disabled',
      }),
    staleTime: 30_000,
  })

  const visibleChannels = data?.items ?? []
  const trimmedMessage = message.trim()
  const selectedChannelList = useMemo(
    () =>
      Object.values(selectedChannels).sort((left, right) => {
        const leftName = left.channel_name || left.chat_key
        const rightName = right.channel_name || right.chat_key
        return leftName.localeCompare(rightName, 'zh-CN')
      }),
    [selectedChannels]
  )
  const selectedChatKeySet = useMemo(
    () => new Set(Object.keys(selectedChannels)),
    [selectedChannels]
  )

  const announcementMutation = useMutation({
    mutationFn: async (payload: { channels: ChatChannel[]; message: string }) => {
      let successCount = 0
      let failureCount = 0

      setSendingState({
        total: payload.channels.length,
        completed: 0,
        successCount: 0,
        failureCount: 0,
        currentChannelName: payload.channels[0]?.channel_name || payload.channels[0]?.chat_key || '',
        phase: 'sending',
      })

      for (const [index, channel] of payload.channels.entries()) {
        const channelName = channel.channel_name || channel.chat_key
        setSendingState(current =>
          current
            ? {
                ...current,
                currentChannelName: channelName,
                phase: 'sending',
              }
            : current
        )

        try {
          const result = await chatChannelApi.sendMessage(
            channel.chat_key,
            payload.message,
            undefined,
            'none'
          )
          if (result.ok) {
            successCount += 1
          } else {
            failureCount += 1
          }
        } catch {
          failureCount += 1
        }

        setSendingState(current =>
          current
            ? {
                ...current,
                completed: index + 1,
                successCount,
                failureCount,
              }
            : current
        )

        if (index < payload.channels.length - 1) {
          setSendingState(current =>
            current
              ? {
                  ...current,
                  phase: 'waiting',
                }
              : current
          )
          await sleep(Math.round((1 + Math.random() * 4) * 1000))
        }
      }

      return {
        total: payload.channels.length,
        successCount,
        failureCount,
      }
    },
    onSuccess: result => {
      if (result.failureCount === 0) {
        notification.success(t('result.allSuccess'))
        setMessage('')
        return
      }

      if (result.successCount > 0) {
        notification.warning(
          `${t('result.success', { count: result.successCount })} / ${t('result.failure', { count: result.failureCount })}`
        )
        return
      }

      notification.error(t('result.failure', { count: result.failureCount }))
    },
    onError: error => {
      notification.error(error instanceof Error ? error.message : String(error))
    },
    onSettled: () => {
      setSendingState(null)
    },
  })

  const toggleChannel = (channel: ChatChannel) => {
    setSelectedChannels(previous => {
      if (previous[channel.chat_key]) {
        const { [channel.chat_key]: _removed, ...next } = previous
        return next
      }
      return {
        ...previous,
        [channel.chat_key]: channel,
      }
    })
  }

  const selectVisibleChannels = () => {
    setSelectedChannels(previous => {
      const next = { ...previous }
      visibleChannels.forEach(channel => {
        next[channel.chat_key] = channel
      })
      return next
    })
  }

  const clearSelection = () => {
    setSelectedChannels({})
  }

  const removeSelectedChannel = (chatKey: string) => {
    setSelectedChannels(previous => {
      const { [chatKey]: _removed, ...next } = previous
      return next
    })
  }

  const handleSend = () => {
    if (selectedChannelList.length === 0) {
      notification.warning(t('composer.selectionRequired'))
      return
    }
    if (!trimmedMessage) {
      notification.warning(t('composer.messageRequired'))
      return
    }

    announcementMutation.mutate({
      channels: selectedChannelList,
      message: trimmedMessage,
    })
  }

  const progressValue = sendingState
    ? Math.round((sendingState.completed / Math.max(sendingState.total, 1)) * 100)
    : 0

  return (
    <Box
      sx={{
        p: 2,
        height: '100%',
        minHeight: 0,
        display: 'flex',
        flexDirection: 'column',
        gap: 2,
        overflow: 'hidden',
        boxSizing: 'border-box',
      }}
    >
      <Card
        sx={{
          ...CARD_VARIANTS.default.styles,
          overflow: 'hidden',
          background: `linear-gradient(135deg, ${alpha(theme.palette.primary.main, 0.16)} 0%, ${alpha(theme.palette.info.main, 0.08)} 55%, transparent 100%)`,
        }}
      >
        <CardContent
          sx={{
            display: 'flex',
            flexWrap: 'wrap',
            justifyContent: 'space-between',
            gap: 2,
            alignItems: 'flex-start',
          }}
        >
          <Box sx={{ display: 'flex', gap: 1.5, alignItems: 'flex-start' }}>
            <Box
              sx={{
                width: 48,
                height: 48,
                borderRadius: '16px',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                bgcolor: alpha(theme.palette.primary.main, 0.14),
                color: 'primary.main',
                flexShrink: 0,
              }}
            >
              <CampaignIcon />
            </Box>

            <Box>
              <Typography variant="h5" sx={{ fontWeight: 800, mb: 0.5 }}>
                {t('title')}
              </Typography>
              <Typography variant="body2" color="text.secondary">
                {t('subtitle')}
              </Typography>
            </Box>
          </Box>

          <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1 }}>
            <Chip
              color="primary"
              variant="outlined"
              label={t('stats.selected', { count: selectedChannelList.length })}
            />
            <Chip
              color="info"
              variant="outlined"
              label={t('stats.filtered', { count: data?.total ?? 0 })}
            />
          </Box>
        </CardContent>
      </Card>

      <Dialog
        open={Boolean(sendingState)}
        fullWidth
        maxWidth="xs"
        PaperProps={{
          sx: {
            borderRadius: 3,
          },
        }}
      >
        <DialogTitle>{t('progress.title')}</DialogTitle>
        <DialogContent sx={{ pt: 1, pb: 3 }}>
          {sendingState && (
            <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5 }}>
                <CircularProgress
                  size={22}
                  color={sendingState.phase === 'sending' ? 'primary' : 'inherit'}
                />
                <Box sx={{ minWidth: 0 }}>
                  <Typography variant="body2" sx={{ fontWeight: 700 }}>
                    {sendingState.phase === 'sending'
                      ? t('progress.sending')
                      : t('progress.waiting')}
                  </Typography>
                  <Typography variant="caption" color="text.secondary">
                    {t('progress.current', { name: sendingState.currentChannelName })}
                  </Typography>
                </Box>
              </Box>

              <LinearProgress
                variant="determinate"
                value={progressValue}
                sx={{ height: 8, borderRadius: 999 }}
              />

              <Box
                sx={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  gap: 1,
                  flexWrap: 'wrap',
                }}
              >
                <Typography variant="body2">
                  {t('progress.count', {
                    completed: sendingState.completed,
                    total: sendingState.total,
                  })}
                </Typography>
                <Typography variant="caption" color="text.secondary">
                  {t('progress.summary', {
                    success: sendingState.successCount,
                    failure: sendingState.failureCount,
                  })}
                </Typography>
              </Box>
            </Box>
          )}
        </DialogContent>
      </Dialog>

      <Box
        sx={{
          display: 'grid',
          gap: 2,
          flex: 1,
          minHeight: 0,
          overflow: 'hidden',
          gridTemplateColumns: {
            xs: '1fr',
            xl: 'minmax(360px, 420px) minmax(0, 1fr)',
          },
        }}
      >
        <Card sx={{ ...CARD_VARIANTS.default.styles, display: 'flex', flexDirection: 'column', minHeight: 0 }}>
          <CardContent sx={{ display: 'flex', flexDirection: 'column', gap: 2, flex: 1, minHeight: 0 }}>
            <ChannelSelectorToolbar
              search={search}
              chatType={chatType}
              status={status}
              selectedCount={selectedChannelList.length}
              visibleCount={visibleChannels.length}
              onSearchChange={value => {
                setSearch(value)
                setPage(DEFAULT_PAGE)
              }}
              onChatTypeChange={value => {
                setChatType(value)
                setPage(DEFAULT_PAGE)
              }}
              onStatusChange={value => {
                setStatus(value)
                setPage(DEFAULT_PAGE)
              }}
              onSelectVisible={selectVisibleChannels}
              onClearSelection={clearSelection}
            />

            <Divider />

            <Box sx={{ flex: 1, minHeight: 0, overflowY: 'auto', pr: 0.5 }}>
              <ChannelSelectorList
                channels={visibleChannels}
                selectedChatKeys={selectedChatKeySet}
                loading={isLoading}
                onToggle={toggleChannel}
              />
            </Box>
          </CardContent>

          <TablePaginationStyled
            component="div"
            count={data?.total ?? 0}
            page={page - 1}
            rowsPerPage={pageSize}
            rowsPerPageOptions={[10, 20, 50]}
            onPageChange={(_, nextPage) => setPage(nextPage + 1)}
            onRowsPerPageChange={event => {
              setPage(DEFAULT_PAGE)
              setPageSize(parseInt(event.target.value, 10))
            }}
            loading={isLoading}
            showFirstLastPageButtons={true}
          />
        </Card>

        <Box
          sx={{
            display: 'flex',
            flexDirection: 'column',
            gap: 2,
            minHeight: 0,
            overflowY: 'auto',
            pr: { xl: 0.5 },
          }}
        >
          <Card sx={CARD_VARIANTS.default.styles}>
            <CardContent sx={{ display: 'flex', flexDirection: 'column', gap: 1.5 }}>
              <Box
                sx={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  gap: 1,
                  flexWrap: 'wrap',
                  alignItems: 'center',
                }}
              >
                <Typography variant="h6" sx={{ fontWeight: 700 }}>
                  {t('composer.title')}
                </Typography>
              </Box>

              <TextField
                fullWidth
                multiline
                minRows={5}
                maxRows={10}
                label={t('composer.messageLabel')}
                placeholder={t('composer.messagePlaceholder')}
                value={message}
                onChange={event => setMessage(event.target.value)}
              />

              <Box
                sx={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  gap: 1,
                  flexWrap: 'wrap',
                  alignItems: 'center',
                }}
              >
                <Typography variant="caption" color="text.secondary">
                  {t('composer.helper')}
                </Typography>
                <Chip
                  size="small"
                  color={trimmedMessage ? 'success' : 'default'}
                  variant="outlined"
                  label={t('composer.length', { count: trimmedMessage.length })}
                />
              </Box>
            </CardContent>
          </Card>

          <Card sx={{ ...CARD_VARIANTS.default.styles, minHeight: 0 }}>
            <CardContent>
              <SelectedChannelSummary
                channels={selectedChannelList}
                onRemove={removeSelectedChannel}
                onClear={clearSelection}
              />
            </CardContent>
          </Card>
        </Box>
      </Box>

      <Card
        sx={{
          ...CARD_VARIANTS.glassmorphism.styles,
          position: 'sticky',
          bottom: 0,
          zIndex: 2,
          borderRadius: '20px',
          boxShadow: theme.shadows[8],
        }}
      >
        <CardContent
          sx={{
            display: 'flex',
            flexWrap: 'wrap',
            gap: 1.5,
            alignItems: 'center',
            justifyContent: 'space-between',
          }}
        >
          <Box sx={{ minWidth: 0 }}>
            <Typography variant="subtitle2" sx={{ fontWeight: 800 }}>
              {t('composer.actionTitle')}
            </Typography>
            <Typography variant="body2" color="text.secondary">
              {selectedChannelList.length > 0
                ? t('composer.actionReady', {
                    channels: selectedChannelList.length,
                    count: trimmedMessage.length,
                  })
                : t('composer.selectionRequired')}
            </Typography>
          </Box>

          <ActionButton
            tone="primary"
            size="medium"
            startIcon={<SendRoundedIcon />}
            onClick={handleSend}
            disabled={announcementMutation.isPending}
            sx={{
              minWidth: { xs: '100%', sm: 220 },
              borderRadius: '12px',
            }}
          >
            {announcementMutation.isPending
              ? t('composer.sending')
              : t('composer.send', { count: selectedChannelList.length })}
          </ActionButton>
        </CardContent>
      </Card>
    </Box>
  )
}
