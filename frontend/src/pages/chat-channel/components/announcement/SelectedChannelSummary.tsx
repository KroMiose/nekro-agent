import {
  Box,
  Chip,
  IconButton,
  Typography,
} from '@mui/material'
import CloseIcon from '@mui/icons-material/Close'
import GroupIcon from '@mui/icons-material/Group'
import PersonIcon from '@mui/icons-material/Person'
import type { ChatChannel } from '../../../../services/api/chat-channel'
import { useTranslation } from 'react-i18next'

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
    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
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
        <Chip
          size="small"
          label={channels.length}
          color="primary"
          variant="outlined"
        />
      </Box>

      {channels.length === 0 ? (
        <Typography variant="body2" color="text.secondary">
          {t('summary.empty')}
        </Typography>
      ) : (
        <>
          <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.75, maxHeight: 180, overflowY: 'auto' }}>
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
            <IconButton size="small" onClick={onClear} aria-label={t('summary.clear')}>
              <CloseIcon fontSize="small" />
            </IconButton>
          </Box>
        </>
      )}
    </Box>
  )
}
