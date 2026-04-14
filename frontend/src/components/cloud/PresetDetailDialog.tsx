import { useState, useEffect } from 'react'
import {
  Box,
  Typography,
  Grid,
  Avatar,
  Chip,
  Button,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  useTheme,
  Divider,
} from '@mui/material'
import { Star as StarIcon } from '@mui/icons-material'
import { CloudPreset } from '../../services/api/cloud/presets_market'
import { favoritesApi } from '../../services/api/cloud/favorites'
import { formatLastActiveTimeFromInput } from '../../utils/time'
import { CARD_VARIANTS, CHIP_VARIANTS } from '../../theme/variants'

interface PresetDetailDialogProps {
  open: boolean
  onClose: () => void
  preset: CloudPreset | null
  t: (key: string, options?: Record<string, unknown>) => string
  onFavoriteChange?: (remoteId: string, isFavorited: boolean) => void
  showFavoriteAction?: boolean
}

export default function PresetDetailDialog({
  open,
  onClose,
  preset,
  t,
  onFavoriteChange,
  showFavoriteAction = true,
}: PresetDetailDialogProps) {
  const theme = useTheme()

  // 收藏状态
  const [isFavorited, setIsFavorited] = useState(false)
  const [favoriteCount, setFavoriteCount] = useState(preset?.favoriteCount || 0)
  const [favoriteLoading, setFavoriteLoading] = useState(false)

  // 获取收藏状态
  useEffect(() => {
    if (open && preset) {
      setFavoriteCount(preset.favoriteCount || 0)
      setIsFavorited(preset.isFavorited || false)
    }
  }, [open, preset])

  const handleFavoriteToggle = async () => {
    if (favoriteLoading || !preset) return
    setFavoriteLoading(true)
    try {
      if (isFavorited) {
        await favoritesApi.removeFavorite('preset', preset.remote_id)
        setIsFavorited(false)
        setFavoriteCount(prev => Math.max(0, prev - 1))
        onFavoriteChange?.(preset.remote_id, false)
      } else {
        await favoritesApi.addFavorite('preset', preset.remote_id)
        setIsFavorited(true)
        setFavoriteCount(prev => prev + 1)
        onFavoriteChange?.(preset.remote_id, true)
      }
    } catch (err) {
      console.error('收藏操作失败:', err)
    } finally {
      setFavoriteLoading(false)
    }
  }

  // 显式依赖theme以确保主题切换时重新渲染
  const dialogBackground = theme.palette.mode === 'dark' ? 'rgba(255,255,255,0.03)' : 'rgba(0,0,0,0.02)'

  // 额外创建内容区域背景样式
  const contentBackground = theme.palette.mode === 'dark' ? 'rgba(0, 0, 0, 0.2)' : 'rgba(0, 0, 0, 0.03)'

  if (!preset) return null

  const tagsArray = preset.tags.split(',').filter(tag => tag.trim())

  return (
    <Dialog
      open={open}
      onClose={onClose}
      maxWidth="md"
      fullWidth
      scroll="paper"
      PaperProps={{
        sx: {
          ...CARD_VARIANTS.default.styles,
          overflow: 'hidden',
        },
      }}
    >
      <DialogTitle
        sx={{
          px: 3,
          py: 2,
          background: dialogBackground,
          borderBottom: '1px solid',
          borderColor: 'divider',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
        }}
      >
        <Typography variant="h6" component="span">
          {t('presetsMarket.presetDetail')}: {preset.title || preset.name}
        </Typography>
      </DialogTitle>
      <DialogContent dividers sx={{ p: 3 }}>
        <Grid container spacing={3}>
          <Grid item xs={12} sm={4} md={3}>
            <Box sx={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 2.5 }}>
              <Avatar
                src={preset.avatar}
                alt={preset.name}
                variant="rounded"
                sx={{
                  width: '100%',
                  height: 'auto',
                  aspectRatio: '1/1',
                  borderRadius: 2,
                  boxShadow: theme.shadows[3],
                }}
              />
              <Box sx={{ width: '100%' }}>
                <Typography variant="subtitle2" gutterBottom fontWeight={600}>
                  {t('presetsMarket.tags')}:
                </Typography>
                <Box sx={{ display: 'flex', gap: 0.75, flexWrap: 'wrap' }}>
                  {tagsArray.length > 0 ? (
                    tagsArray.map((tag, index) => (
                      <Chip
                        key={index}
                        label={tag.trim()}
                        size="small"
                        sx={{
                          ...CHIP_VARIANTS.base(false),
                          margin: '2px',
                          bgcolor:
                            theme.palette.mode === 'dark'
                              ? 'rgba(255,255,255,0.08)'
                              : 'rgba(0,0,0,0.05)',
                        }}
                      />
                    ))
                  ) : (
                    <Typography variant="caption" color="text.disabled">
                      {t('presetsMarket.noTags')}
                    </Typography>
                  )}
                </Box>
              </Box>
            </Box>
          </Grid>

          <Grid item xs={12} sm={8} md={9}>
            <Typography variant="h5" gutterBottom fontWeight={600}>
              {preset.title || preset.name}
            </Typography>

            <Box sx={{ mb: 3 }}>
              <Typography variant="subtitle1" color="text.secondary" gutterBottom>
                {t('presetsMarket.author')}: {preset.author || t('presetsMarket.unknownAuthor')}
              </Typography>
              <Typography
                variant="body1"
                paragraph
                sx={{
                  backgroundColor: dialogBackground,
                  p: 2,
                  borderRadius: 1,
                  borderLeft: '4px solid',
                  borderColor: 'primary.main',
                  mt: 1,
                }}
              >
                {preset.description || t('presetsMarket.noDescription')}
              </Typography>
              <Box sx={{ display: 'flex', gap: 3, flexWrap: 'wrap', mb: 2, mt: 3 }}>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                  <Typography variant="body2" color="text.secondary" fontWeight={500}>
                    {t('presetsMarket.createdAt')}:
                  </Typography>
                  <Typography variant="body2">
                    {formatLastActiveTimeFromInput(preset.create_time)}
                  </Typography>
                </Box>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                  <Typography variant="body2" color="text.secondary" fontWeight={500}>
                    {t('presetsMarket.updatedAt')}:
                  </Typography>
                  <Typography variant="body2">
                    {formatLastActiveTimeFromInput(preset.update_time)}
                  </Typography>
                </Box>
              </Box>
            </Box>

            <Divider sx={{ mb: 2.5 }} />

            <Typography variant="h6" gutterBottom fontWeight={600}>
              {t('presetsMarket.presetContent')}:
            </Typography>
            <Typography
              variant="body2"
              sx={{
                whiteSpace: 'pre-wrap',
                bgcolor: contentBackground,
                p: 2.5,
                borderRadius: 2,
                border: '1px solid',
                borderColor: 'divider',
                maxHeight: '350px',
                overflow: 'auto',
                fontFamily: 'monospace',
                fontSize: '0.9rem',
                lineHeight: 1.6,
              }}
            >
              {preset.content || t('presetsMarket.noContent')}
            </Typography>
          </Grid>
        </Grid>
      </DialogContent>
      <DialogActions sx={{ px: 3, py: 2 }}>
        {showFavoriteAction && (
          <Button
            variant={isFavorited ? 'contained' : 'outlined'}
            color={isFavorited ? 'error' : 'primary'}
            startIcon={<StarIcon />}
            onClick={handleFavoriteToggle}
            disabled={favoriteLoading}
          >
            {isFavorited ? t('presetsMarket.favorited') : t('presetsMarket.favorite')} ({favoriteCount})
          </Button>
        )}
        <Button variant="contained" onClick={onClose} color="primary">
          {t('presetsMarket.close')}
        </Button>
      </DialogActions>
    </Dialog>
  )
}
