import {
  Box,
  Card,
  Checkbox,
  Chip,
  Skeleton,
  Typography,
  useTheme,
} from '@mui/material'
import { alpha } from '@mui/material/styles'
import GroupIcon from '@mui/icons-material/Group'
import PersonIcon from '@mui/icons-material/Person'
import ForumIcon from '@mui/icons-material/Forum'
import type { ChatChannel } from '../../../../services/api/chat-channel'
import { CARD_VARIANTS } from '../../../../theme/variants'
import { useTranslation } from 'react-i18next'

interface ChannelSelectorListProps {
  channels: ChatChannel[]
  selectedChatKeys: Set<string>
  loading: boolean
  onToggle: (channel: ChatChannel) => void
}

const getStatusColor = (status: ChatChannel['status']) => {
  if (status === 'active') return 'success'
  if (status === 'observe') return 'warning'
  return 'default'
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
    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
      {channels.map(channel => {
        const selected = selectedChatKeys.has(channel.chat_key)
        const isGroup = channel.chat_type === 'group'
        const Icon = isGroup ? GroupIcon : PersonIcon

        return (
          <Card
            key={channel.chat_key}
            onClick={() => onToggle(channel)}
            sx={{
              ...CARD_VARIANTS.default.styles,
              p: 1.25,
              cursor: 'pointer',
              borderColor: selected
                ? alpha(theme.palette.primary.main, 0.48)
                : undefined,
              boxShadow: selected
                ? `0 0 0 1px ${alpha(theme.palette.primary.main, 0.18)}`
                : undefined,
              background: selected
                ? alpha(theme.palette.primary.main, 0.08)
                : undefined,
            }}
          >
            <Box sx={{ display: 'flex', gap: 1.25, alignItems: 'flex-start' }}>
              <Checkbox
                checked={selected}
                tabIndex={-1}
                disableRipple
                sx={{ mt: -0.5, ml: -0.5, pointerEvents: 'none' }}
              />

              <Box
                sx={{
                  width: 40,
                  height: 40,
                  borderRadius: '12px',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  color: isGroup ? 'primary.main' : 'info.main',
                  bgcolor: isGroup
                    ? alpha(theme.palette.primary.main, 0.12)
                    : alpha(theme.palette.info.main, 0.12),
                  flexShrink: 0,
                }}
              >
                <Icon fontSize="small" />
              </Box>

              <Box sx={{ minWidth: 0, flex: 1 }}>
                <Box
                  sx={{
                    display: 'flex',
                    gap: 0.75,
                    alignItems: 'center',
                    flexWrap: 'wrap',
                    mb: 0.75,
                  }}
                >
                  <Typography variant="body2" sx={{ fontWeight: 700 }}>
                    {channel.channel_name || channel.chat_key}
                  </Typography>
                  <Chip
                    size="small"
                    label={isGroup ? t('filters.group') : t('filters.private')}
                    color={isGroup ? 'primary' : 'info'}
                    variant="outlined"
                  />
                  <Chip
                    size="small"
                    label={
                      channel.status === 'active'
                        ? t('filters.active')
                        : channel.status === 'observe'
                          ? t('filters.observe')
                          : t('filters.inactive')
                    }
                    color={getStatusColor(channel.status)}
                    variant="outlined"
                  />
                </Box>

                <Typography
                  variant="caption"
                  color="text.secondary"
                  sx={{ display: 'block', fontFamily: 'monospace', mb: 0.5 }}
                >
                  {t('selector.chatKey')}: {channel.chat_key}
                </Typography>

                <Box
                  sx={{
                    display: 'flex',
                    justifyContent: 'space-between',
                    gap: 1,
                    flexWrap: 'wrap',
                  }}
                >
                  <Typography variant="caption" color="text.secondary">
                    {t('selector.messageCount', { count: channel.message_count })}
                  </Typography>
                  <Typography variant="caption" color="text.secondary">
                    {channel.last_message_time || t('selector.noActivity')}
                  </Typography>
                </Box>
              </Box>
            </Box>
          </Card>
        )
      })}
    </Box>
  )
}
