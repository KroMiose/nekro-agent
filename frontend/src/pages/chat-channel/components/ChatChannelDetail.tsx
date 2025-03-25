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
  Divider,
  IconButton,
  Tooltip,
} from '@mui/material'
import {
  Group as GroupIcon,
  Person as PersonIcon,
  CheckCircle as CheckCircleIcon,
  Cancel as CancelIcon,
  Refresh as RefreshIcon,
  Circle as CircleIcon,
  Sync as SyncIcon,
} from '@mui/icons-material'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { chatChannelApi } from '../../../services/api/chat-channel'
import BasicInfo from './detail-tabs/BasicInfo'
import MessageHistory from './detail-tabs/MessageHistory'

interface ChatChannelDetailProps {
  chatKey: string
}

export default function ChatChannelDetail({ chatKey }: ChatChannelDetailProps) {
  const [currentTab, setCurrentTab] = useState(0)
  const [resetDialogOpen, setResetDialogOpen] = useState(false)
  const [isRefreshing, setIsRefreshing] = useState(false)
  const queryClient = useQueryClient()

  // 查询会话详情
  const { data: channel, isLoading } = useQuery({
    queryKey: ['chat-channel-detail', chatKey],
    queryFn: () => chatChannelApi.getDetail(chatKey),
  })

  // 激活/停用会话
  const { mutate: toggleActive, isPending: isToggling } = useMutation({
    mutationFn: (isActive: boolean) => chatChannelApi.setActive(chatKey, isActive),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['chat-channel-detail', chatKey] })
      queryClient.invalidateQueries({ queryKey: ['chat-channels'] })
    },
  })

  // 重置会话
  const { mutate: resetChannel, isPending: isResetting } = useMutation({
    mutationFn: () => chatChannelApi.reset(chatKey),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['chat-channel-detail', chatKey] })
      setResetDialogOpen(false)
    },
  })

  // 刷新会话信息
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
      <Box className="h-full flex items-center justify-center">
        <CircularProgress />
      </Box>
    )
  }

  return (
    <Box className="h-full flex flex-col overflow-hidden">
      {/* 头部信息 */}
      <Box className="p-4 flex-shrink-0">
        <Stack direction="row" spacing={2} alignItems="flex-start" className="mb-3">
          {/* 会话类型图标 */}
          {channel.chat_type === 'group' ? (
            <GroupIcon color="primary" sx={{ fontSize: 32 }} />
          ) : (
            <PersonIcon color="info" sx={{ fontSize: 32 }} />
          )}

          {/* 会话名称和标识 */}
          <Box className="flex-1">
            <Stack direction="row" spacing={1} alignItems="center">
              <Typography variant="h6" className="font-medium">
                {channel.channel_name || '未命名会话'}
              </Typography>
              <Tooltip title="刷新会话信息">
                <IconButton
                  size="small"
                  onClick={handleRefresh}
                  disabled={isRefreshing}
                  sx={{ mr: 0.5 }}
                >
                  {isRefreshing ? (
                    <CircularProgress size={16} />
                  ) : (
                    <SyncIcon fontSize="small" />
                  )}
                </IconButton>
              </Tooltip>
              <CircleIcon
                sx={{
                  fontSize: 10,
                  color: channel.is_active ? 'success.main' : 'text.disabled',
                }}
              />
            </Stack>
            <Typography variant="body2" color="textSecondary" sx={{ marginTop: 1 }}>
              {channel.chat_key}
            </Typography>
          </Box>

          {/* 右侧信息 */}
          <Stack spacing={1} alignItems="flex-end">
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
                {isToggling ? <CircularProgress size={16} /> : channel.is_active ? '停用' : '激活'}
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

        <Divider />
      </Box>

      {/* 标签页 */}
      <Box className="flex-shrink-0">
        <Tabs value={currentTab} onChange={handleTabChange} variant="fullWidth">
          <Tab label="基础信息" />
          <Tab label="消息记录" />
        </Tabs>
      </Box>

      <Divider />

      {/* 标签内容 */}
      <Box className="flex-1 overflow-auto">
        {currentTab === 0 && <BasicInfo channel={channel} />}
        {currentTab === 1 && <MessageHistory chatKey={chatKey} />}
      </Box>

      {/* 重置确认对话框 */}
      <Dialog open={resetDialogOpen} onClose={() => setResetDialogOpen(false)}>
        <DialogTitle>确认重置会话？</DialogTitle>
        <DialogContent>
          <Typography>重置会话将清空所有预设状态和效果，此操作不可撤销，是否继续？</Typography>
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
