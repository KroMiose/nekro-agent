import {
  List,
  ListItem,
  ListItemButton,
  ListItemText,
  ListItemIcon,
  Typography,
  Skeleton,
  Stack,
  Box,
} from '@mui/material'
import { Group as GroupIcon, Person as PersonIcon, Circle as CircleIcon } from '@mui/icons-material'
import { ChatChannel } from '../../../services/api/chat-channel'
import { formatLastActiveTime } from '../../../utils/time'

interface ChatChannelListProps {
  channels: ChatChannel[]
  selectedChatKey: string | null
  onSelectChannel: (chatKey: string) => void
  isLoading: boolean
}

export default function ChatChannelList({
  channels,
  selectedChatKey,
  onSelectChannel,
  isLoading,
}: ChatChannelListProps) {
  if (isLoading) {
    return (
      <List>
        {[...Array(5)].map((_, index) => (
          <ListItem key={index} disablePadding divider>
            <ListItemButton>
              <ListItemIcon>
                <Skeleton variant="circular" width={24} height={24} />
              </ListItemIcon>
              <ListItemText
                primary={<Skeleton width="60%" />}
                secondary={<Skeleton width="40%" />}
              />
            </ListItemButton>
          </ListItem>
        ))}
      </List>
    )
  }

  if (channels.length === 0) {
    return (
      <Box className="h-full flex items-center justify-center">
        <Typography color="textSecondary">暂无聊天频道</Typography>
      </Box>
    )
  }

  return (
    <List disablePadding>
      {channels.map(channel => (
        <ListItem key={channel.chat_key} disablePadding divider>
          <ListItemButton
            selected={channel.chat_key === selectedChatKey}
            onClick={() => onSelectChannel(channel.chat_key)}
            sx={{
              minWidth: 0,
              py: 1.5,
              px: 2,
            }}
          >
            <ListItemIcon className="min-w-[32px]">
              {channel.chat_type === 'group' ? (
                <GroupIcon color="primary" fontSize="small" />
              ) : (
                <PersonIcon color="info" fontSize="small" />
              )}
            </ListItemIcon>
            <Box className="min-w-0 flex-1">
              <Stack direction="row" spacing={1} alignItems="center" className="min-w-0">
                <Typography variant="body2" className="font-medium truncate flex-1">
                  {channel.channel_name || channel.chat_key}
                </Typography>
                <CircleIcon
                  sx={{
                    fontSize: 8,
                    color: channel.is_active ? 'success.main' : 'text.disabled',
                  }}
                  className="flex-shrink-0"
                />
              </Stack>
              <Stack spacing={0.5} className="min-w-0">
                <Stack
                  direction="row"
                  spacing={1}
                  alignItems="center"
                  justifyContent="space-between"
                >
                  <Typography variant="caption" color="textSecondary" sx={{ lineHeight: 1.2 }}>
                    {channel.message_count}条消息
                  </Typography>
                  <Typography variant="caption" color="textSecondary" sx={{ lineHeight: 1.2 }}>
                    {channel.last_message_time
                      ? formatLastActiveTime(
                          Math.floor(new Date(channel.last_message_time).getTime() / 1000)
                        )
                      : '暂无活跃记录'}
                  </Typography>
                </Stack>
              </Stack>
            </Box>
          </ListItemButton>
        </ListItem>
      ))}
    </List>
  )
}
