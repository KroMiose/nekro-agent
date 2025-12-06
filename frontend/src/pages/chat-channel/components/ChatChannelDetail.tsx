import React, { useState } from 'react'
import {
  Box,
  Typography,
  Tabs,
  Tab,
  Stack,
  Chip,
  Button,
  ButtonGroup,
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
} from '@mui/material'
import {
  Group as GroupIcon,
  Person as PersonIcon,
  CheckCircle as CheckCircleIcon,
  Cancel as CancelIcon,
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
import { CARD_VARIANTS } from '../../../theme/variants'
import { useMediaQuery } from '@mui/material'

interface ChatChannelDetailProps {
  chatKey: string
  onBack?: () => void
}

export default function ChatChannelDetail({ chatKey, onBack }: ChatChannelDetailProps) {
  const [currentTab, setCurrentTab] = useState(0)
  const [resetDialogOpen, setResetDialogOpen] = useState(false)
  const [isRefreshing, setIsRefreshing] = useState(false)
  const queryClient = useQueryClient()
  const theme = useTheme()
  const isMobile = useMediaQuery(theme.breakpoints.down('md'))

<<<<<<< HEAD
  // 查询聊天详情
=======
<<<<<<< HEAD
  // 查询聊天详情
=======
<<<<<<< HEAD
  // 查询聊天详情
=======
  // 查询会话详情
>>>>>>> 6cf9d37 (增加PYPI源自定义和代理功能)
>>>>>>> a776096 (增加PYPI源自定义和代理功能)
>>>>>>> e26199f (增加PYPI源自定义和代理功能)
  const { data: channel, isLoading } = useQuery({
    queryKey: ['chat-channel-detail', chatKey],
    queryFn: () => chatChannelApi.getDetail(chatKey),
  })

<<<<<<< HEAD
  // 激活/停用聊天
=======
<<<<<<< HEAD
  // 激活/停用聊天
=======
<<<<<<< HEAD
  // 激活/停用聊天
=======
  // 激活/停用会话
>>>>>>> 6cf9d37 (增加PYPI源自定义和代理功能)
>>>>>>> a776096 (增加PYPI源自定义和代理功能)
>>>>>>> e26199f (增加PYPI源自定义和代理功能)
  const { mutate: toggleActive, isPending: isToggling } = useMutation({
    mutationFn: (isActive: boolean) => chatChannelApi.setActive(chatKey, isActive),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['chat-channel-detail', chatKey] })
      queryClient.invalidateQueries({ queryKey: ['chat-channels'] })
    },
  })

<<<<<<< HEAD
  // 重置聊天
=======
<<<<<<< HEAD
  // 重置聊天
=======
<<<<<<< HEAD
  // 重置聊天
=======
  // 重置会话
>>>>>>> 6cf9d37 (增加PYPI源自定义和代理功能)
>>>>>>> a776096 (增加PYPI源自定义和代理功能)
>>>>>>> e26199f (增加PYPI源自定义和代理功能)
  const { mutate: resetChannel, isPending: isResetting } = useMutation({
    mutationFn: () => chatChannelApi.reset(chatKey),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['chat-channel-detail', chatKey] })
      setResetDialogOpen(false)
    },
  })

<<<<<<< HEAD
  // 刷新聊天信息
=======
<<<<<<< HEAD
  // 刷新聊天信息
=======
<<<<<<< HEAD
  // 刷新聊天信息
=======
  // 刷新会话信息
>>>>>>> 6cf9d37 (增加PYPI源自定义和代理功能)
>>>>>>> a776096 (增加PYPI源自定义和代理功能)
>>>>>>> e26199f (增加PYPI源自定义和代理功能)
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
    setCurrentTab(newValue)
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
          <Stack direction="row" spacing={2} alignItems="flex-start">
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
              <Stack direction="row" spacing={1} alignItems="center">
                <Typography variant="h6" className="font-medium truncate">
<<<<<<< HEAD
                  {channel.channel_name || '未命名聊天'}
                </Typography>
                <Tooltip title="刷新聊天信息">
=======
<<<<<<< HEAD
                  {channel.channel_name || '未命名聊天'}
                </Typography>
                <Tooltip title="刷新聊天信息">
=======
<<<<<<< HEAD
                  {channel.channel_name || '未命名聊天'}
                </Typography>
                <Tooltip title="刷新聊天信息">
=======
                  {channel.channel_name || '未命名会话'}
                </Typography>
                <Tooltip title="刷新会话信息">
>>>>>>> 6cf9d37 (增加PYPI源自定义和代理功能)
>>>>>>> a776096 (增加PYPI源自定义和代理功能)
>>>>>>> e26199f (增加PYPI源自定义和代理功能)
                  <IconButton
                    size="small"
                    onClick={handleRefresh}
                    disabled={isRefreshing}
                    sx={{ mr: 0.5 }}
                  >
                    {isRefreshing ? <CircularProgress size={16} /> : <SyncIcon fontSize="small" />}
                  </IconButton>
                </Tooltip>
                <CircleIcon
                  sx={{
                    fontSize: 10,
                    color: channel.is_active ? 'success.main' : 'text.disabled',
                  }}
                />
              </Stack>
              <Typography
                variant="body2"
                color="textSecondary"
                sx={{ marginTop: 0.5, fontFamily: 'monospace', wordBreak: 'break-all' }}
              >
                {channel.chat_key}
              </Typography>
            </Box>
            <Stack spacing={1} alignItems="flex-end" sx={{ flexShrink: 0 }}>
              <Chip
                size="small"
                icon={channel.chat_type === 'group' ? <GroupIcon /> : <PersonIcon />}
                label={channel.chat_type === 'group' ? '群聊' : '私聊'}
                color={channel.chat_type === 'group' ? 'primary' : 'info'}
                variant="outlined"
              />
              <ButtonGroup variant="outlined" size="small">
                <Button
                  color={channel.is_active ? 'error' : 'success'}
                  onClick={() => toggleActive(!channel.is_active)}
                  disabled={isToggling}
                  startIcon={channel.is_active ? <CancelIcon /> : <CheckCircleIcon />}
                >
                  {isToggling ? (
                    <CircularProgress size={16} />
                  ) : channel.is_active ? (
                    '停用'
                  ) : (
                    '激活'
                  )}
                </Button>
                <Button
                  color="warning"
                  onClick={() => setResetDialogOpen(true)}
                  startIcon={<RefreshIcon />}
                >
                  重置
                </Button>
              </ButtonGroup>
            </Stack>
          </Stack>
        </CardContent>
      </Card>

      {/* 标签页 */}
      <Card sx={CARD_VARIANTS.default.styles}>
        <Tabs
          value={currentTab}
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
          <Tab label="基础信息" />
          <Tab label="覆盖配置" />
          <Tab label="消息记录" />
        </Tabs>
      </Card>

      {/* 标签内容 */}
      <Box className="flex-1 overflow-hidden">
        {currentTab === 0 && (
          <Card sx={{ ...CARD_VARIANTS.default.styles, height: '100%', overflow: 'auto' }}>
            <BasicInfo channel={channel} />
          </Card>
        )}
        {currentTab === 1 && (
          <Card sx={{ ...CARD_VARIANTS.default.styles, height: '100%', overflow: 'auto' }}>
            <OverrideSettings chatKey={chatKey} />
          </Card>
        )}
        {currentTab === 2 && (
          <Card sx={{ ...CARD_VARIANTS.default.styles, height: '100%', p: 0, overflow: 'hidden' }}>
            <MessageHistory chatKey={chatKey} />
          </Card>
        )}
      </Box>

      {/* 重置确认对话框 */}
      <Dialog open={resetDialogOpen} onClose={() => setResetDialogOpen(false)}>
<<<<<<< HEAD
        <DialogTitle>确认重置聊天？</DialogTitle>
        <DialogContent>
          <Typography>重置聊天将清空所有预设状态和效果，此操作不可撤销，是否继续？</Typography>
=======
<<<<<<< HEAD
        <DialogTitle>确认重置聊天？</DialogTitle>
        <DialogContent>
          <Typography>重置聊天将清空所有预设状态和效果，此操作不可撤销，是否继续？</Typography>
=======
<<<<<<< HEAD
        <DialogTitle>确认重置聊天？</DialogTitle>
        <DialogContent>
          <Typography>重置聊天将清空所有预设状态和效果，此操作不可撤销，是否继续？</Typography>
=======
        <DialogTitle>确认重置会话？</DialogTitle>
        <DialogContent>
          <Typography>重置会话将清空所有预设状态和效果，此操作不可撤销，是否继续？</Typography>
>>>>>>> 6cf9d37 (增加PYPI源自定义和代理功能)
>>>>>>> a776096 (增加PYPI源自定义和代理功能)
>>>>>>> e26199f (增加PYPI源自定义和代理功能)
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setResetDialogOpen(false)}>取消</Button>
          <Button onClick={() => resetChannel()} color="warning" disabled={isResetting}>
            {isResetting ? <CircularProgress size={20} /> : '确认重置'}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  )
}
