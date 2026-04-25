import { useState, useEffect, useCallback } from 'react'
import {
  Box,
  Typography,
  Alert,
  Grid,
  Card,
  CardContent,
  CardActions,
  Avatar,
  Chip,
  CircularProgress,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
} from '@mui/material'
import {
  InfoOutlined as InfoIcon,
  Add as AddIcon,
  CloudDownload as CloudDownloadIcon,
  Done as DoneIcon,
  Star as StarIcon,
} from '@mui/icons-material'
import { presetsMarketApi, CloudPreset } from '../../services/api/cloud/presets_market'
import { favoritesApi } from '../../services/api/cloud/favorites'
import { useSnackbar } from 'notistack'
import PaginationStyled from '../../components/common/PaginationStyled'
import PresetDetailDialog from '../../components/cloud/PresetDetailDialog'
import { useNavigate } from 'react-router-dom'
import { UI_STYLES } from '../../theme/themeConfig'
import { CHIP_VARIANTS, CARD_VARIANTS } from '../../theme/variants'
import { useTranslation } from 'react-i18next'
import SearchActionBar from '../../components/common/SearchActionBar'
import ActionButton from '../../components/common/ActionButton'

// 防抖自定义Hook
function useDebounce<T>(value: T, delay: number): T {
  const [debouncedValue, setDebouncedValue] = useState<T>(value)

  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedValue(value)
    }, delay)

    return () => {
      clearTimeout(timer)
    }
  }, [value, delay])

  return debouncedValue
}

// 人设卡片组件
const PresetCard = ({
  preset,
  onDownload,
  onShowDetail,
  t,
}: {
  preset: CloudPreset
  onDownload: () => void
  onShowDetail: () => void
  t: (key: string, options?: Record<string, unknown>) => string
}) => {
  const tagsArray = preset.tags.split(',').filter(tag => tag.trim())

  // 收藏状态
  const [isFavorited, setIsFavorited] = useState(preset.isFavorited || false)
  const [favoriteCount, setFavoriteCount] = useState(preset.favoriteCount || 0)
  const [favoriteLoading, setFavoriteLoading] = useState(false)

  // 同步人设收藏状态
  useEffect(() => {
    setIsFavorited(preset.isFavorited || false)
    setFavoriteCount(preset.favoriteCount || 0)
  }, [preset.isFavorited, preset.favoriteCount])

  const handleFavoriteToggle = async (e: React.MouseEvent) => {
    e.stopPropagation()
    if (favoriteLoading) return
    setFavoriteLoading(true)
    try {
      if (isFavorited) {
        await favoritesApi.removeFavorite('preset', preset.remote_id)
        setIsFavorited(false)
        setFavoriteCount(prev => Math.max(0, prev - 1))
      } else {
        await favoritesApi.addFavorite('preset', preset.remote_id)
        setIsFavorited(true)
        setFavoriteCount(prev => prev + 1)
      }
    } catch (err) {
      console.error('收藏操作失败:', err)
    } finally {
      setFavoriteLoading(false)
    }
  }

  return (
    <Card
      sx={{
        ...CARD_VARIANTS.default.styles,
        display: 'flex',
        flexDirection: 'column',
        height: '100%',
        overflow: 'hidden',
        position: 'relative',
        '&:hover': {
          transform: 'translateY(-2px)',
        },
      }}
    >
      <CardContent sx={{ flexGrow: 1, p: { xs: 1.5, sm: 2.5 }, pb: 1 }}>
        <Box sx={{ display: 'flex', gap: { xs: 1.25, sm: 2.5 }, mb: 2, alignItems: 'flex-start' }}>
          {/* 头像 */}
          <Avatar
            src={preset.avatar}
            alt={preset.name}
            variant="rounded"
            sx={{
              flexShrink: 0,
              width: { xs: 72, sm: 100 },
              height: { xs: 72, sm: 100 },
              borderRadius: 2,
              boxShadow: '0 3px 10px rgba(0,0,0,0.1)',
            }}
          />

          {/* 基本信息 */}
          <Box sx={{ flexGrow: 1, minWidth: 0 }}>
            <Typography
              variant="h6"
              gutterBottom
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
              sx={{
                overflow: 'hidden',
                textOverflow: 'ellipsis',
                display: '-webkit-box',
                WebkitLineClamp: 2,
                WebkitBoxOrient: 'vertical',
                mb: 1,
              }}
            >
              {preset.description || t('presetsMarket.noDescription')}
            </Typography>
            <Box sx={{ display: 'flex', justifyContent: 'space-between', minWidth: 0 }}>
              <Typography variant="caption" color="text.secondary">
                {t('presetsMarket.author')}: {preset.author || t('presetsMarket.unknownAuthor')}
              </Typography>
            </Box>
          </Box>
        </Box>

        {/* 标签 */}
        <Box sx={{ display: 'flex', gap: 0.75, flexWrap: 'wrap', my: 1 }}>
          {tagsArray.length > 0 ? (
            tagsArray.map((tag, index) => (
              <Chip
                key={index}
                label={tag.trim()}
                size="small"
                sx={{
                  ...CHIP_VARIANTS.base(false),
                  bgcolor: UI_STYLES.HOVER,
                  fontWeight: 500,
                  borderRadius: 1,
                }}
              />
            ))
          ) : (
            <Typography variant="caption" color="text.disabled">
              {t('presetsMarket.noTags')}
            </Typography>
          )}
          <Chip
            icon={<StarIcon sx={{ fontSize: 14 }} />}
            label={favoriteCount}
            size="small"
            color={isFavorited ? 'error' : 'default'}
            sx={{ height: 24, fontSize: '0.75rem', ml: 1, cursor: 'pointer' }}
            onClick={handleFavoriteToggle}
            disabled={favoriteLoading}
          />
        </Box>
      </CardContent>

      <CardActions
        sx={{
          justifyContent: 'space-between',
          flexWrap: 'wrap',
          gap: 1,
          p: 1.5,
          bgcolor: UI_STYLES.SELECTED,
          borderTop: '1px solid',
          borderColor: 'divider',
        }}
      >
        <ActionButton size="small" variant="text" startIcon={<InfoIcon />} onClick={onShowDetail}>
          {t('presetsMarket.details')}
        </ActionButton>
        <ActionButton
          size="small"
          variant={preset.is_local ? 'text' : 'contained'}
          startIcon={preset.is_local ? <DoneIcon /> : <CloudDownloadIcon />}
          onClick={onDownload}
          disabled={preset.is_local}
          color="primary"
        >
          {preset.is_local ? t('presetsMarket.obtained') : t('presetsMarket.obtain')}
        </ActionButton>
      </CardActions>
    </Card>
  )
}

export default function PresetsMarket() {
  const [presets, setPresets] = useState<CloudPreset[]>([])
  const [loading, setLoading] = useState(true)
  const [searchKeyword, setSearchKeyword] = useState('')
  const debouncedSearchKeyword = useDebounce(searchKeyword, 800)
  const [currentPage, setCurrentPage] = useState(1)
  const [totalPages, setTotalPages] = useState(1)
  const [error, setError] = useState<string | null>(null)
  const [selectedPreset, setSelectedPreset] = useState<CloudPreset | null>(null)
  const [downloadingId, setDownloadingId] = useState<string | null>(null)
  const [confirmDialog, setConfirmDialog] = useState<{ open: boolean; preset: CloudPreset | null }>(
    {
      open: false,
      preset: null,
    }
  )
  const { enqueueSnackbar } = useSnackbar()
  const navigate = useNavigate()
  const { t } = useTranslation('cloud')
  const pageSize = 12

  const fetchPresets = useCallback(
    async (page: number, keyword: string = '') => {
      try {
        setLoading(true)
        setError(null)

        const data = await presetsMarketApi.getList({
          page,
          page_size: pageSize,
          keyword: keyword || undefined,
        })

        setPresets(data.items)
        setTotalPages(data.total_pages)

        if (data.items.length === 0 && data.total > 0 && page > 1) {
          // 如果当前页没有数据但总数大于0，说明可能是删除后的页码问题，回到第一页
          setCurrentPage(1)
          fetchPresets(1, keyword)
        }
      } catch (error) {
        const errorMessage = error instanceof Error ? error.message : String(error)
        setError(`${t('presetsMarket.fetchFailed')}: ${errorMessage}`)
      } finally {
        setLoading(false)
      }
    },
    [pageSize, setCurrentPage, setLoading, setError, setPresets, setTotalPages, t]
  )

  useEffect(() => {
    fetchPresets(currentPage, debouncedSearchKeyword)
  }, [fetchPresets, currentPage, debouncedSearchKeyword])

  // 监听防抖后的搜索关键词变化，重置到第一页
  useEffect(() => {
    // 当搜索关键词变化时重置页码到第一页
    setCurrentPage(1)
  }, [debouncedSearchKeyword])

  const handlePageChange = (_event: React.ChangeEvent<unknown>, page: number) => {
    if (loading) return // 加载中禁止翻页
    setCurrentPage(page)
  }

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault()
    if (loading) return // 加载中禁止搜索
    setCurrentPage(1)
    fetchPresets(1, searchKeyword)
  }

  const handleSearchInputClear = () => {
    if (loading) return // 加载中禁止清空
    setSearchKeyword('')
    setCurrentPage(1)
    fetchPresets(1, '')
  }

  const handleShowDetail = (preset: CloudPreset) => {
    setSelectedPreset(preset)
  }

  const handleDownloadClick = (preset: CloudPreset) => {
    setConfirmDialog({ open: true, preset })
  }

  const handleDownloadConfirm = async () => {
    if (!confirmDialog.preset) return

    try {
      setDownloadingId(confirmDialog.preset.remote_id)
      const response = await presetsMarketApi.downloadPreset(confirmDialog.preset.remote_id)
      if (response.ok) {
        enqueueSnackbar(t('presetsMarket.obtainSuccess'), { variant: 'success' })
        setPresets(prev =>
          prev.map(p =>
            p.remote_id === confirmDialog.preset?.remote_id ? { ...p, is_local: true } : p
          )
        )
      }
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : String(error)
      enqueueSnackbar(t('presetsMarket.obtainFailedWithReason', { reason: errorMessage }), {
        variant: 'error',
      })
    } finally {
      setDownloadingId(null)
      setConfirmDialog({ open: false, preset: null })
    }
  }

  if (error && presets.length === 0) {
    return (
      <Box sx={{ p: 3, height: '100%', overflow: 'auto' }}>
        <Alert severity="error">{error}</Alert>
      </Box>
    )
  }

  return (
    <Box sx={{ p: { xs: 1.5, sm: 2, md: 3 }, height: '100%', overflow: 'auto' }}>
      <Box
        sx={{
          mb: { xs: 2, md: 4 },
          display: 'flex',
          justifyContent: 'space-between',
          flexWrap: 'wrap',
          gap: 2,
          alignItems: 'center',
        }}
      >
        <SearchActionBar
          value={searchKeyword}
          onChange={setSearchKeyword}
          onClear={handleSearchInputClear}
          onSubmit={handleSearch}
          placeholder={t('presetsMarket.searchPlaceholder')}
          actionLabel={loading ? t('presetsMarket.searching') : t('presetsMarket.search')}
          actionDisabled={loading}
        />
        <Box sx={{ display: 'flex', gap: 2, alignItems: 'center', width: { xs: '100%', sm: 'auto' } }}>
          <ActionButton
            tone="primary"
            startIcon={<AddIcon />}
            onClick={() => navigate('/presets')}
            sx={{ width: { xs: '100%', sm: 'auto' } }}
          >
            {t('presetsMarket.publishPreset')}
          </ActionButton>
        </Box>
      </Box>

      {/* 人设内容区域 */}
      <Box position="relative" minHeight={presets.length === 0 ? '300px' : 'auto'}>
        {/* 加载状态覆盖层 */}
        {loading && (
          <Box
            sx={{
              position: 'absolute',
              top: 0,
              left: 0,
              right: 0,
              bottom: 0,
              display: 'flex',
              justifyContent: 'center',
              alignItems: presets.length === 0 ? 'center' : 'flex-start',
              backgroundColor: 'transparent',
              zIndex: 10,
              borderRadius: 2,
              backdropFilter: 'blur(2px)',
              pt: presets.length === 0 ? 0 : 3,
            }}
          >
            <Box
              sx={{
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                gap: 1,
                backgroundColor: theme =>
                  theme.palette.mode === 'dark'
                    ? 'rgba(30, 30, 30, 0.8)'
                    : 'rgba(255, 255, 255, 0.9)',
                boxShadow: theme =>
                  theme.palette.mode === 'dark'
                    ? '0 4px 20px rgba(0, 0, 0, 0.5)'
                    : '0 4px 20px rgba(0, 0, 0, 0.1)',
                borderRadius: 2,
                padding: '12px 24px',
              }}
            >
              <CircularProgress size={28} thickness={4} />
              <Typography variant="body2" sx={{ opacity: 0.8 }}>
                {t('presetsMarket.loading')}
              </Typography>
            </Box>
          </Box>
        )}

        {presets.length > 0 ? (
          <>
            <Grid container spacing={{ xs: 1.5, sm: 2, md: 3 }}>
              {presets.map(preset => (
                <Grid item xs={12} sm={6} md={4} key={preset.remote_id}>
                  <PresetCard
                    preset={preset}
                    onDownload={() => handleDownloadClick(preset)}
                    onShowDetail={() => handleShowDetail(preset)}
                    t={t}
                  />
                </Grid>
              ))}
            </Grid>

            <PaginationStyled
              totalPages={totalPages}
              currentPage={currentPage}
              onPageChange={handlePageChange}
              loading={loading}
            />
          </>
        ) : (
          !loading && (
            <Box
              sx={{
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                justifyContent: 'center',
                py: 8,
                px: 2,
                minHeight: 300,
                textAlign: 'center',
                bgcolor: theme =>
                  theme.palette.mode === 'dark' ? 'rgba(255,255,255,0.02)' : 'rgba(0,0,0,0.02)',
                borderRadius: 2,
                border: '1px dashed',
                borderColor: 'divider',
              }}
            >
              <Typography variant="h6" color="text.secondary" sx={{ mb: 1, fontWeight: 'normal' }}>
                {t('presetsMarket.noResults.title')}
              </Typography>
              <Typography variant="body2" color="text.disabled" sx={{ maxWidth: 400 }}>
                {t('presetsMarket.noResults.hint1')}
                <br />
                {t('presetsMarket.noResults.hint2')}
              </Typography>
            </Box>
          )
        )}
      </Box>

      {/* 详情对话框 */}
      <PresetDetailDialog
        open={!!selectedPreset}
        onClose={() => setSelectedPreset(null)}
        preset={selectedPreset}
        t={t}
      />

      {/* 确认获取对话框 */}
      <Dialog
        open={confirmDialog.open}
        onClose={() => setConfirmDialog({ open: false, preset: null })}
      >
        <DialogTitle>{t('presetsMarket.confirmObtain')}</DialogTitle>
        <DialogContent>
          <Typography>
            {t('presetsMarket.confirmObtainMessage', {
              name: confirmDialog.preset?.title || confirmDialog.preset?.name,
            })}
          </Typography>
        </DialogContent>
        <DialogActions>
          <ActionButton
            tone="secondary"
            onClick={() => setConfirmDialog({ open: false, preset: null })}
            disabled={!!downloadingId}
          >
            {t('presetsMarket.cancel')}
          </ActionButton>
          <ActionButton tone="primary" onClick={handleDownloadConfirm} disabled={!!downloadingId}>
            {downloadingId ? <CircularProgress size={24} /> : t('presetsMarket.confirm')}
          </ActionButton>
        </DialogActions>
      </Dialog>
    </Box>
  )
}
