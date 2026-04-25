import { useState } from 'react'
import { Avatar, Box, Card, CardActions, CardContent, Chip, Typography } from '@mui/material'
import {
  Face as FaceIcon,
  Star as StarIcon,
  Delete as DeleteIcon,
  OpenInNew as OpenInNewIcon,
  Edit as EditIcon,
} from '@mui/icons-material'
import { UserPreset } from '../../../services/api/cloud/presets_market'
import ActionButton from '../../common/ActionButton'
import { CARD_VARIANTS } from '../../../theme/variants'
import { UI_STYLES } from '../../../theme/themeConfig'

interface UserPresetCardProps {
  preset: UserPreset
  onUnpublish: () => void
  onViewDetail: () => void
  onEdit: () => void
  t: (key: string, options?: Record<string, unknown>) => string
}

export default function UserPresetCard({
  preset,
  onUnpublish,
  onViewDetail,
  onEdit,
  t,
}: UserPresetCardProps) {
  const [avatarError, setAvatarError] = useState(false)

  return (
    <Card
      sx={{
        ...CARD_VARIANTS.default.styles,
        height: '100%',
        display: 'flex',
        flexDirection: 'column',
        overflow: 'hidden',
        transition: 'all 0.2s ease',
        '&:hover': {
          transform: 'translateY(-2px)',
        },
      }}
    >
      <CardContent sx={{ flexGrow: 1, p: 2.5, pb: 1 }}>
        <Box sx={{ display: 'flex', gap: 2.5, mb: 2 }}>
          <Avatar
            src={preset.avatar && !avatarError ? preset.avatar : undefined}
            alt={preset.name}
            variant="rounded"
            sx={{
              width: 100,
              height: 100,
              borderRadius: 2,
              boxShadow: '0 3px 10px rgba(0,0,0,0.1)',
              flexShrink: 0,
            }}
          >
            {avatarError || !preset.avatar ? (
              <FaceIcon sx={{ fontSize: 48, opacity: 0.7 }} />
            ) : null}
          </Avatar>

          {preset.avatar && !avatarError ? (
            <img
              src={preset.avatar}
              alt=""
              onError={() => setAvatarError(true)}
              style={{ display: 'none' }}
            />
          ) : null}

          <Box sx={{ flexGrow: 1, minWidth: 0 }}>
            <Typography
              variant="h6"
              noWrap
              sx={{
                fontWeight: 600,
                fontSize: '1.1rem',
                lineHeight: 1.4,
              }}
            >
              {preset.title || preset.name}
            </Typography>
            <Typography
              variant="body2"
              color="text.secondary"
              noWrap
              sx={{ fontSize: '0.8rem', mb: 1 }}
            >
              {preset.name}
            </Typography>
            {typeof preset.favoriteCount === 'number' && (
              <Chip
                icon={<StarIcon sx={{ fontSize: 14 }} />}
                label={preset.favoriteCount}
                size="small"
                sx={{ height: 24, fontSize: '0.75rem' }}
              />
            )}
          </Box>
        </Box>
      </CardContent>

      <CardActions
        sx={{
          justifyContent: 'space-between',
          p: 1.5,
          bgcolor: UI_STYLES.SELECTED,
          borderTop: '1px solid',
          borderColor: 'divider',
        }}
      >
        <Box sx={{ display: 'flex', gap: 0.5 }}>
          <ActionButton size="small" variant="text" startIcon={<OpenInNewIcon />} onClick={onViewDetail}>
            {t('cloud:profile.viewDetail')}
          </ActionButton>
          <ActionButton size="small" variant="text" startIcon={<EditIcon />} onClick={onEdit}>
            {t('cloud:pluginsMarket.edit')}
          </ActionButton>
        </Box>
        <ActionButton
          size="small"
          tone="danger"
          startIcon={<DeleteIcon />}
          onClick={onUnpublish}
        >
          {t('cloud:pluginsMarket.delist')}
        </ActionButton>
      </CardActions>
    </Card>
  )
}
