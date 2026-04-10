import { useDeferredValue, useMemo, useState } from 'react'
import {
  Box,
  Card,
  CardContent,
  CircularProgress,
  Dialog,
  DialogContent,
  DialogTitle,
  Divider,
  LinearProgress,
  TextField,
  Tooltip,
  Typography,
} from '@mui/material'
import SendRoundedIcon from '@mui/icons-material/SendRounded'
import InfoOutlinedIcon from '@mui/icons-material/InfoOutlined'
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
import IconActionButton from '../../components/common/IconActionButton'

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
            sx={{
              width: '100%',
              overflow: 'hidden',
              '.MuiTablePagination-toolbar': {
                minHeight: 52,
                px: 1,
                gap: 0.5,
                flexWrap: { xs: 'wrap', md: 'nowrap' },
              },
              '.MuiTablePagination-spacer': {
                display: { xs: 'none', md: 'block' },
              },
              '.MuiTablePagination-selectLabel, .MuiTablePagination-displayedRows': {
                margin: 0,
                flexShrink: 0,
              },
              '.MuiTablePagination-actions': {
                marginLeft: 'auto',
                flexShrink: 0,
              },
            }}
          />
        </Card>

        <Box
          sx={{
            display: 'flex',
            flexDirection: 'column',
            minHeight: 0,
            pr: { xl: 0.5 },
          }}
        >
          <Card sx={{ ...CARD_VARIANTS.default.styles, flex: 1, minHeight: 0 }}>
            <CardContent sx={{ display: 'flex', flexDirection: 'column', gap: 1.5, height: '100%', minHeight: 0 }}>
              <Box
                sx={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  gap: 1,
                  flexWrap: 'wrap',
                  alignItems: 'center',
                }}
              >
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.75 }}>
                  <Typography variant="h6" sx={{ fontWeight: 700 }}>
                    {t('composer.title')}
                  </Typography>
                  <Tooltip title={t('subtitle')} arrow placement="top">
                    <span>
                      <IconActionButton
                        size="small"
                        aria-label={t('composer.help')}
                      >
                        <InfoOutlinedIcon fontSize="small" />
                      </IconActionButton>
                    </span>
                  </Tooltip>
                </Box>

                <Typography variant="body2" color="text.secondary">
                  {t('composer.selectionSummary', {
                    selected: selectedChannelList.length,
                    filtered: data?.total ?? 0,
                  })}
                </Typography>
              </Box>

              <SelectedChannelSummary
                channels={selectedChannelList}
                onRemove={removeSelectedChannel}
                onClear={clearSelection}
              />

              <Divider />

              <Box
                sx={{
                  display: 'flex',
                  flexDirection: 'column',
                  gap: 1.25,
                  flex: 1,
                  minHeight: { xs: 260, xl: 320 },
                }}
              >
                <TextField
                  fullWidth
                  multiline
                  label={t('composer.messageLabel')}
                  placeholder={t('composer.messagePlaceholder')}
                  value={message}
                  onChange={event => setMessage(event.target.value)}
                  sx={{
                    flex: 1,
                    minHeight: 0,
                    '& .MuiInputBase-root': {
                      height: '100%',
                      alignItems: 'flex-start',
                    },
                    '& .MuiInputBase-inputMultiline': {
                      height: '100% !important',
                      overflow: 'auto !important',
                    },
                  }}
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
                  <Typography variant="caption" color="text.secondary">
                    {t('composer.length', { count: trimmedMessage.length })}
                  </Typography>
                </Box>
              </Box>

              <Divider />

              <Box
                sx={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  gap: 1.5,
                  flexWrap: 'wrap',
                  alignItems: 'center',
                }}
              >
                <Box sx={{ minWidth: 0 }}>
                  <Typography variant="subtitle2" sx={{ fontWeight: 700 }}>
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
                  }}
                >
                  {announcementMutation.isPending
                    ? t('composer.sending')
                    : t('composer.send', { count: selectedChannelList.length })}
                </ActionButton>
              </Box>
            </CardContent>
          </Card>
        </Box>
      </Box>

    </Box>
  )
}
