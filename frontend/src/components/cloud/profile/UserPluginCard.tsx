import { useState } from 'react'
import { Box, Card, CardActions, CardContent, Chip, Typography } from '@mui/material'
import { Extension as ExtensionIcon, Delete as DeleteIcon, Edit as EditIcon } from '@mui/icons-material'
import { UserPlugin } from '../../../services/api/cloud/plugins_market'
import ActionButton from '../../common/ActionButton'
import { CARD_VARIANTS } from '../../../theme/variants'
import { UI_STYLES } from '../../../theme/themeConfig'

interface UserPluginCardProps {
  plugin: UserPlugin
  onUnpublish: () => void
  onEdit: () => void
  t: (key: string, options?: Record<string, unknown>) => string
}

export default function UserPluginCard({ plugin, onUnpublish, onEdit, t }: UserPluginCardProps) {
  const [iconError, setIconError] = useState(false)

  return (
    <Card
      sx={{
        ...CARD_VARIANTS.default.styles,
        height: '100%',
        display: 'flex',
        flexDirection: 'column',
        '&:hover': {
          transform: 'translateY(-2px)',
        },
      }}
    >
      <CardContent sx={{ flexGrow: 1, p: 2.5, pb: 1 }}>
        <Box
          sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', mb: 1 }}
        >
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5, width: '100%' }}>
            <Box
              sx={{
                width: 48,
                height: 48,
                borderRadius: 1,
                overflow: 'hidden',
                flexShrink: 0,
                border: '1px solid',
                borderColor: 'divider',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                backgroundColor: theme =>
                  theme.palette.mode === 'dark' ? 'rgba(255,255,255,0.05)' : 'rgba(0,0,0,0.02)',
              }}
            >
              {plugin.icon && !iconError ? (
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
                    color: theme => theme.palette.primary.main,
                  }}
                />
              )}
            </Box>

            <Box sx={{ overflow: 'hidden', flex: 1 }}>
              <Typography
                variant="h6"
                component="h2"
                sx={{
                  fontSize: '1rem',
                  fontWeight: 600,
                  overflow: 'hidden',
                  textOverflow: 'ellipsis',
                  whiteSpace: 'nowrap',
                }}
              >
                {plugin.name}
              </Typography>
            </Box>
          </Box>
        </Box>

        <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.75, mt: 1 }}>
          <Chip
            label={plugin.moduleName}
            size="small"
            sx={{
              height: 24,
              fontSize: '0.75rem',
              bgcolor: theme =>
                theme.palette.mode === 'dark' ? 'rgba(255,255,255,0.08)' : 'rgba(0,0,0,0.05)',
            }}
          />
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
        <ActionButton size="small" variant="text" startIcon={<EditIcon />} onClick={onEdit}>
          {t('cloud:pluginsMarket.edit') || '编辑'}
        </ActionButton>
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
