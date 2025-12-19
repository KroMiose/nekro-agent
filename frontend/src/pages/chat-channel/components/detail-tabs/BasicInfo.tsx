import React, { useState, useEffect } from 'react'
import {
  Box,
  Typography,
  Stack,
  Paper,
  Button,
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
} from '@mui/icons-material'
import { ChatChannelDetail, chatChannelApi } from '../../../../services/api/chat-channel'
import { Preset, presetsApi } from '../../../../services/api/presets'
import { useSnackbar } from 'notistack'
import { useQueryClient } from '@tanstack/react-query'
import { useTranslation } from 'react-i18next'

interface BasicInfoProps {
  channel: ChatChannelDetail
}

export default function BasicInfo({ channel }: BasicInfoProps) {
  const [presetDialogOpen, setPresetDialogOpen] = useState(false)
  const [presets, setPresets] = useState<Preset[]>([])
  const [loading, setLoading] = useState(false)
  const [search, setSearch] = useState('')
  const [currentPreset, setCurrentPreset] = useState<Preset | null>(null)
  const { enqueueSnackbar } = useSnackbar()
  const queryClient = useQueryClient()
  const { t } = useTranslation('chat-channel')

  // 获取当前聊天频道的人设信息
  useEffect(() => {
    const fetchCurrentPreset = async () => {
      if (channel.preset_id) {
        try {
          setLoading(true)
          const preset = await presetsApi.getDetail(channel.preset_id)
          setCurrentPreset(preset)
        } catch (error) {
          console.error('获取人设详情失败', error)
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
    } catch (error) {
      console.error('获取人设列表失败', error)
      enqueueSnackbar(t('basicInfo.fetchPresetsFailed'), { variant: 'error' })
    } finally {
      setLoading(false)
    }
  }

  // 搜索人设
  const handleSearch = async () => {
    await loadPresets()
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
    } catch (error) {
      console.error('设置人设失败', error)
      enqueueSnackbar(t('basicInfo.setPresetFailed'), { variant: 'error' })
    } finally {
      setLoading(false)
    }
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
            <Button
              size="small"
              variant="outlined"
              onClick={handleOpenPresetDialog}
              disabled={loading}
            >
              {t('basicInfo.selectPreset')}
            </Button>
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
      </Stack>

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
                    <Button size="small" onClick={handleSearch} disabled={loading}>
                      {t('basicInfo.search')}
                    </Button>
                  </InputAdornment>
                ),
              }}
            />
          </Box>

          <Box className="mb-3">
            <Button
              fullWidth
              variant="outlined"
              onClick={() => handleSelectPreset(null)}
              disabled={loading}
            >
              {t('basicInfo.useDefault')}
            </Button>
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
          <Button onClick={() => setPresetDialogOpen(false)}>{t('basicInfo.cancel')}</Button>
        </DialogActions>
      </Dialog>
    </Box>
  )
}
