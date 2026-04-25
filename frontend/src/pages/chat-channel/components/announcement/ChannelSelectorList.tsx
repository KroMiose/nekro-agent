import {
  Box,
  Checkbox,
  List,
  ListItem,
  ListItemButton,
  Skeleton,
  Stack,
  Tooltip,
  Typography,
  useTheme,
} from '@mui/material'
import { alpha } from '@mui/material/styles'
import GroupIcon from '@mui/icons-material/Group'
import PersonIcon from '@mui/icons-material/Person'
import ForumIcon from '@mui/icons-material/Forum'
import CircleIcon from '@mui/icons-material/Circle'
import type { ChatChannel } from '../../../../services/api/chat-channel'
import { useTranslation } from 'react-i18next'
import { formatLastActiveTimeFromInput } from '../../../../utils/time'

interface ChannelSelectorListProps {
  channels: ChatChannel[]
  selectedChatKeys: Set<string>
  loading: boolean
  onToggle: (channel: ChatChannel) => void
}

export default function ChannelSelectorList({
  channels,
  selectedChatKeys,
  loading,
  onToggle,
}: ChannelSelectorListProps) {
  const theme = useTheme()
  const { t } = useTranslation('chat-announcement')

  if (loading) {
    return (
      <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
        {Array.from({ length: 6 }).map((_, index) => (
          <Skeleton key={index} variant="rounded" height={94} />
        ))}
      </Box>
    )
  }

  if (channels.length === 0) {
    return (
      <Box
        sx={{
          py: 6,
          px: 2,
          textAlign: 'center',
          color: 'text.secondary',
          borderRadius: 2,
          border: `1px dashed ${theme.palette.divider}`,
        }}
      >
        <ForumIcon sx={{ fontSize: 28, mb: 1, opacity: 0.72 }} />
        <Typography variant="body2">{t('selector.empty')}</Typography>
      </Box>
    )
  }

  return (
    <List
      disablePadding
      sx={{
        border: `1px solid ${theme.palette.divider}`,
        borderRadius: 2,
        overflow: 'hidden',
        bgcolor: alpha(theme.palette.background.paper, 0.36),
      }}
    >
      {channels.map(channel => {
        const selected = selectedChatKeys.has(channel.chat_key)
        const isGroup = channel.chat_type === 'group'
        const Icon = isGroup ? GroupIcon : PersonIcon

        return (
          <ListItem
            key={channel.chat_key}
            disablePadding
            divider
          >
            <ListItemButton
              selected={selected}
              onClick={() => onToggle(channel)}
              sx={{
                minWidth: 0,
                px: 2,
                py: 1.5,
                alignItems: 'flex-start',
                gap: 1.25,
                '&.Mui-selected': {
                  backgroundColor: alpha(theme.palette.primary.main, 0.08),
                },
                '&.Mui-selected:hover': {
                  backgroundColor: alpha(theme.palette.primary.main, 0.12),
                },
              }}
            >
              <Checkbox
                checked={selected}
                tabIndex={-1}
                disableRipple
                sx={{ mt: -0.25, ml: -0.5, pointerEvents: 'none' }}
              />

              <Box
                sx={{
                  width: 36,
                  height: 36,
                  borderRadius: 1.5,
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  color: isGroup ? 'primary.main' : 'info.main',
                  bgcolor: isGroup
                    ? alpha(theme.palette.primary.main, 0.1)
                    : alpha(theme.palette.info.main, 0.1),
                  flexShrink: 0,
                  mt: 0.25,
                }}
              >
                <Icon fontSize="small" />
              </Box>

              <Box sx={{ minWidth: 0, flex: 1 }}>
                <Box
                  sx={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    gap: 1,
                    mb: 0.5,
                  }}
                >
                  <Tooltip title={channel.channel_name || channel.chat_key} placement="top" arrow>
                    <Typography
                      variant="body2"
                      sx={{
                        fontWeight: 700,
                        minWidth: 0,
                        flex: 1,
                      }}
                      noWrap
                    >
                      {channel.channel_name || channel.chat_key}
                    </Typography>
                  </Tooltip>

                  <CircleIcon
                    sx={{
                      fontSize: 8,
                      color: channel.status === 'active'
                        ? 'success.main'
                        : channel.status === 'observe'
                          ? 'warning.main'
                          : 'text.disabled',
                      flexShrink: 0,
                    }}
                  />
                </Box>

                <Tooltip title={`${t('selector.chatKey')}: ${channel.chat_key}`} placement="top" arrow>
                  <Typography
                    variant="caption"
                    color="text.secondary"
                    sx={{
                      display: 'block',
                      fontFamily: 'monospace',
                      mb: 0.5,
                    }}
                    noWrap
                  >
                    {t('selector.chatKey')}: {channel.chat_key}
                  </Typography>
                </Tooltip>

                <Stack
                  direction="row"
                  sx={{
                    justifyContent: 'space-between',
                    gap: 1,
                    alignItems: 'center',
                    minWidth: 0,
                  }}
                >
                  <Stack direction="row" spacing={1} sx={{ minWidth: 0 }}>
                    <Typography variant="caption" color="text.secondary" noWrap>
                      {isGroup ? t('filters.group') : t('filters.private')}
                    </Typography>
                    <Typography variant="caption" color="text.secondary" noWrap>
                      {t('selector.messageCount', { count: channel.message_count })}
                    </Typography>
                  </Stack>
                  <Typography variant="caption" color="text.secondary">
                    {channel.last_message_time
                      ? formatLastActiveTimeFromInput(channel.last_message_time)
                      : t('selector.noActivity')}
                  </Typography>
                </Stack>
              </Box>
            </ListItemButton>
          </ListItem>
        )
      })}
    </List>
  )
}
