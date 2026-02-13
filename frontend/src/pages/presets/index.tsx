import { useState, useEffect, useRef, useCallback } from 'react'
import {
  Box,
  Typography,
  Button,
  TextField,
  Card,
  CardContent,
  CardActions,
  Grid,
  Chip,
  IconButton,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Avatar,
  InputAdornment,
  Divider,
  Tooltip,
  Alert,
  CircularProgress,
  FormControlLabel,
  Checkbox,
  Link,
  useTheme,
  useMediaQuery,
} from '@mui/material'
import {
  Add as AddIcon,
  Search as SearchIcon,
  Sync as SyncIcon,
  Delete as DeleteIcon,
  Edit as EditIcon,
  CloudDownload as CloudDownloadIcon,
  CloudUpload as CloudUploadIcon,
  CloudOff as CloudOffIcon,
  Upload as UploadIcon,
  Tag as TagIcon,
  CloudSync as CloudSyncIcon,
  Close as CloseIcon,
  InfoOutlined as InfoIcon,
  FilterList as FilterListIcon,
  Clear as ClearIcon,
} from '@mui/icons-material'
import { Preset, PresetDetail, presetsApi, TagInfo } from '../../services/api/presets'
import { useSnackbar } from 'notistack'
import { formatLastActiveTime } from '../../utils/time'

import { CHIP_VARIANTS, CARD_VARIANTS, SCROLLBAR_VARIANTS } from '../../theme/variants'
import { UI_STYLES } from '../../theme/themeConfig'
import { Fade } from '@mui/material'
import PaginationStyled from '../../components/common/PaginationStyled'
import { useTranslation } from 'react-i18next'

// 定义预设编辑表单数据类型
interface PresetFormData {
  name: string
  title: string
  avatar: string
  content: string
  description: string
  tags: string
  author: string
  remove_remote: boolean
}

// 编辑对话框组件
const PresetEditDialog = ({
  open,
  onClose,
  preset,
  onSave,
  isNew = false,
}: {
  open: boolean
  onClose: () => void
  preset?: PresetDetail
  onSave: (data: PresetFormData) => Promise<void>
  isNew?: boolean
}) => {
  const [loading, setLoading] = useState(false)
  const [formData, setFormData] = useState<PresetFormData>({
    name: '',
    title: '',
    avatar: '',
    content: '',
    description: '',
    tags: '',
    author: '',
    remove_remote: false,
  })
  const [confirmDialog, setConfirmDialog] = useState(false)
  const [errors, setErrors] = useState<Record<string, string>>({})
  const fileInputRef = useRef<HTMLInputElement>(null)
  const { enqueueSnackbar } = useSnackbar()
  const { t } = useTranslation('presets')

  useEffect(() => {
    if (preset) {
      setFormData({
        name: preset.name,
        title: preset.title || '',
        avatar: preset.avatar,
        content: preset.content || '',
        description: preset.description || '',
        tags: preset.tags || '',
        author: preset.author || '',
        remove_remote: false,
      })
    } else {
      setFormData({
        name: '',
        title: '',
        avatar: '',
        content: '',
        description: '',
        tags: '',
        author: '',
        remove_remote: false,
      })
    }
    // 重置错误状态
    setErrors({})
  }, [preset, open])

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
    const { name, value } = e.target
    setFormData(prev => ({
      ...prev,
      [name]: value,
    }))

    // 当字段值改变时，清除对应的错误信息
    if (errors[name]) {
      setErrors(prev => {
        const newErrors = { ...prev }
        delete newErrors[name]
        return newErrors
      })
    }
  }

  const handleTagKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter' || e.key === ',') {
      e.preventDefault()
      const input = e.target as HTMLInputElement
      const value = input.value.trim()

      if (value) {
        // 检查是否已有8个标签
        const tagsArray = formData.tags.split(',').filter(tag => tag.trim())
        if (tagsArray.length >= 8) {
          setErrors(prev => ({
            ...prev,
            tags: t('form.maxTags'),
          }))
          return
        }

        // 检查是否是重复标签
        if (tagsArray.some(tag => tag.trim().toLowerCase() === value.toLowerCase())) {
          setErrors(prev => ({
            ...prev,
            tags: t('form.duplicateTag'),
          }))
          return
        }

        // 清除标签错误信息
        if (errors.tags) {
          setErrors(prev => {
            const newErrors = { ...prev }
            delete newErrors.tags
            return newErrors
          })
        }

        // 清除输入框，并将新标签添加到已有标签中
        input.value = ''
        const newTags = formData.tags ? `${formData.tags},${value}` : value
        setFormData(prev => ({
          ...prev,
          tags: newTags,
        }))
      }
    }
  }

  const handleDeleteTag = (tagToDelete: string) => {
    const tagsArray = formData.tags
      .split(',')
      .filter(tag => tag.trim() && tag.trim() !== tagToDelete.trim())
    setFormData(prev => ({
      ...prev,
      tags: tagsArray.join(','),
    }))
  }

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return

    try {
      setLoading(true)
      const response = await presetsApi.uploadAvatar(file)
      setFormData(prev => ({
        ...prev,
        avatar: response.avatar,
      }))
      enqueueSnackbar(t('form.uploadSuccess'), { variant: 'success' })
    } catch {
      setErrors(prev => ({
        ...prev,
        avatar: t('form.retryUpload'),
      }))
    } finally {
      setLoading(false)
    }
  }

  // 验证表单
  const validateForm = (): boolean => {
    const newErrors: Record<string, string> = {}

    if (!formData.name.trim()) {
      newErrors.name = t('form.nameRequired')
    }

    if (!formData.content.trim()) {
      newErrors.content = t('form.contentRequired')
    }

    setErrors(newErrors)
    return Object.keys(newErrors).length === 0
  }

  const handleSave = async () => {
    // 验证表单
    if (!validateForm()) {
      return
    }

    // 如果是云端人设且正在编辑，但不是自己上传的(on_shared为false)，需要确认是否解除云端关联
    if (preset?.remote_id && !isNew && !preset?.on_shared && !confirmDialog) {
      setConfirmDialog(true)
      return
    }

    try {
      setLoading(true)
      await onSave({
        ...formData,
        // 如果是自己上传的云端人设(on_shared为true)，则不解除关联
        remove_remote: preset?.remote_id && !preset?.on_shared ? true : false,
      })
      onClose()
    } catch (error) {
      // 显示通用错误
      setErrors(prev => ({
        ...prev,
        general: error instanceof Error ? error.message : String(error),
      }))
    } finally {
      setLoading(false)
      setConfirmDialog(false)
    }
  }

  const handleRemoteConfirm = async (confirm: boolean) => {
    setConfirmDialog(false)
    if (confirm) {
      try {
        setLoading(true)
        await onSave({
          ...formData,
          remove_remote: true,
        })
        onClose()
      } catch (error) {
        // 显示通用错误
        setErrors(prev => ({
          ...prev,
          general: error instanceof Error ? error.message : String(error),
        }))
      } finally {
        setLoading(false)
      }
    }
  }

  return (
    <>
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
            background: theme =>
              theme.palette.mode === 'dark' ? 'rgba(255,255,255,0.03)' : 'rgba(0,0,0,0.02)',
            borderBottom: '1px solid',
            borderColor: 'divider',
          }}
        >
          {isNew ? t('dialog.createTitle') : t('dialog.editTitle')}
        </DialogTitle>
        <DialogContent dividers sx={{ p: 3 }}>
          <Box component="form" noValidate sx={{ mt: 1 }} className="space-y-4" autoComplete="off">
            {preset?.remote_id && preset?.on_shared && (
              <Alert severity="info" sx={{ mb: 2 }}>
                {t('cloud.sharedInfo')}
              </Alert>
            )}

            {errors.general && (
              <Alert severity="error" sx={{ mb: 2 }}>
                {errors.general}
              </Alert>
            )}

            <Grid container spacing={2}>
              <Grid item xs={12} md={4}>
                <Box className="flex flex-col items-center">
                  <Box
                    sx={{
                      width: '100%',
                      paddingBottom: '100%',
                      position: 'relative',
                      bgcolor: 'rgba(0,0,0,0.05)',
                      borderRadius: 2,
                      mb: 2,
                    }}
                  >
                    {formData.avatar ? (
                      <img
                        src={formData.avatar}
                        alt={t('form.avatar')}
                        style={{
                          position: 'absolute',
                          top: 0,
                          left: 0,
                          width: '100%',
                          height: '100%',
                          objectFit: 'cover',
                          borderRadius: 8,
                        }}
                      />
                    ) : (
                      <Box
                        sx={{
                          position: 'absolute',
                          top: 0,
                          left: 0,
                          width: '100%',
                          height: '100%',
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'center',
                          color: 'text.secondary',
                        }}
                      >
                        <Typography variant="body2">{t('form.noAvatar')}</Typography>
                      </Box>
                    )}
                    {loading && (
                      <Box
                        sx={{
                          position: 'absolute',
                          top: 0,
                          left: 0,
                          width: '100%',
                          height: '100%',
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'center',
                          bgcolor: 'rgba(0,0,0,0.3)',
                          borderRadius: 2,
                        }}
                      >
                        <CircularProgress />
                      </Box>
                    )}
                  </Box>
                  <input
                    type="file"
                    hidden
                    ref={fileInputRef}
                    accept="image/*"
                    onChange={handleFileUpload}
                    autoComplete="off"
                  />
                  <Button
                    variant="outlined"
                    onClick={() => fileInputRef.current?.click()}
                    disabled={loading}
                  >
                    {t('form.uploadAvatar')}
                  </Button>
                  {errors.avatar && (
                    <Typography variant="caption" color="error" mt={1}>
                      {errors.avatar}
                    </Typography>
                  )}
                  <Typography variant="caption" color="text.secondary" mt={1}>
                    {t('form.avatarTip')}
                  </Typography>
                </Box>
              </Grid>
              <Grid item xs={12} md={8} className="space-y-4">
                <TextField
                  name="name"
                  label={t('form.name')}
                  fullWidth
                  required
                  value={formData.name}
                  onChange={handleChange}
                  autoComplete="off"
                  error={!!errors.name}
                  helperText={errors.name}
                />
                <TextField
                  name="title"
                  label={t('form.title')}
                  fullWidth
                  value={formData.title}
                  onChange={handleChange}
                  helperText={t('form.titleHelper')}
                  autoComplete="off"
                />
                <Box sx={{ width: '100%', mb: 2 }}>
                  <Typography variant="body2" color="text.secondary" gutterBottom>
                    {t('form.tags')}
                  </Typography>

                  <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1, mb: 1 }}>
                    {formData.tags
                      .split(',')
                      .map(
                        (tag, index) =>
                          tag.trim() && (
                            <Chip
                              key={index}
                              label={tag.trim()}
                              size="small"
                              onDelete={() => handleDeleteTag(tag)}
                              sx={{ ...CHIP_VARIANTS.base(true) }}
                            />
                          )
                      )}
                  </Box>

                  <TextField
                    fullWidth
                    placeholder={t('form.tagsPlaceholder')}
                    size="small"
                    onKeyDown={handleTagKeyDown}
                    onChange={e => {
                      // 实时过滤非法字符
                      e.target.value = e.target.value.replace(/[^a-zA-Z0-9\u4e00-\u9fa5,\s]/g, '')
                    }}
                    InputProps={{
                      startAdornment: formData.tags ? (
                        <InputAdornment position="start">
                          <TagIcon fontSize="small" sx={{ opacity: 0.6 }} />
                        </InputAdornment>
                      ) : null,
                    }}
                    autoComplete="off"
                    helperText={errors.tags || t('form.tagsHelper')}
                  />
                </Box>
                <TextField
                  name="author"
                  label={t('form.author')}
                  fullWidth
                  value={formData.author}
                  onChange={handleChange}
                  autoComplete="off"
                />
                <TextField
                  name="description"
                  label={t('form.description')}
                  fullWidth
                  multiline
                  rows={2}
                  value={formData.description}
                  onChange={handleChange}
                  autoComplete="off"
                  helperText={t('form.descriptionHelper')}
                />
                <TextField
                  name="content"
                  label={t('form.content')}
                  fullWidth
                  required
                  multiline
                  rows={8}
                  value={formData.content}
                  onChange={handleChange}
                  autoComplete="off"
                  error={!!errors.content}
                  helperText={errors.content}
                />
              </Grid>
            </Grid>
          </Box>
        </DialogContent>
        <DialogActions sx={{ px: 3, py: 2 }}>
          <Button onClick={onClose} disabled={loading}>
            {t('dialog.cancel')}
          </Button>
          <Button onClick={handleSave} color="primary" disabled={loading} variant="contained">
            {loading ? <CircularProgress size={24} /> : t('dialog.save')}
          </Button>
        </DialogActions>
      </Dialog>

      {/* 确认解除云端关联的对话框 */}
      <Dialog
        open={confirmDialog}
        onClose={() => setConfirmDialog(false)}
        PaperProps={{
          sx: {
            ...CARD_VARIANTS.default.styles,
          },
        }}
      >
        <DialogTitle
          sx={{
            px: 3,
            py: 2,
            background: theme =>
              theme.palette.mode === 'dark' ? 'rgba(255,255,255,0.03)' : 'rgba(0,0,0,0.02)',
            borderBottom: '1px solid',
            borderColor: 'divider',
          }}
        >
          {t('cloud.unlinkTitle')}
        </DialogTitle>
        <DialogContent sx={{ p: 3 }}>
          <Alert severity="warning" sx={{ mb: 2 }}>
            {t('cloud.unlinkWarning')}
          </Alert>
          <Typography>{t('cloud.unlinkConfirm')}</Typography>
        </DialogContent>
        <DialogActions sx={{ px: 3, py: 2 }}>
          <Button onClick={() => handleRemoteConfirm(false)}>{t('dialog.cancel')}</Button>
          <Button onClick={() => handleRemoteConfirm(true)} color="primary" variant="contained">
            {t('cloud.unlinkButton')}
          </Button>
        </DialogActions>
      </Dialog>
    </>
  )
}

// 人设卡片组件
const PresetCard = ({
  preset: initialPreset,
  onExpand,
  expanded,
  onDelete,
  onSync,
  onEdit,
  showError,
  showSuccess,
  onRefreshList,
  isMobile,
  isSmall,
}: {
  preset: Preset
  onExpand: () => void
  expanded: boolean
  onDelete: () => void
  onSync: (id: number) => Promise<void>
  onEdit: () => void
  showError: (message: string) => void
  showSuccess: (message: string) => void
  onRefreshList: () => Promise<void>
  isMobile?: boolean
  isSmall?: boolean
}) => {
  const { enqueueSnackbar } = useSnackbar()
  const { t } = useTranslation('presets')
  const [preset, setPreset] = useState(initialPreset)
  const [loading, setLoading] = useState(false)
  const [detailData, setDetailData] = useState<PresetDetail | null>(null)
  const [showShareDialog, setShowShareDialog] = useState(false)
  const [showUnshareDialog, setShowUnshareDialog] = useState(false)
  const [showSyncToCloudDialog, setShowSyncToCloudDialog] = useState(false)
  const [isSfw, setIsSfw] = useState(true)
  const [agreeToTerms, setAgreeToTerms] = useState(false)
  const [shareLoading, setShareLoading] = useState(false)
  const [syncLoading, setSyncLoading] = useState(false)
  const theme = useTheme()
  const isGridLayout = useMediaQuery(theme.breakpoints.up('md'))

  // 更新 preset 当 initialPreset 变化时
  useEffect(() => {
    setPreset(initialPreset)
  }, [initialPreset])

  // 加载详情数据
  useEffect(() => {
    if (expanded && !detailData) {
      const fetchData = async () => {
        try {
          setLoading(true)
          const data = await presetsApi.getDetail(preset.id)
          setDetailData(data)
        } catch (error) {
          showError(t('card.loadDetails'))
        } finally {
          setLoading(false)
        }
      }
      fetchData()
    }
  }, [expanded, preset.id, enqueueSnackbar, detailData, showError, t])

  // 共享人设到云端
  const handleShareToCloud = async () => {
    try {
      setShareLoading(true)
      // 移除过程提示
      const response = await presetsApi.shareToCloud(preset.id, isSfw)
      showSuccess(t('cloud.shareSuccess'))
      setShowShareDialog(false)
      setPreset({
        ...preset,
        on_shared: true,
        remote_id: response.remote_id || String(preset.id),
      })
      await onRefreshList()
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : String(error)
      showError(`${t('cloud.shareFailed')}: ${errorMessage}`)
      setShowShareDialog(false)
    } finally {
      setShareLoading(false)
    }
  }

  // 撤回共享
  const handleUnshare = async () => {
    try {
      setShareLoading(true)
      // 移除过程提示
      await presetsApi.unshare(preset.id)
      showSuccess(t('cloud.revokeSuccess'))
      setShowUnshareDialog(false)
      setPreset({
        ...preset,
        on_shared: false,
        remote_id: null,
      })
      await onRefreshList()
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : String(error)
      showError(`${t('cloud.revokeFailed')}: ${errorMessage}`)
      setShowUnshareDialog(false)
    } finally {
      setShareLoading(false)
    }
  }

  // 同步到云端
  const handleSyncToCloud = async () => {
    try {
      setShareLoading(true)
      // 移除过程提示
      await presetsApi.syncToCloud(preset.id, isSfw)
      showSuccess(t('cloud.syncSuccess'))
      setShowSyncToCloudDialog(false)
      await onRefreshList()
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : String(error)
      showError(`${t('cloud.syncFailed')}: ${errorMessage}`)
      setShowSyncToCloudDialog(false)
    } finally {
      setShareLoading(false)
    }
  }

  const tagsArray = preset.tags.split(',').filter(tag => tag.trim())

  // 决定显示哪个共享按钮
  const renderShareButtons = () => {
    // 未共享 且 无远程id：显示"共享此设定"按钮
    if (!preset.on_shared && !preset.remote_id) {
      return (
        <Tooltip title={t('cloud.shareToCloud')}>
          <IconButton size="small" color="primary" onClick={() => setShowShareDialog(true)}>
            <CloudUploadIcon />
          </IconButton>
        </Tooltip>
      )
    }
    // 已共享 且 有远程id：显示"撤回共享"和"同步设定"按钮
    else if (preset.on_shared) {
      return (
        <>
          <Tooltip title={t('cloud.revokeShare')}>
            <IconButton size="small" color="warning" onClick={() => setShowUnshareDialog(true)}>
              <CloudOffIcon />
            </IconButton>
          </Tooltip>
          <Tooltip title={t('cloud.syncToCloud')}>
            <IconButton size="small" color="primary" onClick={() => setShowSyncToCloudDialog(true)}>
              <UploadIcon />
            </IconButton>
          </Tooltip>
        </>
      )
    }
    // 未共享但有远程id：显示"从云端同步"按钮（云端下载的人设）
    else if (!preset.on_shared && preset.remote_id) {
      return (
        <Tooltip title={t('cloud.syncFromCloud')}>
          <IconButton
            size="small"
            color="primary"
            onClick={async () => {
              setSyncLoading(true)
              try {
                await onSync(preset.id)
              } finally {
                setSyncLoading(false)
              }
            }}
            disabled={syncLoading}
          >
            {syncLoading ? <CircularProgress size={24} /> : <SyncIcon />}
          </IconButton>
        </Tooltip>
      )
    }
    return null
  }

  return (
    <Card
      sx={{
        ...CARD_VARIANTS.default.styles,
        position: 'relative',
        overflow: 'visible',
        height: isGridLayout ? '100%' : 'auto',
        display: 'flex',
        flexDirection: 'column',
        transition: 'all 0.2s ease-in-out',
        '&:hover': {
          transform: 'translateY(-2px)',
          boxShadow: theme => theme.shadows[8],
        },
        ...(preset.remote_id
          ? {
              boxShadow: theme =>
                `0 0 0 1px ${theme.palette.primary.light}30, 0 2px 8px ${theme.palette.primary.light}20`,
            }
          : {}),
      }}
    >
      {preset.remote_id && (
        <Chip
          icon={<CloudDownloadIcon />}
          label={t('filter.cloud')}
          size="small"
          color="primary"
          sx={{
            position: 'absolute',
            top: -10,
            right: 16,
            zIndex: 1,
            ...CHIP_VARIANTS.base(isSmall),
          }}
        />
      )}

      {preset.on_shared && (
        <Chip
          icon={<CloudUploadIcon />}
          label={t('filter.shared')}
          size="small"
          color="success"
          sx={{
            position: 'absolute',
            top: -10,
            right: preset.remote_id ? 110 : 16,
            zIndex: 1,
            ...CHIP_VARIANTS.base(isSmall),
          }}
        />
      )}

      <CardContent sx={{ p: 2.5, pb: 1, flex: 1, display: 'flex', flexDirection: 'column' }}>
        <Box
          sx={{
            display: 'flex',
            gap: 2.5,
            flexDirection: isGridLayout ? 'row' : isMobile && isSmall ? 'column' : 'row',
            height: '100%',
          }}
        >
          {/* 左侧头像区域 */}
          <Box
            sx={{
              width: isGridLayout
                ? 100
                : isMobile && isSmall
                  ? '100%'
                  : { xs: '25%', sm: '16.66%' },
              height: isGridLayout ? 100 : 'auto',
              flexShrink: 0,
              maxWidth: isMobile && isSmall && !isGridLayout ? '160px' : 'none',
              alignSelf: isMobile && isSmall && !isGridLayout ? 'center' : 'flex-start',
              mb: isMobile && isSmall && !isGridLayout ? 2 : 0,
            }}
          >
            <Avatar
              src={preset.avatar}
              alt={preset.name}
              sx={{
                width: '100%',
                height: isGridLayout ? '100%' : 'auto',
                aspectRatio: '1/1',
                borderRadius: 2,
                boxShadow: '0 3px 10px rgba(0,0,0,0.1)',
              }}
              variant="rounded"
            />
          </Box>

          {/* 右侧内容区域 */}
          <Box
            sx={{
              flex: 1,
              display: 'flex',
              flexDirection: 'column',
              justifyContent: 'space-between',
              minWidth: 0, // 防止内容溢出
              height: '100%',
            }}
          >
            <Box
              sx={{
                flex: '1 0 auto',
                display: 'flex',
                flexDirection: 'column',
                justifyContent: 'flex-start',
              }}
            >
              {/* 标题 */}
              <Typography
                variant={isGridLayout ? 'h6' : 'h6'}
                gutterBottom
                sx={{
                  overflow: 'hidden',
                  textOverflow: 'ellipsis',
                  display: '-webkit-box',
                  WebkitLineClamp: 1,
                  WebkitBoxOrient: 'vertical',
                  fontWeight: 600,
                  fontSize: '1.1rem',
                  lineHeight: 1.4,
                }}
              >
                {preset.title}
              </Typography>

              {/* 描述 */}
              <Typography
                variant="body2"
                color="text.secondary"
                sx={{
                  flex: '1 0 auto',
                  flexGrow: 1,
                  mb: 1.5,
                  lineHeight: 1.4,
                  maxHeight: expanded ? 'none' : isGridLayout ? '2.8em' : '4.2em',
                  overflow: 'hidden',
                  textOverflow: 'ellipsis',
                  display: '-webkit-box',
                  WebkitLineClamp: isGridLayout ? 2 : 3,
                  WebkitBoxOrient: 'vertical',
                }}
              >
                {preset.description || t('card.noDescription')}
              </Typography>
            </Box>

            <Box sx={{ display: 'flex', flexDirection: 'column', justifyContent: 'space-between' }}>
              {/* 标签栏 */}
              {(tagsArray.length > 0 || !isGridLayout) && (
                <Box
                  sx={{
                    display: 'flex',
                    gap: 0.75,
                    flexWrap: 'wrap',
                    my: 1,
                    maxHeight: isGridLayout ? '24px' : 'auto',
                    overflow: 'hidden',
                  }}
                >
                  {tagsArray.length > 0 ? (
                    tagsArray.slice(0, isGridLayout ? 3 : undefined).map((tag, index) => (
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
                  ) : !isGridLayout ? (
                    <Typography variant="caption" color="text.disabled">
                      {t('filter.noTags')}
                    </Typography>
                  ) : null}
                  {isGridLayout && tagsArray.length > 3 && (
                    <Typography
                      variant="caption"
                      color="text.secondary"
                      sx={{ alignSelf: 'center' }}
                    >
                      +{tagsArray.length - 3}
                    </Typography>
                  )}
                </Box>
              )}

              {/* 底部信息栏 */}
              {!isGridLayout && (
                <Box
                  sx={{
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                  }}
                >
                  <Typography variant="caption" color="text.secondary">
                    {t('form.author')}: {preset.author || t('common.unknown', { ns: 'common' })}
                  </Typography>
                  <Typography variant="caption" color="text.secondary">
                    最近更新: {formatLastActiveTime(new Date(preset.update_time).getTime() / 1000)}
                  </Typography>
                </Box>
              )}
            </Box>
          </Box>
        </Box>
      </CardContent>

      <CardActions
        sx={{
          justifyContent: 'space-between',
          p: 1.5,
          mt: 'auto',
          bgcolor: UI_STYLES.SELECTED,
          borderTop: '1px solid',
          borderColor: 'divider',
        }}
      >
        <Button
          size="small"
          variant="text"
          startIcon={<InfoIcon />}
          onClick={onExpand}
          sx={{
            textTransform: 'none',
            fontWeight: 'normal',
            '&:hover': {
              backgroundColor: 'transparent',
              color: theme => theme.palette.primary.main,
            },
          }}
        >
          {t('card.moreActions')}
        </Button>
        <Box>
          <Tooltip title={t('card.edit')}>
            <IconButton size="small" color="primary" onClick={onEdit}>
              <EditIcon />
            </IconButton>
          </Tooltip>
          {preset.remote_id && preset.on_shared && (
            <Tooltip title={t('cloud.syncFromCloud')}>
              <IconButton
                size="small"
                color="primary"
                onClick={async () => {
                  setSyncLoading(true)
                try {
                  await onSync(preset.id)
                } finally {
                  setSyncLoading(false)
                }
                }}
                disabled={syncLoading}
              >
                {syncLoading ? <CircularProgress size={24} /> : <SyncIcon />}
              </IconButton>
            </Tooltip>
          )}
          {renderShareButtons()}
          <Tooltip title={t('card.delete')}>
            <IconButton size="small" color="error" onClick={onDelete}>
              <DeleteIcon />
            </IconButton>
          </Tooltip>
        </Box>
      </CardActions>

      {/* 使用MUI Dialog组件实现展开内容 */}
      <Dialog
        open={expanded}
        onClose={onExpand}
        maxWidth="md"
        fullWidth
        scroll="paper"
        TransitionComponent={Fade}
        transitionDuration={{ enter: 300, exit: 200 }}
        PaperProps={{
          elevation: 8,
          sx: {
            ...CARD_VARIANTS.default.styles,
            overflow: 'hidden',
            maxWidth: isMobile ? '95%' : '800px',
            maxHeight: '80vh',
          },
        }}
      >
        <DialogTitle
          sx={{
            px: 3,
            py: 2,
            background: theme =>
              theme.palette.mode === 'dark' ? 'rgba(255,255,255,0.03)' : 'rgba(0,0,0,0.02)',
            borderBottom: '1px solid',
            borderColor: 'divider',
            display: 'flex',
            alignItems: 'center',
            gap: 1,
          }}
        >
          <Avatar
            src={preset.avatar}
            sx={{ width: 36, height: 36, borderRadius: 1 }}
            variant="rounded"
          />
          <Typography variant="h6" component="div" sx={{ flex: 1 }}>
            人设详情：{preset.title}
          </Typography>
          <IconButton size="small" onClick={onExpand} edge="end">
            <CloseIcon />
          </IconButton>
        </DialogTitle>
        <DialogContent dividers sx={{ p: 3 }}>
          {loading ? (
            <Box sx={{ display: 'flex', justifyContent: 'center', py: 4 }}>
              <CircularProgress />
            </Box>
          ) : detailData ? (
            <Grid container spacing={3}>
              <Grid item xs={12} sm={4} md={3}>
                <Box
                  sx={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 2.5 }}
                >
                  <Avatar
                    src={preset.avatar}
                    alt={preset.name}
                    variant="rounded"
                    sx={{
                      width: '100%',
                      height: 'auto',
                      aspectRatio: '1/1',
                      borderRadius: 2,
                      boxShadow: theme => theme.shadows[3],
                    }}
                  />
                  <Box sx={{ width: '100%' }}>
                    <Typography variant="subtitle2" gutterBottom fontWeight={600}>
                      标签:
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
                              bgcolor: theme =>
                                theme.palette.mode === 'dark'
                                  ? 'rgba(255,255,255,0.08)'
                                  : 'rgba(0,0,0,0.05)',
                            }}
                          />
                        ))
                      ) : (
                        <Typography variant="caption" color="text.disabled">
                          {t('filter.noTags')}
                        </Typography>
                      )}
                    </Box>
                  </Box>
                </Box>
              </Grid>
              <Grid item xs={12} sm={8} md={9}>
                <Typography variant="h5" gutterBottom fontWeight={600}>
                  {preset.title}
                </Typography>
                <Box sx={{ mb: 3 }}>
                  <Typography variant="subtitle1" color="text.secondary" gutterBottom>
                    {t('form.author')}: {preset.author || t('common.unknown', { ns: 'common' })}
                  </Typography>
                  <Typography
                    variant="body1"
                    paragraph
                    sx={{
                      backgroundColor: theme =>
                        theme.palette.mode === 'dark'
                          ? 'rgba(255,255,255,0.03)'
                          : 'rgba(0,0,0,0.02)',
                      p: 2,
                      borderRadius: 1,
                      borderLeft: '4px solid',
                      borderColor: 'primary.main',
                      mt: 1,
                    }}
                  >
                    {preset.description || t('card.noDescription')}
                  </Typography>
                  <Box sx={{ display: 'flex', gap: 3, flexWrap: 'wrap', mb: 2, mt: 3 }}>
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                      <Typography variant="body2" color="text.secondary" fontWeight={500}>
                        {t('card.updatedAt')}:
                      </Typography>
                      <Typography variant="body2">
                        {formatLastActiveTime(new Date(preset.update_time).getTime() / 1000)}
                      </Typography>
                    </Box>
                  </Box>
                </Box>
                <Divider sx={{ mb: 2.5 }} />
                <Typography variant="h6" gutterBottom fontWeight={600}>
                  {t('form.content')}:
                </Typography>
                <Typography
                  variant="body2"
                  sx={{
                    whiteSpace: 'pre-wrap',
                    bgcolor: theme =>
                      theme.palette.mode === 'dark' ? 'rgba(0, 0, 0, 0.2)' : 'rgba(0, 0, 0, 0.03)',
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
                  {detailData.content || t('card.noContent')}
                </Typography>
              </Grid>
            </Grid>
          ) : (
            <Typography color="text.secondary">{t('card.loadDetails')}</Typography>
          )}
        </DialogContent>
        <DialogActions sx={{ px: 3, py: 2 }}>
          <Button variant="contained" onClick={onExpand} color="primary">
            {t('actions.close')}
          </Button>
        </DialogActions>
      </Dialog>

      {/* 共享对话框 */}
      <Dialog
        open={showShareDialog}
        onClose={() => setShowShareDialog(false)}
        PaperProps={{
          sx: {
            ...CARD_VARIANTS.default.styles,
          },
        }}
      >
        <DialogTitle
          sx={{
            px: 3,
            py: 2,
            background: theme =>
              theme.palette.mode === 'dark' ? 'rgba(255,255,255,0.03)' : 'rgba(0,0,0,0.02)',
            borderBottom: '1px solid',
            borderColor: 'divider',
          }}
        >
          {t('cloud.shareConfirmTitle')}
        </DialogTitle>
        <DialogContent sx={{ p: 3 }}>
          <Typography paragraph>{t('cloud.shareConfirmMessage')}</Typography>
          <Alert severity="info" sx={{ mb: 2 }}>
            {t('cloud.shareInfo')}
          </Alert>
          <Box sx={{ display: 'flex', flexDirection: 'column' }}>
            <FormControlLabel
              control={<Checkbox checked={isSfw} onChange={e => setIsSfw(e.target.checked)} />}
              label={t('cloud.sfwConfirm')}
            />
            <FormControlLabel
              control={
                <Checkbox
                  checked={agreeToTerms}
                  onChange={e => setAgreeToTerms(e.target.checked)}
                />
              }
              label={
                <Box component="span" sx={{ display: 'flex', alignItems: 'center' }}>
                  {t('cloud.termsConfirm')}{' '}
                  <Link
                    href="https://community.nekro.ai/terms"
                    target="_blank"
                    underline="hover"
                    sx={{ ml: 0.5 }}
                  >
                    {t('cloud.termsLink')}
                  </Link>
                </Box>
              }
            />
          </Box>
        </DialogContent>
        <DialogActions sx={{ px: 3, py: 2 }}>
          <Button onClick={() => setShowShareDialog(false)} disabled={shareLoading}>
            {t('dialog.cancel')}
          </Button>
          <Button
            onClick={handleShareToCloud}
            color="primary"
            variant="contained"
            disabled={shareLoading || !isSfw || !agreeToTerms}
          >
            {shareLoading ? <CircularProgress size={24} /> : t('actions.share')}
          </Button>
        </DialogActions>
      </Dialog>

      {/* 撤回共享对话框 */}
      <Dialog
        open={showUnshareDialog}
        onClose={() => setShowUnshareDialog(false)}
        PaperProps={{
          sx: {
            ...CARD_VARIANTS.default.styles,
          },
        }}
      >
        <DialogTitle
          sx={{
            px: 3,
            py: 2,
            background: theme =>
              theme.palette.mode === 'dark' ? 'rgba(255,255,255,0.03)' : 'rgba(0,0,0,0.02)',
            borderBottom: '1px solid',
            borderColor: 'divider',
          }}
        >
          {t('cloud.revokeConfirmTitle')}
        </DialogTitle>
        <DialogContent sx={{ p: 3 }}>
          <Alert severity="warning" sx={{ mb: 2 }}>
            {t('cloud.revokeWarning')}
          </Alert>
          <Typography>{t('cloud.revokeConfirmMessage')}</Typography>
        </DialogContent>
        <DialogActions sx={{ px: 3, py: 2 }}>
          <Button onClick={() => setShowUnshareDialog(false)} disabled={shareLoading}>
            {t('dialog.cancel')}
          </Button>
          <Button
            onClick={handleUnshare}
            color="warning"
            variant="contained"
            disabled={shareLoading}
          >
            {shareLoading ? <CircularProgress size={24} /> : t('cloud.revokeShare')}
          </Button>
        </DialogActions>
      </Dialog>

      {/* 同步云端对话框 */}
      <Dialog
        open={showSyncToCloudDialog}
        onClose={() => setShowSyncToCloudDialog(false)}
        PaperProps={{
          sx: {
            ...CARD_VARIANTS.default.styles,
          },
        }}
      >
        <DialogTitle
          sx={{
            px: 3,
            py: 2,
            background: theme =>
              theme.palette.mode === 'dark' ? 'rgba(255,255,255,0.03)' : 'rgba(0,0,0,0.02)',
            borderBottom: '1px solid',
            borderColor: 'divider',
          }}
        >
          {t('cloud.syncConfirmTitle')}
        </DialogTitle>
        <DialogContent sx={{ p: 3 }}>
          <Typography paragraph>{t('cloud.syncConfirmMessage')}</Typography>
          <Alert severity="info" sx={{ mb: 2 }}>
            {t('cloud.syncWarning')}
          </Alert>
          <Box sx={{ display: 'flex', flexDirection: 'column' }}>
            <FormControlLabel
              control={<Checkbox checked={isSfw} onChange={e => setIsSfw(e.target.checked)} />}
              label={t('cloud.sfwConfirm')}
            />
            <FormControlLabel
              control={
                <Checkbox
                  checked={agreeToTerms}
                  onChange={e => setAgreeToTerms(e.target.checked)}
                />
              }
              label={
                <Box component="span" sx={{ display: 'flex', alignItems: 'center' }}>
                  {t('cloud.termsConfirm')}{' '}
                  <Link
                    href="https://community.nekro.ai/terms"
                    target="_blank"
                    underline="hover"
                    sx={{ ml: 0.5 }}
                  >
                    {t('cloud.termsLink')}
                  </Link>
                </Box>
              }
            />
          </Box>
        </DialogContent>
        <DialogActions sx={{ px: 3, py: 2 }}>
          <Button onClick={() => setShowSyncToCloudDialog(false)} disabled={shareLoading}>
            {t('dialog.cancel')}
          </Button>
          <Button
            onClick={handleSyncToCloud}
            color="primary"
            variant="contained"
            disabled={shareLoading || !isSfw || !agreeToTerms}
          >
            {shareLoading ? <CircularProgress size={24} /> : '同步'}
          </Button>
        </DialogActions>
      </Dialog>
    </Card>
  )
}

// 主页面组件
export default function PresetsPage() {
  const [presets, setPresets] = useState<Preset[]>([])
  const [loading, setLoading] = useState(true)
  const [page, setPage] = useState(1)
  const pageSize = 25
  const [search, setSearch] = useState('')
  const [selectedTags, setSelectedTags] = useState<string[]>([])
  const [totalPages, setTotalPages] = useState(1)
  const [availableTags, setAvailableTags] = useState<TagInfo[]>([])
  const [expandedId, setExpandedId] = useState<number | null>(null)
  const [editDialog, setEditDialog] = useState(false)
  const [editingPreset, setEditingPreset] = useState<PresetDetail | undefined>(undefined)
  const [confirmDelete, setConfirmDelete] = useState<number | null>(null)
  const { enqueueSnackbar } = useSnackbar()
  const [refreshingShared, setRefreshingShared] = useState(false)
  const theme = useTheme()
  const isMobile = useMediaQuery(theme.breakpoints.down('md'))
  const isSmall = useMediaQuery(theme.breakpoints.down('sm'))
  // 添加宽屏检测
  const isLargeScreen = useMediaQuery(theme.breakpoints.up('lg'))
  const isExtraLargeScreen = useMediaQuery(theme.breakpoints.up('xl'))
  const { t } = useTranslation('presets')

  // 统一使用 notistack 的通知系统
  const showError = useCallback(
    (message: string) => {
      enqueueSnackbar(message, { variant: 'error', autoHideDuration: 5000 })
    },
    [enqueueSnackbar]
  )

  // 统一使用 notistack 的通知系统
  const showSuccess = useCallback(
    (message: string) => {
      enqueueSnackbar(message, { variant: 'success', autoHideDuration: 3000 })
    },
    [enqueueSnackbar]
  )

  const fetchData = useCallback(async () => {
    try {
      setLoading(true)
      const data = await presetsApi.getList({
        page,
        page_size: pageSize,
        search: search || undefined,
        tags: selectedTags.length ? selectedTags.join(',') : undefined,
      })
      setPresets(data.items)
      setTotalPages(Math.ceil(data.total / pageSize))

      // 如果当前页没有数据但总数大于0，说明可能是删除后的页码问题，回到第一页
      if (data.items.length === 0 && data.total > 0 && page > 1) {
        setPage(1)
      }
    } catch (error) {
      showError(t('list.fetchFailed'))
    } finally {
      setLoading(false)
    }
  }, [page, pageSize, search, selectedTags, showError, t])

  useEffect(() => {
    fetchData()
  }, [fetchData])

  // 获取所有可用标签
  const fetchAvailableTags = useCallback(async () => {
    try {
      const tags = await presetsApi.getTags()
      setAvailableTags(tags)
    } catch (error) {
      showError(t('list.fetchTagsFailed'))
    }
  }, [showError, t])

  useEffect(() => {
    fetchAvailableTags()
  }, [fetchAvailableTags])

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault()
    setPage(1)
  }

  const handleTagFilter = (tag: string) => {
    setSelectedTags(prev => {
      const exists = prev.includes(tag)
      const next = exists ? prev.filter(t => t !== tag) : [...prev, tag]
      return next
    })
    setPage(1)
  }

  const handlePageChange = (_event: React.ChangeEvent<unknown>, newPage: number) => {
    setPage(newPage)
    // 页面变化时滚动到顶部
    window.scrollTo({ top: 0, behavior: 'smooth' })
  }

  const handleExpandClick = (id: number) => {
    setExpandedId(expandedId === id ? null : id)
  }

  const handleEditClick = async (preset: Preset) => {
    try {
      showSuccess(t('list.loadingDetails'))
      // 加载详细数据
      const detailData = await presetsApi.getDetail(preset.id)
      setEditingPreset(detailData)
      setEditDialog(true)
    } catch (error) {
      showError(t('card.loadDetails'))
    }
  }

  const handleSave = async (data: PresetFormData) => {
    try {
      if (editingPreset) {
        showSuccess(t('list.updating'))
        await presetsApi.update(editingPreset.id, data)
        showSuccess(t('messages.updateSuccess', { ns: 'common' }))
      } else {
        showSuccess(t('list.creating'))
        await presetsApi.create(data)
        showSuccess(t('messages.createSuccess', { ns: 'common' }))
      }
      fetchData()
      fetchAvailableTags() // 刷新标签列表
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : String(error)
      showError(`${t('messages.saveFailed', { ns: 'common' })}: ${errorMessage}`)
      throw error // 传递错误以便上层组件处理
    }
  }

  const handleDeleteClick = (id: number) => {
    setConfirmDelete(id)
  }

  const handleDeleteConfirm = async () => {
    if (confirmDelete === null) return

    try {
      showSuccess(t('list.deleting'))
      await presetsApi.delete(confirmDelete)
      showSuccess(t('messages.deleteSuccess', { ns: 'common' }))
      fetchData()
      fetchAvailableTags() // 刷新标签列表
      if (expandedId === confirmDelete) {
        setExpandedId(null)
      }
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : String(error)
      showError(`${t('messages.deleteFailed', { ns: 'common' })}: ${errorMessage}`)
    } finally {
      setConfirmDelete(null)
    }
  }

  const handleSyncClick = async (id: number): Promise<void> => {
    try {
      await presetsApi.sync(id)
      showSuccess(t('cloud.syncSuccess'))
      await fetchData()
      if (expandedId === id) {
        setExpandedId(null)
        setTimeout(() => setExpandedId(id), 100)
      }
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : String(error)
      showError(`${t('cloud.syncFailed')}: ${errorMessage}`)
      throw error
    }
  }

  // 添加刷新共享状态的函数
  const handleRefreshSharedStatus = async () => {
    try {
      setRefreshingShared(true)
      showSuccess(t('cloud.refreshingStatus'))
      const response = await presetsApi.refreshSharedStatus()
      showSuccess(t('cloud.refreshStatusSuccess'))
      showSuccess(
        t('cloud.refreshStatusDetails', {
          updated: response.updated_count,
          total: response.total_cloud_presets,
        })
      )
      await fetchData()
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : String(error)
      showError(`${t('cloud.refreshFailed')}: ${errorMessage}`)
    } finally {
      setRefreshingShared(false)
    }
  }

  // 修改PresetCard组件，传入showError函数
  const renderPresetCard = (preset: Preset) => (
    <PresetCard
      key={preset.id}
      preset={preset}
      expanded={expandedId === preset.id}
      onExpand={() => handleExpandClick(preset.id)}
      onDelete={() => handleDeleteClick(preset.id)}
      onSync={handleSyncClick}
      onEdit={() => handleEditClick(preset)}
      showError={showError}
      showSuccess={showSuccess}
      onRefreshList={fetchData}
      isMobile={isMobile}
      isSmall={isSmall}
    />
  )

  // 根据屏幕尺寸决定网格布局的列数
  const getGridColumns = () => {
    if (isExtraLargeScreen) return 3 // 超大屏幕显示3列
    if (isLargeScreen) return 2 // 大屏幕显示2列
    return 1 // 默认显示1列
  }

  return (
    <Box sx={{ p: 3, height: '100%', overflow: 'auto' }}>
      <Box className="flex justify-between items-center mb-4 flex-wrap gap-2">
        <Box component="form" onSubmit={handleSearch} className="flex" autoComplete="off">
          <TextField
            size="small"
            placeholder={t('search.placeholder')}
            value={search}
            onChange={e => setSearch(e.target.value)}
            autoComplete="off"
            InputProps={{
              startAdornment: (
                <InputAdornment position="start">
                  <SearchIcon fontSize="small" />
                </InputAdornment>
              ),
            }}
          />
          {/* <Button type="submit" sx={{ ml: 1 }}>
            搜索
          </Button> */}
        </Box>
        <Box className="flex gap-2">
          <Button
            variant="outlined"
            startIcon={<CloudSyncIcon />}
            onClick={handleRefreshSharedStatus}
            disabled={refreshingShared}
            size={isSmall ? 'small' : 'medium'}
          >
            {refreshingShared ? (
              <CircularProgress size={isSmall ? 16 : 24} />
            ) : isMobile ? (
              t('actions.refreshShort')
            ) : (
              t('actions.refresh')
            )}
          </Button>
          <Button
            variant="contained"
            startIcon={<AddIcon />}
            onClick={() => {
              setEditingPreset(undefined)
              setEditDialog(true)
            }}
            size={isSmall ? 'small' : 'medium'}
          >
            {t('actions.create')}
          </Button>
        </Box>
      </Box>

      {/* 标签过滤栏 */}
      {availableTags.length > 0 && (
        <Box
          sx={{
            mb: 3,
            ...CARD_VARIANTS.default.styles,
            p: 2,
            borderRadius: 2,
          }}
        >
          <Box
            sx={{
              display: 'flex',
              alignItems: 'center',
              gap: 1,
              mb: 2,
              flexWrap: 'wrap',
            }}
          >
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
              <FilterListIcon fontSize="small" color="primary" />
              <Typography variant="body2" color="text.secondary" fontWeight={500}>
                {t('filter.byTag', { count: availableTags.length })}
              </Typography>
            </Box>
            {selectedTags.length > 0 && (
              <Button
                size="small"
                startIcon={<ClearIcon />}
                onClick={() => setSelectedTags([])}
                sx={{
                  fontSize: '0.75rem',
                  minHeight: 24,
                  px: 1,
                  color: 'text.secondary',
                  '&:hover': {
                    color: 'primary.main',
                  },
                }}
              >
                {t('filter.clearFilters')}
              </Button>
            )}
          </Box>
          <Box
            sx={{
              display: 'flex',
              gap: 1,
              flexWrap: 'wrap',
              maxHeight: isSmall ? '140px' : '100px',
              overflow: 'auto',
              ...SCROLLBAR_VARIANTS.thin.styles,
            }}
          >
            {availableTags.map(({ tag, count }) => (
              <Chip
                key={tag}
                label={`${tag} (${count})`}
                onClick={() => handleTagFilter(tag)}
                color={selectedTags.includes(tag) ? 'primary' : 'default'}
                variant={selectedTags.includes(tag) ? 'filled' : 'outlined'}
                size={isSmall ? 'small' : 'medium'}
                sx={{
                  cursor: 'pointer',
                  transition: 'all 0.2s',
                  fontWeight: selectedTags.includes(tag) ? 600 : 400,
                  '&:hover': {
                    transform: 'translateY(-1px)',
                    boxShadow: theme => theme.shadows[2],
                  },
                  // 使用主题系统的背景样式
                  ...(!selectedTags.includes(tag) && {
                    background: UI_STYLES.HOVER,
                    '&:hover': {
                      background: UI_STYLES.SELECTED,
                      transform: 'translateY(-1px)',
                      boxShadow: theme => theme.shadows[2],
                    },
                  }),
                }}
              />
            ))}
          </Box>
        </Box>
      )}

      {loading && presets.length === 0 ? (
        <Box sx={{ display: 'flex', justifyContent: 'center', py: 8 }}>
          <CircularProgress />
        </Box>
      ) : presets.length > 0 ? (
        <>
          <Grid container spacing={isSmall ? 1.5 : 2}>
            {presets.map(preset => (
              <Grid
                item
                xs={12}
                md={getGridColumns() === 2 ? 6 : 12}
                lg={getGridColumns() === 3 ? 4 : 6}
                key={preset.id}
              >
                {renderPresetCard(preset)}
              </Grid>
            ))}
          </Grid>

          {/* 分页组件和统计信息 */}
          <Box
            sx={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 1, mt: 3 }}
          >
            {/* 总数统计 */}
            <PaginationStyled
              totalPages={totalPages}
              currentPage={page}
              onPageChange={handlePageChange}
              loading={loading}
              showPageInfo={!isSmall}
              siblingCount={isSmall ? 0 : 1}
              boundaryCount={isSmall ? 1 : 1}
            />
          </Box>
        </>
      ) : (
        <Box
          sx={{
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            justifyContent: 'center',
            py: isSmall ? 4 : 8,
          }}
        >
          <Typography color="text.secondary" gutterBottom>
            {t('list.noResults')}
          </Typography>
          <Button
            variant="outlined"
            startIcon={<AddIcon />}
            onClick={() => {
              setEditingPreset(undefined)
              setEditDialog(true)
            }}
            size={isSmall ? 'small' : 'medium'}
          >
            {t('actions.create')}
          </Button>
        </Box>
      )}

      {/* 编辑对话框 */}
      <PresetEditDialog
        open={editDialog}
        onClose={() => setEditDialog(false)}
        preset={editingPreset}
        onSave={handleSave}
        isNew={!editingPreset}
      />

      {/* 删除确认对话框 */}
      <Dialog
        open={confirmDelete !== null}
        onClose={() => setConfirmDelete(null)}
        PaperProps={{
          sx: {
            ...CARD_VARIANTS.default.styles,
          },
        }}
      >
        <DialogTitle
          sx={{
            px: 3,
            py: 2,
            background: theme =>
              theme.palette.mode === 'dark' ? 'rgba(255,255,255,0.03)' : 'rgba(0,0,0,0.02)',
            borderBottom: '1px solid',
            borderColor: 'divider',
          }}
        >
          {t('dialog.confirmDeleteTitle')}
        </DialogTitle>
        <DialogContent sx={{ p: 3 }}>
          <Typography>{t('dialog.confirmDeleteMessage')}</Typography>
        </DialogContent>
        <DialogActions sx={{ px: 3, py: 2 }}>
          <Button onClick={() => setConfirmDelete(null)}>{t('dialog.cancel')}</Button>
          <Button onClick={handleDeleteConfirm} color="error" variant="contained">
            {t('dialog.confirmDeleteTitle')}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  )
}
