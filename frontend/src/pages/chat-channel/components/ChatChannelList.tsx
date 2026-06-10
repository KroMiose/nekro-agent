import {
  List,
  ListItem,
  ListItemButton,
  ListItemIcon,
  ListItemText,
  Typography,
  Skeleton,
  Stack,
  Box,
} from '@mui/material'
import { Group as GroupIcon, Person as PersonIcon, Circle as CircleIcon } from '@mui/icons-material'
import { getChannelDisplayName, type ChatChannel } from '../../../services/api/chat-channel'
import { useTranslation } from 'react-i18next'
import { formatLastActiveTimeFromInput } from '../../../utils/time'

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
  const { t } = useTranslation('chat-channel')
  if (isLoading) {
    return (
      <List disablePadding sx={{ width: '100%', minWidth: 0 }}>
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
        <Typography color="textSecondary">{t('list.empty')}</Typography>
      </Box>
    )
  }

  return (
    <List disablePadding sx={{ width: '100%', minWidth: 0, overflowX: 'hidden' }}>
      {channels.map(channel => (
        <ListItem key={channel.chat_key} disablePadding divider sx={{ width: '100%', minWidth: 0 }}>
          <ListItemButton
            selected={channel.chat_key === selectedChatKey}
            onClick={() => onSelectChannel(channel.chat_key)}
            sx={{
              width: '100%',
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
            <Box className="min-w-0 flex-1 overflow-hidden">
              <Stack direction="row" spacing={1} alignItems="center" className="min-w-0">
                <Typography variant="body2" className="font-medium truncate flex-1">
                  {getChannelDisplayName(channel)}
                </Typography>
                <CircleIcon
                  sx={{
                    fontSize: 8,
                    color: channel.status === 'active'
                      ? 'success.main'
                      : channel.status === 'observe'
                        ? 'warning.main'
                        : 'text.disabled',
                  }}
                  className="flex-shrink-0"
                />
              </Stack>
              <Typography
                variant="caption"
                color="textSecondary"
                sx={{
                  lineHeight: 1.35,
                  display: 'block',
                  minWidth: 0,
                  overflowWrap: 'anywhere',
                  wordBreak: 'break-word',
                }}
              >
                {channel.chat_key}
              </Typography>
              <Stack direction="row" spacing={1} alignItems="center" justifyContent="space-between" className="min-w-0">
                <Typography variant="caption" color="textSecondary" sx={{ lineHeight: 1.2 }}>
                  {t('list.messageCount', { count: channel.message_count })}
                </Typography>
                <Typography variant="caption" color="textSecondary" sx={{ lineHeight: 1.2 }} className="truncate">
                  {channel.last_message_time
                    ? formatLastActiveTimeFromInput(channel.last_message_time)
                    : t('list.noActiveRecord')}
                </Typography>
              </Stack>
            </Box>
          </ListItemButton>
        </ListItem>
      ))}
    </List>
  )
}
