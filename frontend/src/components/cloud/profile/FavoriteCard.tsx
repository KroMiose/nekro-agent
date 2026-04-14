import { useState } from 'react'
import { Chip, IconButton, Tooltip } from '@mui/material'
import { Extension as ExtensionIcon, Face as FaceIcon, Favorite as FavoriteIcon, OpenInNew as OpenInNewIcon, Download as DownloadIcon, Delete as DeleteIcon } from '@mui/icons-material'
import { FavoriteItem } from '../../../services/api/cloud/favorites'
import ActionButton from '../../common/ActionButton'
import ProfileResourceCard from './ProfileResourceCard'

interface FavoriteCardProps {
  favorite: FavoriteItem
  onRemove: () => void
  onViewDetail: () => void
  onDownload: () => void
  t: (key: string, options?: Record<string, unknown>) => string
}

export default function FavoriteCard({ favorite, onRemove, onViewDetail, onDownload, t }: FavoriteCardProps) {
  const [iconError, setIconError] = useState(false)
  const isPlugin = favorite.targetType === 'plugin'
  const isObtained = Boolean(favorite.resource.isLocal)

  return (
    <ProfileResourceCard
      media={
        (favorite.resource.icon || favorite.resource.avatar) && !iconError ? (
          <img
            src={favorite.resource.icon || favorite.resource.avatar}
            alt={`${favorite.resource.name} 图标`}
            onError={() => setIconError(true)}
            style={{ width: '100%', height: '100%', objectFit: 'cover' }}
          />
        ) : isPlugin ? (
          <ExtensionIcon
            sx={{
              fontSize: 28,
              opacity: 0.7,
              color: 'primary.main',
            }}
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
      title={favorite.resource.title || favorite.resource.name}
      subtitle={`${t('cloud:profile.author')}: ${favorite.resource.author}`}
      description={favorite.resource.description || t('cloud:profile.noDescription')}
      meta={
        <>
          <Chip
            label={isPlugin ? t('cloud:profile.plugin') : t('cloud:profile.preset')}
            size="small"
            color={isPlugin ? 'primary' : 'secondary'}
            sx={{ height: 24, fontSize: '0.75rem' }}
          />
          {isObtained && (
            <Chip
              label={t('cloud:profile.obtained') || '已获取'}
              size="small"
              color="success"
              sx={{ height: 24, fontSize: '0.75rem' }}
            />
          )}
          <Chip
            label={`${t('cloud:profile.collectedAt')}: ${new Date(favorite.createdAt).toLocaleDateString()}`}
            size="small"
            sx={{ height: 24, fontSize: '0.75rem', bgcolor: 'action.selected' }}
          />
        </>
      }
      actions={
        <>
          <ActionButton size="small" tone="ghost" startIcon={<OpenInNewIcon />} onClick={onViewDetail}>
            {t('cloud:profile.viewDetail') || '查看详情'}
          </ActionButton>
          <ActionButton
            size="small"
            tone={isObtained ? 'secondary' : 'ghost'}
            startIcon={isObtained ? <DeleteIcon /> : <DownloadIcon />}
            onClick={onDownload}
            sx={isObtained ? { color: 'error.main' } : undefined}
          >
            {isObtained
              ? t('common:actions.delete') || '删除'
              : t('cloud:profile.download') || '下载'}
          </ActionButton>
        </>
      }
      trailingAction={
        <Tooltip title={t('cloud:profile.removeFavorite')}>
          <IconButton size="small" color="error" onClick={onRemove}>
            <FavoriteIcon />
          </IconButton>
        </Tooltip>
      }
    />
  )
}
