import {
  Box,
  Chip,
  Typography,
} from '@mui/material'
import CloseIcon from '@mui/icons-material/Close'
import GroupIcon from '@mui/icons-material/Group'
import PersonIcon from '@mui/icons-material/Person'
import type { ChatChannel } from '../../../../services/api/chat-channel'
import { useTranslation } from 'react-i18next'
import IconActionButton from '../../../../components/common/IconActionButton'

interface SelectedChannelSummaryProps {
  channels: ChatChannel[]
  onRemove: (chatKey: string) => void
  onClear: () => void
}

export default function SelectedChannelSummary({
  channels,
  onRemove,
  onClear,
}: SelectedChannelSummaryProps) {
  const { t } = useTranslation('chat-announcement')

  return (
    <Box
      sx={{
        display: 'flex',
        flexDirection: 'column',
        gap: 1,
        border: theme => `1px solid ${theme.palette.divider}`,
        borderRadius: 2,
        px: 1.5,
        py: 1.25,
        bgcolor: theme => theme.palette.action.hover,
      }}
    >
      <Box
        sx={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          gap: 1,
        }}
      >
        <Typography variant="subtitle2" sx={{ fontWeight: 700 }}>
          {t('summary.title')}
        </Typography>
        <Typography variant="caption" color="text.secondary">
          {t('summary.count', { count: channels.length })}
        </Typography>
      </Box>

      {channels.length === 0 ? (
        <Box
          sx={{
            py: 1,
            borderRadius: 1.5,
          }}
        >
          <Typography variant="body2" color="text.secondary">
            {t('summary.empty')}
          </Typography>
        </Box>
      ) : (
        <>
          <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.75, maxHeight: 120, overflowY: 'auto' }}>
            {channels.map(channel => (
              <Chip
                key={channel.chat_key}
                icon={channel.chat_type === 'group' ? <GroupIcon /> : <PersonIcon />}
                label={channel.channel_name || channel.chat_key}
                onDelete={() => onRemove(channel.chat_key)}
                deleteIcon={<CloseIcon />}
                variant="outlined"
              />
            ))}
          </Box>

          <Box sx={{ display: 'flex', justifyContent: 'flex-end' }}>
            <IconActionButton size="small" onClick={onClear} aria-label={t('summary.clear')}>
              <CloseIcon fontSize="small" />
            </IconActionButton>
          </Box>
        </>
      )}
    </Box>
  )
}
