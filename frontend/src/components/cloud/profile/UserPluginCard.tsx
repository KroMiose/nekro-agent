import { useState } from 'react'
import { Chip } from '@mui/material'
import { Extension as ExtensionIcon, Delete as DeleteIcon, Edit as EditIcon } from '@mui/icons-material'
import { UserPlugin } from '../../../services/api/cloud/plugins_market'
import ActionButton from '../../common/ActionButton'
import ProfileResourceCard from './ProfileResourceCard'

interface UserPluginCardProps {
  plugin: UserPlugin
  onUnpublish: () => void
  onEdit: () => void
  t: (key: string, options?: Record<string, unknown>) => string
}

export default function UserPluginCard({ plugin, onUnpublish, onEdit, t }: UserPluginCardProps) {
  const [iconError, setIconError] = useState(false)

  return (
    <ProfileResourceCard
      media={
        plugin.icon && !iconError ? (
          <img
            src={plugin.icon}
            alt={`${plugin.name} 图标`}
            onError={() => setIconError(true)}
            style={{ width: '100%', height: '100%', objectFit: 'cover' }}
          />
        ) : (
          <ExtensionIcon
            sx={{
              fontSize: 28,
              opacity: 0.7,
              color: 'primary.main',
            }}
          />
        )
      }
      title={plugin.name}
      subtitle={plugin.moduleName}
      meta={
        <Chip
          label={t('cloud:profile.plugin')}
          size="small"
          color="primary"
          sx={{ height: 24, fontSize: '0.75rem' }}
        />
      }
      actions={
        <ActionButton size="small" tone="ghost" startIcon={<EditIcon />} onClick={onEdit}>
          {t('cloud:pluginsMarket.edit') || '编辑'}
        </ActionButton>
      }
      trailingAction={
        <ActionButton
          size="small"
          tone="danger"
          startIcon={<DeleteIcon />}
          onClick={onUnpublish}
        >
          {t('cloud:pluginsMarket.delist')}
        </ActionButton>
      }
    />
  )
}
