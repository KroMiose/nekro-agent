import { useState } from 'react'
import { Chip } from '@mui/material'
import {
  Face as FaceIcon,
  Delete as DeleteIcon,
  OpenInNew as OpenInNewIcon,
  Edit as EditIcon,
} from '@mui/icons-material'
import { UserPreset } from '../../../services/api/cloud/presets_market'
import ActionButton from '../../common/ActionButton'
import ProfileResourceCard from './ProfileResourceCard'

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
    <ProfileResourceCard
      media={
        preset.avatar && !avatarError ? (
          <img
            src={preset.avatar}
            alt={`${preset.name} 头像`}
            onError={() => setAvatarError(true)}
            style={{ width: '100%', height: '100%', objectFit: 'cover' }}
          />
        ) : (
          <FaceIcon
            sx={{
              fontSize: 28,
              opacity: 0.7,
              color: 'secondary.main',
            }}
          />
        )
      }
      title={preset.title || preset.name}
      subtitle={preset.name}
      meta={
        <Chip
          label={t('cloud:profile.preset')}
          size="small"
          color="secondary"
          sx={{ height: 24, fontSize: '0.75rem' }}
        />
      }
      actions={
        <>
          <ActionButton size="small" variant="text" startIcon={<OpenInNewIcon />} onClick={onViewDetail}>
            {t('cloud:profile.viewDetail')}
          </ActionButton>
          <ActionButton size="small" variant="text" startIcon={<EditIcon />} onClick={onEdit}>
            {t('cloud:pluginsMarket.edit')}
          </ActionButton>
        </>
      }
      trailingAction={
        <ActionButton
          size="small"
          variant="text"
          color="error"
          startIcon={<DeleteIcon />}
          onClick={onUnpublish}
        >
          {t('cloud:pluginsMarket.delist')}
        </ActionButton>
      }
    />
  )
}
