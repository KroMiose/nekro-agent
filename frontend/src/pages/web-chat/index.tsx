import { useDeferredValue, useEffect, useMemo, useRef, useState, type ChangeEvent, type KeyboardEvent } from 'react'
import {
  Box,
  Alert,
  Chip,
  CircularProgress,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  Divider,
  Drawer,
  Stack,
  TextField,
  Tooltip,
  Typography,
  useMediaQuery,
  useTheme,
} from '@mui/material'
import AddIcon from '@mui/icons-material/Add'
import AttachFileIcon from '@mui/icons-material/AttachFile'
import ChatIcon from '@mui/icons-material/Chat'
import CloseIcon from '@mui/icons-material/Close'
import DeleteIcon from '@mui/icons-material/Delete'
import EditIcon from '@mui/icons-material/Edit'
import OpenInNewIcon from '@mui/icons-material/OpenInNew'
import RefreshIcon from '@mui/icons-material/Refresh'
import SendIcon from '@mui/icons-material/Send'
import TuneIcon from '@mui/icons-material/Tune'
import ViewSidebarIcon from '@mui/icons-material/ViewSidebar'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useTranslation } from 'react-i18next'
import { useNavigate } from 'react-router-dom'

import ActionButton from '../../components/common/ActionButton'
import IconActionButton from '../../components/common/IconActionButton'
import SearchField from '../../components/common/SearchField'
import { useNotification } from '../../hooks/useNotification'
import MessageHistory from '../chat-channel/components/detail-tabs/MessageHistory'
import { chatChannelPath, DEFAULT_CHAT_CHANNEL_DETAIL_TAB } from '../../router/routes'
import { adaptersApi } from '../../services/api/adapters'
import { webChatApi, getWebSessionDisplayName, type WebSession } from '../../services/api/web-chat'
import { CARD_VARIANTS } from '../../theme/variants'

const SELECTED_SESSION_STORAGE_KEY = 'webChat.selectedChatKey'
const DEFAULT_MESSAGE_MAX_LENGTH = 8000
const DEFAULT_FILE_UPLOAD_MAX_SIZE_MB = 100

function statusColor(status: WebSession['status']): 'success' | 'warning' | 'default' {
  if (status === 'active') return 'success'
  if (status === 'observe') return 'warning'
  return 'default'
}

export default function WebChatPage() {
  const { t } = useTranslation('web-chat')
  const theme = useTheme()
  const isMobile = useMediaQuery(theme.breakpoints.down('md'))
  const isSmall = useMediaQuery(theme.breakpoints.down('sm'))
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const notification = useNotification()
  const inputRef = useRef<HTMLInputElement>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)

  const [search, setSearch] = useState('')
  const deferredSearch = useDeferredValue(search)
  const [selectedChatKey, setSelectedChatKey] = useState(() => sessionStorage.getItem(SELECTED_SESSION_STORAGE_KEY) ?? '')
  const [drawerOpen, setDrawerOpen] = useState(false)
  const [inputValue, setInputValue] = useState('')
  const [selectedFile, setSelectedFile] = useState<File | null>(null)
  const [isComposing, setIsComposing] = useState(false)
  const [editingSession, setEditingSession] = useState<WebSession | null>(null)
  const [editingName, setEditingName] = useState('')
  const [deletingSession, setDeletingSession] = useState<WebSession | null>(null)

  useEffect(() => {
    if (selectedChatKey) {
      sessionStorage.setItem(SELECTED_SESSION_STORAGE_KEY, selectedChatKey)
    } else {
      sessionStorage.removeItem(SELECTED_SESSION_STORAGE_KEY)
    }
  }, [selectedChatKey])

  const adapterStatusQuery = useQuery({
    queryKey: ['web-chat', 'adapter-status'],
    queryFn: () => adaptersApi.getAdapterStatus('web'),
    retry: false,
  })

  const adapterReady = adapterStatusQuery.data?.status === 'enabled'

  const allSessionsQuery = useQuery({
    queryKey: ['web-chat', 'sessions', 'all'],
    queryFn: () => webChatApi.getSessions({ page: 1, page_size: 100 }),
    enabled: adapterReady,
    staleTime: 15_000,
  })

  const filteredSessionsQuery = useQuery({
    queryKey: ['web-chat', 'sessions', 'search', deferredSearch],
    queryFn: () => webChatApi.getSessions({ page: 1, page_size: 100, search: deferredSearch }),
    enabled: adapterReady && Boolean(deferredSearch),
    staleTime: 15_000,
  })

  const allSessions = useMemo(() => allSessionsQuery.data?.items ?? [], [allSessionsQuery.data?.items])
  const webChatLimits = allSessionsQuery.data?.limits ?? filteredSessionsQuery.data?.limits
  const messageMaxLength = webChatLimits?.message_max_length ?? DEFAULT_MESSAGE_MAX_LENGTH
  const fileUploadMaxSizeMb = webChatLimits?.file_upload_max_size_mb ?? DEFAULT_FILE_UPLOAD_MAX_SIZE_MB
  const sessionsQuery = deferredSearch ? filteredSessionsQuery : allSessionsQuery
  const sessions = useMemo(
    () => (deferredSearch ? filteredSessionsQuery.data?.items ?? [] : allSessions),
    [allSessions, deferredSearch, filteredSessionsQuery.data?.items],
  )
  const selectedSession = useMemo(
    () => allSessions.find(session => session.chat_key === selectedChatKey) ?? null,
    [allSessions, selectedChatKey],
  )
  const composerDisabled = selectedSession?.status === 'disabled'

  useEffect(() => {
    if (!adapterReady || allSessionsQuery.isLoading || selectedChatKey || allSessions.length === 0) return
    const firstSession = allSessions[0]
    if (firstSession) {
      setSelectedChatKey(firstSession.chat_key)
    }
  }, [adapterReady, allSessions, allSessionsQuery.isLoading, selectedChatKey])

  const createSessionMutation = useMutation({
    mutationFn: () => webChatApi.createSession(),
    onSuccess: async session => {
      notification.success(t('notifications.sessionCreated'))
      setSelectedChatKey(session.chat_key)
      await queryClient.invalidateQueries({ queryKey: ['web-chat', 'sessions'] })
      if (isMobile) {
        setDrawerOpen(false)
      }
    },
    onError: error => {
      const message = error instanceof Error ? error.message : String(error)
      notification.error(`${t('notifications.sessionCreateFailed')}: ${message}`)
    },
  })

  const updateSessionMutation = useMutation({
    mutationFn: ({ chatKey, name }: { chatKey: string; name: string }) => webChatApi.updateSession(chatKey, name),
    onSuccess: async () => {
      notification.success(t('notifications.sessionUpdated'))
      setEditingSession(null)
      setEditingName('')
      await queryClient.invalidateQueries({ queryKey: ['web-chat', 'sessions'] })
    },
    onError: error => {
      const message = error instanceof Error ? error.message : String(error)
      notification.error(`${t('notifications.sessionUpdateFailed')}: ${message}`)
    },
  })

  const deleteSessionMutation = useMutation({
    mutationFn: async (chatKey: string) => {
      await webChatApi.deleteSession(chatKey)
      return chatKey
    },
    onSuccess: async deletedChatKey => {
      notification.success(t('notifications.sessionDeleted'))
      setDeletingSession(null)
      if (selectedChatKey === deletedChatKey) {
        const nextSession = sessions.find(session => session.chat_key !== deletedChatKey)
        setSelectedChatKey(nextSession?.chat_key ?? '')
      }
      await queryClient.invalidateQueries({ queryKey: ['web-chat', 'sessions'] })
      await queryClient.removeQueries({ queryKey: ['chat-messages', deletedChatKey] })
    },
    onError: error => {
      const message = error instanceof Error ? error.message : String(error)
      notification.error(`${t('notifications.sessionDeleteFailed')}: ${message}`)
    },
  })

  const sendMessageMutation = useMutation({
    mutationFn: ({ chatKey, content, file }: { chatKey: string; content: string; file: File | null }) =>
      file ? webChatApi.sendUploadMessage(chatKey, content, file) : webChatApi.sendMessage(chatKey, content),
    onSuccess: async (_data, variables) => {
      setInputValue('')
      setSelectedFile(null)
      if (fileInputRef.current) {
        fileInputRef.current.value = ''
      }
      await queryClient.invalidateQueries({ queryKey: ['web-chat', 'sessions'] })
      await queryClient.invalidateQueries({ queryKey: ['chat-messages', variables.chatKey] })
    },
    onError: error => {
      const message = error instanceof Error ? error.message : String(error)
      notification.error(`${t('notifications.sendFailed')}: ${message}`)
    },
  })

  const handleSelectSession = (chatKey: string) => {
    setSelectedChatKey(chatKey)
    if (isMobile) {
      setDrawerOpen(false)
    }
  }

  const openEditSession = (session: WebSession) => {
    setEditingSession(session)
    setEditingName(getWebSessionDisplayName(session))
  }

  const handleUpdateSession = () => {
    if (!editingSession || updateSessionMutation.isPending) return
    updateSessionMutation.mutate({
      chatKey: editingSession.chat_key,
      name: editingName.trim(),
    })
  }

  const handleDeleteSession = () => {
    if (!deletingSession || deleteSessionMutation.isPending) return
    deleteSessionMutation.mutate(deletingSession.chat_key)
  }

  const handleSend = () => {
    const content = inputValue.trim()
    if (!selectedSession || composerDisabled || (!content && !selectedFile) || sendMessageMutation.isPending) return
    if (content.length > messageMaxLength) {
      notification.warning(t('notifications.messageTooLong', { count: messageMaxLength }))
      return
    }
    if (selectedFile && selectedFile.size > fileUploadMaxSizeMb * 1024 * 1024) {
      notification.warning(t('notifications.fileTooLarge', { count: fileUploadMaxSizeMb }))
      return
    }
    sendMessageMutation.mutate({ chatKey: selectedSession.chat_key, content, file: selectedFile })
  }

  const handleFileChange = (event: ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0] ?? null
    if (file && file.size > fileUploadMaxSizeMb * 1024 * 1024) {
      notification.warning(t('notifications.fileTooLarge', { count: fileUploadMaxSizeMb }))
      if (fileInputRef.current) {
        fileInputRef.current.value = ''
      }
      setSelectedFile(null)
      return
    }
    setSelectedFile(file)
  }

  const clearSelectedFile = () => {
    setSelectedFile(null)
    if (fileInputRef.current) {
      fileInputRef.current.value = ''
    }
  }

  const handleKeyDown = (event: KeyboardEvent) => {
    if (event.key === 'Enter' && !event.shiftKey && !event.nativeEvent.isComposing && !isComposing) {
      event.preventDefault()
      handleSend()
    }
  }

  const openChannelDetail = () => {
    if (!selectedSession) return
    navigate(chatChannelPath(selectedSession.chat_key, DEFAULT_CHAT_CHANNEL_DETAIL_TAB))
  }

  const renderSessionList = () => (
    <Box
      sx={{
        height: '100%',
        minWidth: 0,
        minHeight: 0,
        display: 'flex',
        flexDirection: 'column',
        overflow: 'hidden',
      }}
    >
      <Box sx={{ p: { xs: 1.25, sm: 1.5 }, flexShrink: 0, minWidth: 0, bgcolor: 'background.paper' }}>
        <Stack spacing={1.5}>
          <Stack direction="row" spacing={1} alignItems="center">
            <SearchField
              fullWidth
              value={search}
              placeholder={t('sessions.searchPlaceholder')}
              onChange={setSearch}
              onClear={() => setSearch('')}
              clearAriaLabel={t('sessions.clearSearch')}
            />
            <Tooltip title={t('actions.refresh')}>
              <span>
                <IconActionButton
                  tone="subtle"
                  onClick={() => {
                    void adapterStatusQuery.refetch()
                    void sessionsQuery.refetch()
                  }}
                  disabled={adapterStatusQuery.isFetching || sessionsQuery.isFetching}
                  aria-label={t('actions.refresh')}
                >
                  <RefreshIcon fontSize="small" />
                </IconActionButton>
              </span>
            </Tooltip>
          </Stack>
          <ActionButton
            tone="primary"
            fullWidth
            startIcon={<AddIcon />}
            onClick={() => createSessionMutation.mutate()}
            disabled={!adapterReady || createSessionMutation.isPending}
          >
            {t('actions.createSession')}
          </ActionButton>
        </Stack>
      </Box>
      <Divider />
      <Box sx={{ flex: 1, minHeight: 0, overflowY: 'auto', overflowX: 'hidden', bgcolor: 'background.paper', p: 1 }}>
        {sessionsQuery.isLoading ? (
          <Box sx={{ height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            <CircularProgress size={24} />
          </Box>
        ) : sessions.length === 0 ? (
          <Box sx={{ height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center', px: 2 }}>
            <Typography variant="body2" color="text.secondary" textAlign="center">
              {t('sessions.empty')}
            </Typography>
          </Box>
        ) : (
          <Stack spacing={0.75}>
            {sessions.map(session => {
              const selected = session.chat_key === selectedChatKey
              return (
                <Box
                  key={session.chat_key}
                  role="button"
                  tabIndex={0}
                  onClick={() => handleSelectSession(session.chat_key)}
                  onKeyDown={event => {
                    if (event.key === 'Enter' || event.key === ' ') {
                      event.preventDefault()
                      handleSelectSession(session.chat_key)
                    }
                  }}
                  sx={{
                    p: 1.25,
                    borderRadius: 1,
                    cursor: 'pointer',
                    bgcolor: selected ? 'action.selected' : 'transparent',
                    border: '1px solid',
                    borderColor: selected ? 'primary.main' : 'divider',
                    transition: theme.transitions.create(['background-color', 'border-color']),
                    '&:hover': {
                      bgcolor: selected ? 'action.selected' : 'action.hover',
                    },
                  }}
                >
                  <Stack spacing={0.75}>
                    <Stack direction="row" spacing={1} alignItems="center" minWidth={0}>
                      <ChatIcon sx={{ fontSize: 18, color: selected ? 'primary.main' : 'text.secondary', flexShrink: 0 }} />
                      <Typography variant="body2" fontWeight={600} noWrap title={getWebSessionDisplayName(session)}>
                        {getWebSessionDisplayName(session)}
                      </Typography>
                      <Box sx={{ flex: 1 }} />
                      <Tooltip title={t('actions.editSession')}>
                        <span>
                          <IconActionButton
                            size="small"
                            tone="subtle"
                            onClick={event => {
                              event.stopPropagation()
                              openEditSession(session)
                            }}
                            aria-label={t('actions.editSession')}
                            sx={{ width: 28, height: 28 }}
                          >
                            <EditIcon sx={{ fontSize: 16 }} />
                          </IconActionButton>
                        </span>
                      </Tooltip>
                      <Tooltip title={t('actions.deleteSession')}>
                        <span>
                          <IconActionButton
                            size="small"
                            tone="danger"
                            onClick={event => {
                              event.stopPropagation()
                              setDeletingSession(session)
                            }}
                            aria-label={t('actions.deleteSession')}
                            sx={{ width: 28, height: 28 }}
                          >
                            <DeleteIcon sx={{ fontSize: 16 }} />
                          </IconActionButton>
                        </span>
                      </Tooltip>
                    </Stack>
                    <Stack direction="row" spacing={0.75} alignItems="center">
                      <Chip
                        size="small"
                        color={statusColor(session.status)}
                        label={t(`status.${session.status}`)}
                        sx={{ height: 22, '& .MuiChip-label': { px: 0.75 } }}
                      />
                      <Typography variant="caption" color="text.secondary" noWrap>
                        {t('sessions.messageCount', { count: session.message_count })}
                      </Typography>
                    </Stack>
                  </Stack>
                </Box>
              )
            })}
          </Stack>
        )}
      </Box>
    </Box>
  )

  const adapterUnavailable = adapterStatusQuery.data && adapterStatusQuery.data.status !== 'enabled'
  const adapterStatusErrorMessage = adapterStatusQuery.error instanceof Error
    ? adapterStatusQuery.error.message
    : String(adapterStatusQuery.error ?? '')

  return (
    <Box
      className="h-full flex flex-col gap-2 overflow-hidden p-2 box-border"
      sx={{ minWidth: 0, minHeight: 0 }}
    >
      <Box sx={{ ...CARD_VARIANTS.default.styles, px: { xs: 1.5, md: 2 }, py: 1.5, flexShrink: 0 }}>
        <Stack direction="row" alignItems="center" justifyContent="space-between" spacing={1.5}>
          <Box sx={{ minWidth: 0 }}>
            <Typography variant="h5" fontWeight={700} noWrap>
              {t('title')}
            </Typography>
            <Typography variant="body2" color="text.secondary" noWrap={!isSmall}>
              {t('subtitle')}
            </Typography>
          </Box>
          <Stack direction="row" spacing={1} alignItems="center" flexShrink={0}>
            {isMobile && (
              <Tooltip title={t('actions.sessions')}>
                <IconActionButton
                  tone="subtle"
                  onClick={() => setDrawerOpen(true)}
                  aria-label={t('actions.sessions')}
                >
                  <ViewSidebarIcon fontSize="small" />
                </IconActionButton>
              </Tooltip>
            )}
            <ActionButton
              tone="secondary"
              startIcon={<TuneIcon />}
              onClick={() => navigate('/adapters/web')}
            >
              {t('actions.adapterSettings')}
            </ActionButton>
          </Stack>
        </Stack>
      </Box>

      <Box
        sx={{
          flex: 1,
          minWidth: 0,
          minHeight: 0,
          display: 'flex',
          flexDirection: isMobile ? 'column' : 'row-reverse',
          gap: 1,
          overflow: 'hidden',
        }}
      >
        {!isMobile && (
          <Box
            sx={{
              ...CARD_VARIANTS.default.styles,
              width: 360,
              height: '100%',
              flexShrink: 0,
              display: 'flex',
              flexDirection: 'column',
              minHeight: 0,
              overflow: 'hidden',
            }}
          >
            {renderSessionList()}
          </Box>
        )}

        <Box
          sx={{
            ...CARD_VARIANTS.default.styles,
            flex: 1,
            minWidth: 0,
            minHeight: 0,
            display: 'flex',
            flexDirection: 'column',
            overflow: 'hidden',
            p: 0,
          }}
        >
          {adapterStatusQuery.isLoading ? (
            <Box sx={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
              <CircularProgress />
            </Box>
          ) : adapterStatusQuery.isError ? (
            <Box sx={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', p: 2 }}>
              <Stack spacing={2} alignItems="center" textAlign="center" sx={{ maxWidth: 520 }}>
                <Alert severity="error" sx={{ width: '100%' }}>
                  {adapterStatusErrorMessage || t('adapterUnavailable.description')}
                </Alert>
                <ActionButton tone="primary" startIcon={<RefreshIcon />} onClick={() => void adapterStatusQuery.refetch()}>
                  {t('actions.refresh')}
                </ActionButton>
              </Stack>
            </Box>
          ) : adapterUnavailable ? (
            <Box sx={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', p: 2 }}>
              <Stack spacing={2} alignItems="center" textAlign="center" sx={{ maxWidth: 520 }}>
                <Chip label={t(`adapterStatus.${adapterStatusQuery.data.status}`)} color="warning" />
                <Typography variant="h6">{t('adapterUnavailable.title')}</Typography>
                <Typography variant="body2" color="text.secondary">
                  {adapterStatusQuery.data.error_message || t('adapterUnavailable.description')}
                </Typography>
                <ActionButton tone="primary" startIcon={<TuneIcon />} onClick={() => navigate('/adapters/web')}>
                  {t('actions.adapterSettings')}
                </ActionButton>
              </Stack>
            </Box>
          ) : selectedSession ? (
            <>
              <Box
                sx={{
                  flexShrink: 0,
                  px: { xs: 1.5, md: 2 },
                  py: 1,
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  gap: 1,
                  borderBottom: `1px solid ${theme.palette.divider}`,
                  bgcolor: 'background.paper',
                }}
              >
                <Box sx={{ minWidth: 0 }}>
                  <Typography variant="subtitle1" fontWeight={700} noWrap>
                    {getWebSessionDisplayName(selectedSession)}
                  </Typography>
                  <Typography variant="caption" color="text.secondary" noWrap title={selectedSession.chat_key}>
                    {selectedSession.chat_key}
                  </Typography>
                </Box>
                <Stack direction="row" spacing={1} alignItems="center" flexShrink={0}>
                  <Chip size="small" color={statusColor(selectedSession.status)} label={t(`status.${selectedSession.status}`)} />
                  <Tooltip title={t('actions.openChannelDetail')}>
                    <IconActionButton
                      tone="subtle"
                      onClick={openChannelDetail}
                      aria-label={t('actions.openChannelDetail')}
                    >
                      <OpenInNewIcon fontSize="small" />
                    </IconActionButton>
                  </Tooltip>
                </Stack>
              </Box>
              <Box sx={{ flex: 1, minHeight: 0 }}>
                <MessageHistory chatKey={selectedSession.chat_key} canSend={false} aiAlwaysIncludeMsgId webUserRight />
              </Box>
              <Box
                sx={{
                  flexShrink: 0,
                  px: { xs: 1, md: 1.5 },
                  py: 1,
                  borderTop: `1px solid ${theme.palette.divider}`,
                  bgcolor: 'background.paper',
                }}
              >
                {selectedSession.status === 'disabled' && (
                  <Typography variant="caption" color="warning.main" sx={{ display: 'block', mb: 0.75 }}>
                    {t('composer.disabledHint')}
                  </Typography>
                )}
                {selectedFile && (
                  <Chip
                    icon={<AttachFileIcon />}
                    label={selectedFile.name}
                    onDelete={clearSelectedFile}
                    deleteIcon={<CloseIcon />}
                    sx={{ mb: 0.75, maxWidth: '100%', '& .MuiChip-label': { overflow: 'hidden', textOverflow: 'ellipsis' } }}
                  />
                )}
                <Stack direction="row" spacing={1} alignItems="flex-end">
                  <input
                    ref={fileInputRef}
                    type="file"
                    hidden
                    onChange={handleFileChange}
                  />
                  <Tooltip title={t('actions.attachFile')}>
                    <span>
                      <IconActionButton
                        tone="subtle"
                        onClick={() => fileInputRef.current?.click()}
                        disabled={composerDisabled || sendMessageMutation.isPending}
                        aria-label={t('actions.attachFile')}
                        sx={{ width: 42, height: 42 }}
                      >
                        <AttachFileIcon fontSize="small" />
                      </IconActionButton>
                    </span>
                  </Tooltip>
                  <TextField
                    inputRef={inputRef}
                    fullWidth
                    multiline
                    minRows={1}
                    maxRows={4}
                    value={inputValue}
                    placeholder={t('composer.placeholder')}
                    onChange={event => setInputValue(event.target.value)}
                    onKeyDown={handleKeyDown}
                    onCompositionStart={() => setIsComposing(true)}
                    onCompositionEnd={() => setIsComposing(false)}
                    disabled={composerDisabled || sendMessageMutation.isPending}
                    inputProps={{ maxLength: messageMaxLength }}
                  />
                  <Tooltip title={t('actions.send')}>
                    <span>
                      <IconActionButton
                        tone="primary"
                        onClick={handleSend}
                        disabled={composerDisabled || (!inputValue.trim() && !selectedFile) || sendMessageMutation.isPending}
                        aria-label={t('actions.send')}
                        sx={{ width: 42, height: 42 }}
                      >
                        {sendMessageMutation.isPending ? <CircularProgress size={20} /> : <SendIcon fontSize="small" />}
                      </IconActionButton>
                    </span>
                  </Tooltip>
                </Stack>
              </Box>
            </>
          ) : (
            <Box sx={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', p: 2 }}>
              <Stack spacing={2} alignItems="center" textAlign="center">
                <ChatIcon sx={{ fontSize: 42, color: 'text.disabled' }} />
                <Typography color="text.secondary">{t('sessions.empty')}</Typography>
                <ActionButton
                  tone="primary"
                  startIcon={<AddIcon />}
                  onClick={() => createSessionMutation.mutate()}
                  disabled={!adapterReady || createSessionMutation.isPending}
                >
                  {t('actions.createSession')}
                </ActionButton>
              </Stack>
            </Box>
          )}
        </Box>
      </Box>

      <Drawer
        anchor="left"
        open={drawerOpen}
        onClose={() => setDrawerOpen(false)}
        PaperProps={{
          sx: {
            width: isSmall ? 'min(88vw, 360px)' : 360,
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
        {renderSessionList()}
      </Drawer>

      <Dialog open={Boolean(editingSession)} onClose={() => setEditingSession(null)} fullWidth maxWidth="xs">
        <DialogTitle>{t('dialogs.editTitle')}</DialogTitle>
        <DialogContent>
          <TextField
            autoFocus
            fullWidth
            margin="dense"
            value={editingName}
            label={t('dialogs.sessionName')}
            inputProps={{ maxLength: 64 }}
            onChange={event => setEditingName(event.target.value)}
            onKeyDown={event => {
              if (event.key === 'Enter') {
                event.preventDefault()
                handleUpdateSession()
              }
            }}
          />
        </DialogContent>
        <DialogActions>
          <ActionButton tone="secondary" onClick={() => setEditingSession(null)}>
            {t('actions.cancel')}
          </ActionButton>
          <ActionButton tone="primary" onClick={handleUpdateSession} disabled={updateSessionMutation.isPending}>
            {updateSessionMutation.isPending ? <CircularProgress size={18} /> : t('actions.save')}
          </ActionButton>
        </DialogActions>
      </Dialog>

      <Dialog open={Boolean(deletingSession)} onClose={() => setDeletingSession(null)} fullWidth maxWidth="xs">
        <DialogTitle>{t('dialogs.deleteTitle')}</DialogTitle>
        <DialogContent>
          <Typography variant="body2" color="text.secondary">
            {t('dialogs.deleteContent', { name: deletingSession ? getWebSessionDisplayName(deletingSession) : '' })}
          </Typography>
        </DialogContent>
        <DialogActions>
          <ActionButton tone="secondary" onClick={() => setDeletingSession(null)}>
            {t('actions.cancel')}
          </ActionButton>
          <ActionButton tone="danger" onClick={handleDeleteSession} disabled={deleteSessionMutation.isPending}>
            {deleteSessionMutation.isPending ? <CircularProgress size={18} /> : t('actions.deleteSession')}
          </ActionButton>
        </DialogActions>
      </Dialog>
    </Box>
  )
}
