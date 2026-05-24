import React, { useState, useEffect } from 'react'
import {
  Box,
  Typography,
  Stack,
  Paper,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  List,
  ListItem,
  ListItemText,
  ListItemButton,
  ListItemAvatar,
  Avatar,
  CircularProgress,
  TextField,
  InputAdornment,
  Chip,
  Divider,
} from '@mui/material'
import {
  Message as MessageIcon,
  Person as PersonIcon,
  AccessTime as AccessTimeIcon,
  Update as UpdateIcon,
  Face as FaceIcon,
  Search as SearchIcon,
  CloudDownload as CloudDownloadIcon,
  ContentCopy as ContentCopyIcon,
} from '@mui/icons-material'
import { ChatChannelDetail, chatChannelApi } from '../../../../services/api/chat-channel'
import { Preset, presetsApi } from '../../../../services/api/presets'
import { useSnackbar } from 'notistack'
import { useQueryClient } from '@tanstack/react-query'
import { useTranslation } from 'react-i18next'
import { copyText } from '../../../../utils/clipboard'
import ActionButton from '../../../../components/common/ActionButton'

interface BasicInfoProps {
  channel: ChatChannelDetail
}

export default function BasicInfo({ channel }: BasicInfoProps) {
  const [presetDialogOpen, setPresetDialogOpen] = useState(false)
  const [customNameDialogOpen, setCustomNameDialogOpen] = useState(false)
  const [customName, setCustomName] = useState(channel.custom_channel_name ?? '')
  const [presets, setPresets] = useState<Preset[]>([])
  const [loading, setLoading] = useState(false)
  const [search, setSearch] = useState('')
  const [currentPreset, setCurrentPreset] = useState<Preset | null>(null)
  const { enqueueSnackbar } = useSnackbar()
  const queryClient = useQueryClient()
  const { t } = useTranslation('chat-channel')

  useEffect(() => {
    setCustomName(channel.custom_channel_name ?? '')
  }, [channel.custom_channel_name])

  // 获取当前聊天频道的人设信息
  useEffect(() => {
    const fetchCurrentPreset = async () => {
      if (channel.preset_id) {
        try {
          setLoading(true)
          const preset = await presetsApi.getDetail(channel.preset_id)
          setCurrentPreset(preset)
        } finally {
          setLoading(false)
        }
      } else {
        setCurrentPreset(null)
      }
    }
    fetchCurrentPreset()
  }, [channel.preset_id])

  // 打开人设选择对话框时加载人设列表
  const handleOpenPresetDialog = async () => {
    setPresetDialogOpen(true)
    await loadPresets()
  }

  // 加载人设列表
  const loadPresets = async () => {
    try {
      setLoading(true)
      const response = await presetsApi.getList({
        page: 1,
        page_size: 100,
        search: search || undefined,
      })
      setPresets(response.items)
    } catch (_error) {
      enqueueSnackbar(t('basicInfo.fetchPresetsFailed'), { variant: 'error' })
    } finally {
      setLoading(false)
    }
  }

  // 搜索人设
  const handleSearch = async () => {
    await loadPresets()
  }

  const handleSaveCustomName = async () => {
    try {
      setLoading(true)
      const nextName = customName.trim()
      await chatChannelApi.setCustomChannelName(channel.chat_key, nextName || null)
      enqueueSnackbar(t('basicInfo.saveCustomNameSuccess'), { variant: 'success' })
      setCustomNameDialogOpen(false)
      queryClient.invalidateQueries({ queryKey: ['chat-channel-detail', channel.chat_key] })
      queryClient.invalidateQueries({ queryKey: ['chat-channel-management-list'] })
      queryClient.invalidateQueries({ queryKey: ['channel-directory'] })
    } catch (_error) {
      enqueueSnackbar(t('basicInfo.saveCustomNameFailed'), { variant: 'error' })
    } finally {
      setLoading(false)
    }
  }

  // 选择人设
  const handleSelectPreset = async (preset: Preset | null) => {
    try {
      setLoading(true)
      await chatChannelApi.setPreset(channel.chat_key, preset?.id || null)
      enqueueSnackbar(
        t('basicInfo.setPresetSuccess', {
          action: preset ? t('basicInfo.set') : t('basicInfo.clear'),
          name: preset?.title || t('basicInfo.defaultPreset'),
        }),
        {
          variant: 'success',
        }
      )
      setPresetDialogOpen(false)

      // 刷新聊天频道详情
      queryClient.invalidateQueries({ queryKey: ['chat-channel-detail', channel.chat_key] })
    } catch (_error) {
      enqueueSnackbar(t('basicInfo.setPresetFailed'), { variant: 'error' })
    } finally {
      setLoading(false)
    }
  }

  const handleCopyChannelId = async () => {
    const success = await copyText(channel.chat_key)
    if (success) {
      enqueueSnackbar('频道 ID 已复制到剪贴板', { variant: 'success' })
      return
    }

    enqueueSnackbar('复制失败，请稍后重试', { variant: 'error' })
  }

  const InfoItem = ({
    icon,
    label,
    value,
    action,
  }: {
    icon: React.ReactNode
    label: string
    value: React.ReactNode
    action?: React.ReactNode
  }) => (
    <Paper variant="outlined" className="p-3">
      <Stack direction="row" spacing={2} alignItems="center">
        {icon}
        <Box className="flex-1">
          <Typography variant="body2" color="textSecondary" className="mb-1">
            {label}
          </Typography>
          <Typography variant="body1" component="div">
            {value}
          </Typography>
        </Box>
        {action}
      </Stack>
    </Paper>
  )

  return (
    <Box className="p-4">
      <Stack spacing={2}>
        <InfoItem
          icon={<MessageIcon color="primary" />}
          label={t('basicInfo.displayName')}
          value={
            <Stack spacing={0.5}>
              <Typography component="div">
                {channel.custom_channel_name || channel.channel_name || channel.chat_key}
              </Typography>
              {channel.custom_channel_name && (
                <Typography variant="caption" color="textSecondary" component="div" sx={{ wordBreak: 'break-all' }}>
                  {t('basicInfo.originalName')}: {channel.channel_name || channel.chat_key}
                </Typography>
              )}
            </Stack>
          }
          action={
            <ActionButton
              size="small"
              variant="outlined"
              onClick={() => setCustomNameDialogOpen(true)}
              disabled={loading}
            >
              {t('basicInfo.editCustomName')}
            </ActionButton>
          }
        />
        <InfoItem
          icon={<FaceIcon color="secondary" />}
          label={t('basicInfo.currentPreset')}
          value={
            loading ? (
              <CircularProgress size={16} />
            ) : currentPreset ? (
              <Stack direction="row" spacing={1} alignItems="center">
                <Avatar
                  src={currentPreset.avatar}
                  alt={currentPreset.name}
                  sx={{ width: 24, height: 24, marginRight: 0.5 }}
                />
                <Typography component="div">
                  {currentPreset.title}
                  {currentPreset.is_remote && (
                    <Chip
                      icon={<CloudDownloadIcon sx={{ fontSize: '0.7rem !important' }} />}
                      label={t('basicInfo.cloud')}
                      size="small"
                      color="primary"
                      variant="outlined"
                      sx={{ ml: 1, height: 20, fontSize: '0.7rem' }}
                    />
                  )}
                </Typography>
              </Stack>
            ) : (
              t('basicInfo.defaultPreset')
            )
          }
          action={
            <ActionButton
              size="small"
              variant="outlined"
              onClick={handleOpenPresetDialog}
              disabled={loading}
            >
              {t('basicInfo.selectPreset')}
            </ActionButton>
          }
        />
        <InfoItem
          icon={<MessageIcon color="primary" />}
          label={t('basicInfo.messageCount')}
          value={t('basicInfo.messagesCount', { count: channel.message_count })}
        />
        <InfoItem
          icon={<PersonIcon color="info" />}
          label={t('basicInfo.uniqueUsers')}
          value={t('basicInfo.usersCount', { count: channel.unique_users })}
        />
        <InfoItem
          icon={<AccessTimeIcon color="success" />}
          label={t('basicInfo.startTime')}
          value={channel.conversation_start_time}
        />
        <InfoItem
          icon={<UpdateIcon color="warning" />}
          label={t('basicInfo.lastActiveTime')}
          value={channel.last_message_time || t('basicInfo.noMessages')}
        />
        <InfoItem
          icon={<PersonIcon color="action" />}
          label="频道 ID"
          value={
            <Typography component="div" sx={{ fontFamily: 'monospace', wordBreak: 'break-all' }}>
              {channel.chat_key}
            </Typography>
          }
          action={
            <ActionButton
              size="small"
              variant="outlined"
              startIcon={<ContentCopyIcon />}
              onClick={handleCopyChannelId}
            >
              复制 ID
            </ActionButton>
          }
        />
      </Stack>

      <Dialog
        open={customNameDialogOpen}
        onClose={() => setCustomNameDialogOpen(false)}
        maxWidth="sm"
        fullWidth
      >
        <DialogTitle>{t('basicInfo.editCustomName')}</DialogTitle>
        <DialogContent>
          <Box className="mt-2">
            <TextField
              fullWidth
              size="small"
              label={t('basicInfo.customName')}
              placeholder={channel.channel_name || channel.chat_key}
              value={customName}
              inputProps={{ maxLength: 64 }}
              helperText={t('basicInfo.customNamePlaceholder')}
              onChange={event => setCustomName(event.target.value)}
              onKeyDown={event => event.key === 'Enter' && handleSaveCustomName()}
            />
          </Box>
        </DialogContent>
        <DialogActions>
          <ActionButton tone="secondary" onClick={() => setCustomNameDialogOpen(false)}>
            {t('basicInfo.cancel')}
          </ActionButton>
          <ActionButton onClick={handleSaveCustomName} disabled={loading}>
            {loading ? <CircularProgress size={20} /> : t('basicInfo.save')}
          </ActionButton>
        </DialogActions>
      </Dialog>

      {/* 人设选择对话框 */}
      <Dialog
        open={presetDialogOpen}
        onClose={() => setPresetDialogOpen(false)}
        maxWidth="sm"
        fullWidth
      >
        <DialogTitle>{t('basicInfo.selectPreset')}</DialogTitle>
        <DialogContent>
          <Box className="mb-3 mt-2">
            <TextField
              fullWidth
              size="small"
              placeholder={t('basicInfo.searchPreset')}
              value={search}
              onChange={e => setSearch(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && handleSearch()}
              InputProps={{
                startAdornment: (
                  <InputAdornment position="start">
                    <SearchIcon fontSize="small" />
                  </InputAdornment>
                ),
                endAdornment: (
                  <InputAdornment position="end">
                    <ActionButton size="small" onClick={handleSearch} disabled={loading}>
                      {t('basicInfo.search')}
                    </ActionButton>
                  </InputAdornment>
                ),
              }}
            />
          </Box>

          <Box className="mb-3">
            <ActionButton
              fullWidth
              variant="outlined"
              onClick={() => handleSelectPreset(null)}
              disabled={loading}
            >
              {t('basicInfo.useDefault')}
            </ActionButton>
          </Box>

          <Divider className="mb-2" />

          {loading ? (
            <Box className="flex justify-center p-4">
              <CircularProgress />
            </Box>
          ) : presets.length > 0 ? (
            <List sx={{ maxHeight: '400px', overflow: 'auto' }}>
              {presets.map(preset => (
                <ListItem key={preset.id} disablePadding>
                  <ListItemButton onClick={() => handleSelectPreset(preset)}>
                    <ListItemAvatar>
                      <Avatar src={preset.avatar} alt={preset.name} />
                    </ListItemAvatar>
                    <ListItemText
                      primary={
                        <Stack direction="row" spacing={1} alignItems="center">
                          {preset.title}
                          {preset.is_remote && (
                            <Chip
                              icon={<CloudDownloadIcon sx={{ fontSize: '0.7rem !important' }} />}
                              label={t('basicInfo.cloud')}
                              size="small"
                              color="primary"
                              variant="outlined"
                              sx={{ height: 20, fontSize: '0.7rem' }}
                            />
                          )}
                        </Stack>
                      }
                      secondary={preset.description || preset.name}
                    />
                  </ListItemButton>
                </ListItem>
              ))}
            </List>
          ) : (
            <Typography className="p-4 text-center" color="textSecondary">
              {t('search.noResults')}
            </Typography>
          )}
        </DialogContent>
        <DialogActions>
          <ActionButton onClick={() => setPresetDialogOpen(false)}>{t('basicInfo.cancel')}</ActionButton>
        </DialogActions>
      </Dialog>
    </Box>
  )
}
