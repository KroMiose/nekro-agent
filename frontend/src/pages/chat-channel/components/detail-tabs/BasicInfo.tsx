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
  
  // 获取当前会话的人设信息
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
      enqueueSnackbar('获取人设列表失败', { variant: 'error' })
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
      enqueueSnackbar(`已${preset ? '设置' : '清除'}人设: ${preset?.title || '默认人设'}`, {
        variant: 'success',
      })
      setPresetDialogOpen(false)
      
      // 刷新会话详情
      queryClient.invalidateQueries({ queryKey: ['chat-channel-detail', channel.chat_key] })
    } catch (error) {
      console.error('设置人设失败', error)
      enqueueSnackbar('设置人设失败', { variant: 'error' })
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
          <Typography variant="body1">{value}</Typography>
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
          label="当前人设"
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
                <Typography>
                  {currentPreset.title}
                  {currentPreset.is_remote && (
                    <Chip
                      icon={<CloudDownloadIcon sx={{ fontSize: '0.7rem !important' }} />}
                      label="云端"
                      size="small"
                      color="primary"
                      variant="outlined"
                      sx={{ ml: 1, height: 20, fontSize: '0.7rem' }}
                    />
                  )}
                </Typography>
              </Stack>
            ) : (
              '默认人设'
            )
          }
          action={
            <Button
              size="small"
              variant="outlined"
              onClick={handleOpenPresetDialog}
              disabled={loading}
            >
              选择人设
            </Button>
          }
        />
        <InfoItem
          icon={<MessageIcon color="primary" />}
          label="消息数量"
          value={`${channel.message_count} 条消息`}
        />
        <InfoItem
          icon={<PersonIcon color="info" />}
          label="参与用户数"
          value={`${channel.unique_users} 位用户`}
        />
        <InfoItem
          icon={<AccessTimeIcon color="success" />}
          label="对话开始时间"
          value={channel.conversation_start_time}
        />
        <InfoItem
          icon={<UpdateIcon color="warning" />}
          label="最后活跃时间"
          value={channel.last_message_time || '暂无消息'}
        />
      </Stack>
      
      {/* 人设选择对话框 */}
      <Dialog open={presetDialogOpen} onClose={() => setPresetDialogOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>选择人设</DialogTitle>
        <DialogContent>
          <Box className="mb-3 mt-2">
            <TextField
              fullWidth
              size="small"
              placeholder="搜索人设..."
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
                      搜索
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
              使用默认人设(清除当前人设)
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
                              label="云端"
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
              未找到人设
            </Typography>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setPresetDialogOpen(false)}>取消</Button>
        </DialogActions>
      </Dialog>
    </Box>
  )
} 