import { useState, useEffect, useCallback, useMemo } from 'react'
import {
  Box,
  Typography,
  Alert,
  Grid,
  Card,
  CardContent,
  CardActions,
  Button,
  Avatar,
  Chip,
  TextField,
  InputAdornment,
  IconButton,
  CircularProgress,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  useTheme,
  Divider,
} from '@mui/material'
import {
  Search as SearchIcon,
  Clear as ClearIcon,
  InfoOutlined as InfoIcon,
  Add as AddIcon,
  CloudDownload as CloudDownloadIcon,
  Done as DoneIcon,
} from '@mui/icons-material'
import { presetsMarketApi, CloudPreset } from '../../services/api/cloud/presets_market'
import { useSnackbar } from 'notistack'
import { formatLastActiveTime } from '../../utils/time'
import PaginationStyled from '../../components/common/PaginationStyled'
import { useNavigate } from 'react-router-dom'
import { UI_STYLES } from '../../theme/themeConfig'
import { CHIP_VARIANTS, CARD_VARIANTS } from '../../theme/variants'
import { useTranslation } from 'react-i18next'

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
      <CardContent sx={{ flexGrow: 1, p: 2.5, pb: 1 }}>
        <Box sx={{ display: 'flex', gap: 2.5, mb: 2 }}>
          {/* 头像 */}
          <Avatar
            src={preset.avatar}
            alt={preset.name}
            variant="rounded"
            sx={{
              width: 100,
              height: 100,
              borderRadius: 2,
              boxShadow: '0 3px 10px rgba(0,0,0,0.1)',
            }}
          />

          {/* 基本信息 */}
          <Box sx={{ flexGrow: 1 }}>
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
            <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
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
        <Button size="small" variant="text" startIcon={<InfoIcon />} onClick={onShowDetail}>
          {t('presetsMarket.details')}
        </Button>
        <Button
          size="small"
          variant={preset.is_local ? 'text' : 'contained'}
          startIcon={preset.is_local ? <DoneIcon /> : <CloudDownloadIcon />}
          onClick={onDownload}
          disabled={preset.is_local}
          color="primary"
        >
          {preset.is_local ? t('presetsMarket.obtained') : t('presetsMarket.obtain')}
        </Button>
      </CardActions>
    </Card>
  )
}

// 详情对话框组件
const PresetDetailDialog = ({
  open,
  onClose,
  preset,
  t,
}: {
  open: boolean
  onClose: () => void
  preset: CloudPreset | null
  t: (key: string, options?: Record<string, unknown>) => string
}) => {
  const theme = useTheme()

  // 显式依赖theme以确保主题切换时重新渲染
  const dialogBackground = useMemo(
    () => (theme.palette.mode === 'dark' ? 'rgba(255,255,255,0.03)' : 'rgba(0,0,0,0.02)'),
    [theme.palette.mode]
  )

  // 额外创建内容区域背景样式
  const contentBackground = useMemo(
    () => (theme.palette.mode === 'dark' ? 'rgba(0, 0, 0, 0.2)' : 'rgba(0, 0, 0, 0.03)'),
    [theme.palette.mode]
  )

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
        }}
      >
        <Typography variant="h6">
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
                    {formatLastActiveTime(new Date(preset.create_time).getTime() / 1000)}
                  </Typography>
                </Box>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                  <Typography variant="body2" color="text.secondary" fontWeight={500}>
                    {t('presetsMarket.updatedAt')}:
                  </Typography>
                  <Typography variant="body2">
                    {formatLastActiveTime(new Date(preset.update_time).getTime() / 1000)}
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
        <Button variant="contained" onClick={onClose} color="primary">
          {t('presetsMarket.close')}
        </Button>
      </DialogActions>
    </Dialog>
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
        console.error('Failed to fetch presets', error)
        setError(t('presetsMarket.fetchFailed'))
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

      if (response.code === 200) {
        enqueueSnackbar(t('presetsMarket.obtainSuccess'), { variant: 'success' })
        // 更新本地状态
        setPresets(prev =>
          prev.map(p =>
            p.remote_id === confirmDialog.preset?.remote_id ? { ...p, is_local: true } : p
          )
        )
      } else {
        enqueueSnackbar(t('presetsMarket.obtainFailedWithReason', { reason: response.msg }), {
          variant: 'error',
        })
      }
    } catch (error) {
      console.error('Obtain failed', error)
      enqueueSnackbar(t('presetsMarket.obtainRetry'), { variant: 'error' })
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
    <Box sx={{ p: 3, height: '100%', overflow: 'auto' }}>
      <Box
        sx={{
          mb: 4,
          display: 'flex',
          justifyContent: 'space-between',
          flexWrap: 'wrap',
          gap: 2,
          alignItems: 'center',
        }}
      >
        <Box
          component="form"
          onSubmit={handleSearch}
          sx={{
            display: 'flex',
            boxShadow: theme =>
              theme.palette.mode === 'dark'
                ? '0 0 10px rgba(0,0,0,0.2)'
                : '0 0 15px rgba(0,0,0,0.07)',
            borderRadius: 2,
          }}
        >
          <TextField
            size="small"
            placeholder={t('presetsMarket.searchPlaceholder')}
            value={searchKeyword}
            onChange={e => setSearchKeyword(e.target.value)}
            sx={{
              minWidth: 220,
              '& .MuiOutlinedInput-root': {
                borderRadius: '8px 0 0 8px',
              },
            }}
            InputProps={{
              startAdornment: (
                <InputAdornment position="start">
                  <SearchIcon fontSize="small" />
                </InputAdornment>
              ),
              endAdornment: searchKeyword && (
                <InputAdornment position="end">
                  <IconButton size="small" onClick={handleSearchInputClear}>
                    <ClearIcon fontSize="small" />
                  </IconButton>
                </InputAdornment>
              ),
            }}
          />
          <Button
            type="submit"
            disabled={loading}
            sx={{
              borderRadius: '0 8px 8px 0',
              px: 2,
              background: theme => theme.palette.primary.main,
              '&:hover': {
                background: theme => theme.palette.primary.dark,
              },
            }}
            variant="contained"
          >
            {loading ? t('presetsMarket.searching') : t('presetsMarket.search')}
          </Button>
        </Box>
        <Box sx={{ display: 'flex', gap: 2, alignItems: 'center' }}>
          <Button
            variant="contained"
            color="primary"
            startIcon={<AddIcon />}
            onClick={() => navigate('/presets')}
          >
            {t('presetsMarket.publishPreset')}
          </Button>
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
            <Grid container spacing={3}>
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
          <Button
            onClick={() => setConfirmDialog({ open: false, preset: null })}
            disabled={!!downloadingId}
          >
            {t('presetsMarket.cancel')}
          </Button>
          <Button onClick={handleDownloadConfirm} color="primary" disabled={!!downloadingId}>
            {downloadingId ? <CircularProgress size={24} /> : t('presetsMarket.confirm')}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  )
}
