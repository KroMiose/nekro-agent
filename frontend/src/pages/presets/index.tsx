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
  Snackbar,
  Link,
  useTheme,
  useMediaQuery,
} from '@mui/material'
import {
  Add as AddIcon,
  Search as SearchIcon,
  Sync as SyncIcon,
  ExpandMore as ExpandMoreIcon,
  ExpandLess as ExpandLessIcon,
  Delete as DeleteIcon,
  Edit as EditIcon,
  CloudDownload as CloudDownloadIcon,
  CloudUpload as CloudUploadIcon,
  CloudOff as CloudOffIcon,
  Upload as UploadIcon,
  Tag as TagIcon,
  CloudSync as CloudSyncIcon,
  Close as CloseIcon,
} from '@mui/icons-material'
import { Preset, PresetDetail, presetsApi } from '../../services/api/presets'
import { useSnackbar } from 'notistack'
import { formatLastActiveTime } from '../../utils/time'
import { UI_STYLES, BORDER_RADIUS } from '../../theme/themeConfig'
import { LAYOUT, CHIP_VARIANTS } from '../../theme/variants'
import { Fade } from '@mui/material'

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
            tags: '最多只能添加8个标签',
          }))
          return
        }

        // 检查是否是重复标签
        if (tagsArray.some(tag => tag.trim().toLowerCase() === value.toLowerCase())) {
          setErrors(prev => ({
            ...prev,
            tags: '标签不能重复',
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
      if (response.code === 200) {
        setFormData(prev => ({
          ...prev,
          avatar: response.data.avatar,
        }))
        enqueueSnackbar('头像上传成功', { variant: 'success' })
      } else {
        setErrors(prev => ({
          ...prev,
          avatar: `上传失败: ${response.msg}`,
        }))
      }
    } catch {
      setErrors(prev => ({
        ...prev,
        avatar: '上传失败，请重试',
      }))
    } finally {
      setLoading(false)
    }
  }

  // 验证表单
  const validateForm = (): boolean => {
    const newErrors: Record<string, string> = {}

    if (!formData.name.trim()) {
      newErrors.name = '请输入人设名称'
    }

    if (!formData.content.trim()) {
      newErrors.content = '请输入人设内容'
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
      console.error('保存失败', error)
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
        console.error('保存失败', error)
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
      <Dialog open={open} onClose={onClose} maxWidth="md" fullWidth>
        <DialogTitle>{isNew ? '创建新人设' : '编辑人设'}</DialogTitle>
        <DialogContent dividers>
          <Box component="form" noValidate sx={{ mt: 1 }} className="space-y-4" autoComplete="off">
            {preset?.remote_id && preset?.on_shared && (
              <Alert severity="info" sx={{ mb: 2 }}>
                此人设已共享到云端，保存后可以通过"同步到云端"按钮将修改同步到云端共享。
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
                        alt="头像预览"
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
                        <Typography variant="body2">无头像</Typography>
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
                    上传头像
                  </Button>
                  {errors.avatar && (
                    <Typography variant="caption" color="error" mt={1}>
                      {errors.avatar}
                    </Typography>
                  )}
                  <Typography variant="caption" color="text.secondary" mt={1}>
                    建议比例: 正方形图片, 将自动压缩至 500KB 内
                  </Typography>
                </Box>
              </Grid>
              <Grid item xs={12} md={8} className="space-y-4">
                <TextField
                  name="name"
                  label="人设名称"
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
                  label="标题"
                  fullWidth
                  value={formData.title}
                  onChange={handleChange}
                  helperText="默认与名称相同"
                  autoComplete="off"
                />
                <Box sx={{ width: '100%', mb: 2 }}>
                  <Typography variant="body2" color="text.secondary" gutterBottom>
                    标签
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
                    placeholder="输入标签后按回车或逗号添加"
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
                    helperText={errors.tags || '用逗号或回车分隔多个标签，最多8个'}
                  />
                </Box>
                <TextField
                  name="author"
                  label="作者"
                  fullWidth
                  value={formData.author}
                  onChange={handleChange}
                  autoComplete="off"
                />
                <TextField
                  name="description"
                  label="描述"
                  fullWidth
                  multiline
                  rows={2}
                  value={formData.description}
                  onChange={handleChange}
                  autoComplete="off"
                  helperText="填写人设的简要描述"
                />
                <TextField
                  name="content"
                  label="人设内容"
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
        <DialogActions>
          <Button onClick={onClose} disabled={loading}>
            取消
          </Button>
          <Button onClick={handleSave} color="primary" disabled={loading}>
            {loading ? <CircularProgress size={24} /> : '保存'}
          </Button>
        </DialogActions>
      </Dialog>

      {/* 确认解除云端关联的对话框 */}
      <Dialog open={confirmDialog} onClose={() => setConfirmDialog(false)}>
        <DialogTitle>解除云端关联确认</DialogTitle>
        <DialogContent>
          <Alert severity="warning" sx={{ mb: 2 }}>
            此人设来自云端下载，编辑后将解除与云端的关联，无法再同步最新更新。
          </Alert>
          <Typography>确定要继续编辑并解除云端关联吗？</Typography>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => handleRemoteConfirm(false)}>取消</Button>
          <Button onClick={() => handleRemoteConfirm(true)} color="primary">
            确认解除并继续
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
          console.error('获取人设详情失败', error)
          enqueueSnackbar('获取人设详情失败', { variant: 'error', autoHideDuration: 5000 })
          showError('获取人设详情失败')
        } finally {
          setLoading(false)
        }
      }
      fetchData()
    }
  }, [expanded, preset.id, enqueueSnackbar, detailData, showError])

  // 共享人设到云端
  const handleShareToCloud = async () => {
    try {
      setShareLoading(true)
      // 移除过程提示
      const response = await presetsApi.shareToCloud(preset.id, isSfw)
      if (response.code === 200) {
        showSuccess('共享成功')
        setShowShareDialog(false)
        // 更新本地状态
        setPreset({
          ...preset,
          on_shared: true,
          remote_id: response.data?.remote_id || String(preset.id),
        })
        await onRefreshList()
      } else {
        // 直接显示错误，只使用全局错误提示
        const errorMsg = response.msg || '未知错误'
        showError(`共享失败: ${errorMsg}`)

        // 如果是描述缺失错误，打开编辑对话框
        if (response.msg && response.msg.includes('描述不能为空')) {
          setTimeout(() => {
            showError('请添加人设描述后再共享')
            onEdit()
          }, 800)
        }
        setShowShareDialog(false)
      }
    } catch (error) {
      console.error('共享失败', error)
      const errorMessage = error instanceof Error ? error.message : String(error)
      showError(`共享失败: ${errorMessage}`)
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
      const response = await presetsApi.unshare(preset.id)
      if (response.code === 200) {
        showSuccess('撤回共享成功')
        setShowUnshareDialog(false)
        // 更新本地状态
        setPreset({
          ...preset,
          on_shared: false,
          remote_id: null,
        })
        await onRefreshList()
      } else {
        const errorMsg = response.msg || '未知错误'
        showError(`撤回共享失败: ${errorMsg}`)
        setShowUnshareDialog(false)
      }
    } catch (error) {
      console.error('撤回共享失败', error)
      const errorMessage = error instanceof Error ? error.message : String(error)
      showError(`撤回共享失败: ${errorMessage}`)
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
      const response = await presetsApi.syncToCloud(preset.id, isSfw)
      if (response.code === 200) {
        showSuccess('同步成功')
        // 显示更详细的成功信息
        if (response.msg) {
          showSuccess(response.msg)
        }
        setShowSyncToCloudDialog(false)
        await onRefreshList()
      } else {
        // 直接显示错误，同时使用全局错误提示
        const errorMsg = response.msg || '未知错误'
        showError(`同步失败: ${errorMsg}`)

        // 如果是描述缺失错误，打开编辑对话框
        if (response.msg && response.msg.includes('描述不能为空')) {
          setTimeout(() => {
            showError('请添加人设描述后再同步')
            onEdit()
          }, 800)
        }
        setShowSyncToCloudDialog(false)
      }
    } catch (error) {
      console.error('同步失败', error)
      const errorMessage = error instanceof Error ? error.message : String(error)
      showError(`同步失败: ${errorMessage}`)
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
        <Tooltip title="共享此设定到云端">
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
          <Tooltip title="撤回共享">
            <IconButton size="small" color="warning" onClick={() => setShowUnshareDialog(true)}>
              <CloudOffIcon />
            </IconButton>
          </Tooltip>
          <Tooltip title="同步更新到云端">
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
        <Tooltip title="从云端同步最新版本">
          <IconButton
            size="small"
            color="primary"
            onClick={async () => {
              setSyncLoading(true)
              try {
                await onSync(preset.id)
              } catch (error) {
                console.error('同步按钮错误:', error)
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
        position: 'relative',
        transition: LAYOUT.TRANSITION.DEFAULT,
        overflow: 'visible',
        height: isGridLayout ? '100%' : 'auto',
        display: 'flex',
        flexDirection: 'column',
        '&:hover': {
          boxShadow: UI_STYLES.SHADOWS.CARD.HOVER,
          transform: 'translateY(-2px)',
        },
        background: UI_STYLES.GRADIENTS.CARD.DEFAULT,
        backdropFilter: UI_STYLES.CARD_LAYOUT.BACKDROP_FILTER,
        border: UI_STYLES.BORDERS.CARD.DEFAULT,
        borderRadius: BORDER_RADIUS.DEFAULT,
        ...(preset.remote_id
          ? {
              boxShadow: theme =>
                `0 0 0 1px ${theme.palette.primary.light}30, 0 2px 8px ${theme.palette.primary.light}20`,
              bgcolor: theme =>
                theme.palette.mode === 'dark'
                  ? `rgba(25, 118, 210, 0.03)`
                  : `rgba(25, 118, 210, 0.02)`,
            }
          : {}),
      }}
    >
      {preset.remote_id && (
        <Chip
          icon={<CloudDownloadIcon />}
          label="云端人设"
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
          label="已共享"
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

      <CardContent sx={{ pt: 3, pb: 1, flex: 1, display: 'flex', flexDirection: 'column' }}>
        <Box
          sx={{
            display: 'flex',
            gap: 2,
            flexDirection: isGridLayout ? 'row' : isMobile && isSmall ? 'column' : 'row',
            height: '100%',
          }}
        >
          {/* 左侧头像区域 */}
          <Box
            sx={{
              width: isGridLayout ? 80 : isMobile && isSmall ? '100%' : { xs: '25%', sm: '16.66%' },
              height: isGridLayout ? 80 : 'auto',
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
                boxShadow: '0 2px 8px rgba(0,0,0,0.1)',
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
                variant={isGridLayout ? 'subtitle1' : 'h6'}
                gutterBottom
                sx={{
                  overflow: 'hidden',
                  textOverflow: 'ellipsis',
                  display: '-webkit-box',
                  WebkitLineClamp: 1,
                  WebkitBoxOrient: 'vertical',
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
                  lineHeight: '1.2',
                  maxHeight: expanded ? 'none' : isGridLayout ? '2.4em' : '4.5em',
                  overflow: 'hidden',
                  textOverflow: 'ellipsis',
                  display: '-webkit-box',
                  WebkitLineClamp: isGridLayout ? 2 : 3,
                  WebkitBoxOrient: 'vertical',
                }}
              >
                {preset.description || '无描述'}
              </Typography>
            </Box>

            <Box sx={{ display: 'flex', flexDirection: 'column', justifyContent: 'space-between' }}>
              {/* 标签栏 */}
              {(tagsArray.length > 0 || !isGridLayout) && (
                <Box
                  sx={{
                    display: 'flex',
                    gap: 0.5,
                    flexWrap: 'wrap',
                    pb: 3,
                    maxHeight: isGridLayout ? '20px' : 'auto',
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
                          ...(theme.palette.mode === 'dark'
                            ? CHIP_VARIANTS.getCustomColorChip('rgba(255,255,255,0.7)', isSmall)
                            : CHIP_VARIANTS.getCustomColorChip('rgba(0,0,0,0.7)', isSmall)),
                        }}
                      />
                    ))
                  ) : !isGridLayout ? (
                    <Typography variant="caption" color="text.disabled">
                      无标签
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
                    作者: {preset.author || '未知'}
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

      <CardActions sx={{ justifyContent: 'space-between', pt: 0, mt: 'auto' }}>
        <Button
          size="small"
          onClick={onExpand}
          endIcon={expanded ? <ExpandLessIcon /> : <ExpandMoreIcon />}
          sx={{
            textTransform: 'none',
            fontWeight: 'normal',
            '&:hover': {
              backgroundColor: 'transparent',
              color: theme => theme.palette.primary.main,
            },
          }}
        >
          {expanded ? '收起' : '展开'}
        </Button>
        <Box>
          <Tooltip title="编辑">
            <IconButton size="small" color="primary" onClick={onEdit}>
              <EditIcon />
            </IconButton>
          </Tooltip>
          {preset.remote_id && preset.on_shared && (
            <Tooltip title="同步云端最新数据">
              <IconButton
                size="small"
                color="primary"
                onClick={async () => {
                  setSyncLoading(true)
                  try {
                    await onSync(preset.id)
                  } catch (error) {
                    console.error('同步按钮错误:', error)
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
          <Tooltip title="删除">
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
        TransitionComponent={Fade}
        transitionDuration={{ enter: 300, exit: 200 }}
        PaperProps={{
          elevation: 8,
          sx: {
            borderRadius: BORDER_RADIUS.DEFAULT,
            background: UI_STYLES.GRADIENTS.CARD.DEFAULT,
            backdropFilter: UI_STYLES.CARD_LAYOUT.BACKDROP_FILTER,
            border: UI_STYLES.BORDERS.CARD.DEFAULT,
            overflow: 'hidden',
            maxWidth: isMobile ? '95%' : '800px',
            maxHeight: '80vh',
          },
        }}
      >
        <DialogTitle sx={{ display: 'flex', alignItems: 'center', gap: 1, p: 2 }}>
          <Avatar
            src={preset.avatar}
            sx={{ width: 36, height: 36, borderRadius: 1 }}
            variant="rounded"
          />
          <Typography variant="h6" component="div" sx={{ flex: 1 }}>
            {preset.title}
          </Typography>
          <IconButton size="small" onClick={onExpand} edge="end">
            <CloseIcon />
          </IconButton>
        </DialogTitle>
        <Divider />
        <DialogContent>
          {loading ? (
            <Box sx={{ display: 'flex', justifyContent: 'center', py: 4 }}>
              <CircularProgress />
            </Box>
          ) : detailData ? (
            <Grid container spacing={2}>
              <Grid item xs={12}>
                <Typography variant="subtitle2" gutterBottom>
                  人设内容:
                </Typography>
                <Typography
                  variant="body2"
                  sx={{
                    whiteSpace: 'pre-wrap',
                    bgcolor: 'background.paper',
                    p: 2,
                    borderRadius: 1,
                    border: '1px solid',
                    borderColor: 'divider',
                    maxHeight: '50vh',
                    overflow: 'auto',
                  }}
                >
                  {detailData.content || '无内容'}
                </Typography>
              </Grid>
              <Grid item xs={12}>
                <Box sx={{ display: 'flex', justifyContent: 'space-between', mt: 1 }}>
                  <Typography variant="caption" color="text.secondary">
                    作者: {preset.author || '未知'}
                  </Typography>
                  <Typography variant="caption" color="text.secondary">
                    最近更新: {formatLastActiveTime(new Date(preset.update_time).getTime() / 1000)}
                  </Typography>
                </Box>
              </Grid>
            </Grid>
          ) : (
            <Typography color="text.secondary">加载失败</Typography>
          )}
        </DialogContent>
      </Dialog>

      {/* 共享对话框 */}
      <Dialog open={showShareDialog} onClose={() => setShowShareDialog(false)}>
        <DialogTitle>共享人设到云端</DialogTitle>
        <DialogContent>
          <Typography paragraph>
            确定要将此人设共享到云端平台吗？共享后将可被其他实例下载使用。
          </Typography>
          <Alert severity="info" sx={{ mb: 2 }}>
            共享后，其他人可以下载和使用您的人设。
          </Alert>
          <Box sx={{ display: 'flex', flexDirection: 'column' }}>
            <FormControlLabel
              control={<Checkbox checked={isSfw} onChange={e => setIsSfw(e.target.checked)} />}
              label="我确认这是符合社区内容规则的安全内容(SFW)"
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
                  我已阅读并接受{' '}
                  <Link
                    href="https://community.nekro.ai/terms"
                    target="_blank"
                    underline="hover"
                    sx={{ ml: 0.5 }}
                  >
                    《NekroAI 社区资源共享协议》
                  </Link>
                </Box>
              }
            />
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setShowShareDialog(false)} disabled={shareLoading}>
            取消
          </Button>
          <Button
            onClick={handleShareToCloud}
            color="primary"
            disabled={shareLoading || !isSfw || !agreeToTerms}
          >
            {shareLoading ? <CircularProgress size={24} /> : '共享'}
          </Button>
        </DialogActions>
      </Dialog>

      {/* 撤回共享对话框 */}
      <Dialog open={showUnshareDialog} onClose={() => setShowUnshareDialog(false)}>
        <DialogTitle>撤回共享</DialogTitle>
        <DialogContent>
          <Alert severity="warning" sx={{ mb: 2 }}>
            撤回共享将从云端删除此人设，其他实例可能无法再下载此人设。
          </Alert>
          <Typography>确定要撤回共享吗？</Typography>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setShowUnshareDialog(false)} disabled={shareLoading}>
            取消
          </Button>
          <Button onClick={handleUnshare} color="warning" disabled={shareLoading}>
            {shareLoading ? <CircularProgress size={24} /> : '撤回共享'}
          </Button>
        </DialogActions>
      </Dialog>

      {/* 同步云端对话框 */}
      <Dialog open={showSyncToCloudDialog} onClose={() => setShowSyncToCloudDialog(false)}>
        <DialogTitle>同步更新到云端</DialogTitle>
        <DialogContent>
          <Typography paragraph>
            确定要将本地修改同步到云端平台吗？这将覆盖云端的当前版本。
          </Typography>
          <Alert severity="info" sx={{ mb: 2 }}>
            同步将用本地版本覆盖云端版本。
          </Alert>
          <Box sx={{ display: 'flex', flexDirection: 'column' }}>
            <FormControlLabel
              control={<Checkbox checked={isSfw} onChange={e => setIsSfw(e.target.checked)} />}
              label="我确认这是符合社区内容规则的安全内容(SFW)"
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
                  我已阅读并接受{' '}
                  <Link
                    href="https://community.nekro.ai/terms"
                    target="_blank"
                    underline="hover"
                    sx={{ ml: 0.5 }}
                  >
                    《NekroAI 社区资源共享协议》
                  </Link>
                </Box>
              }
            />
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setShowSyncToCloudDialog(false)} disabled={shareLoading}>
            取消
          </Button>
          <Button
            onClick={handleSyncToCloud}
            color="primary"
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
  const [expandedId, setExpandedId] = useState<number | null>(null)
  const [editDialog, setEditDialog] = useState(false)
  const [editingPreset, setEditingPreset] = useState<PresetDetail | undefined>(undefined)
  const [confirmDelete, setConfirmDelete] = useState<number | null>(null)
  const { enqueueSnackbar } = useSnackbar()
  const [errorMessage, setErrorMessage] = useState<{
    type: 'success' | 'error' | 'info' | 'warning'
    content: string
  } | null>(null)
  const [refreshingShared, setRefreshingShared] = useState(false)
  const theme = useTheme()
  const isMobile = useMediaQuery(theme.breakpoints.down('md'))
  const isSmall = useMediaQuery(theme.breakpoints.down('sm'))
  // 添加宽屏检测
  const isLargeScreen = useMediaQuery(theme.breakpoints.up('lg'))
  const isExtraLargeScreen = useMediaQuery(theme.breakpoints.up('xl'))

  // 添加全局错误处理函数
  const showError = useCallback((message: string) => {
    console.error(message)
    setErrorMessage({ type: 'error', content: message })
    setTimeout(() => setErrorMessage(null), 5000) // 5秒后自动关闭
  }, [])

  // 添加全局成功处理函数
  const showSuccess = useCallback((message: string) => {
    console.log(message)
    setErrorMessage({ type: 'success', content: message })
    setTimeout(() => setErrorMessage(null), 2000) // 2秒后自动关闭
  }, [])

  const fetchData = useCallback(async () => {
    try {
      setLoading(true)
      const data = await presetsApi.getList({
        page,
        page_size: pageSize,
        search: search || undefined,
      })
      setPresets(data.items)
    } catch (error) {
      console.error('获取人设列表失败', error)
      enqueueSnackbar('获取人设列表失败', { variant: 'error', autoHideDuration: 5000 })
      showError('获取人设列表失败')
    } finally {
      setLoading(false)
    }
  }, [page, pageSize, search, enqueueSnackbar, showError])

  useEffect(() => {
    fetchData()
  }, [fetchData])

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault()
    setPage(1)
    fetchData()
  }

  const handleExpandClick = (id: number) => {
    setExpandedId(expandedId === id ? null : id)
  }

  const handleEditClick = async (preset: Preset) => {
    try {
      enqueueSnackbar('正在加载人设详情...', { variant: 'info', autoHideDuration: 2000 })
      // 加载详细数据
      const detailData = await presetsApi.getDetail(preset.id)
      setEditingPreset(detailData)
      setEditDialog(true)
    } catch (error) {
      console.error('获取人设详情失败', error)
      enqueueSnackbar('获取人设详情失败', { variant: 'error', autoHideDuration: 5000 })
      showError('获取人设详情失败')
    }
  }

  const handleSave = async (data: PresetFormData) => {
    console.log('主页面handleSave被调用，数据:', data)
    try {
      if (editingPreset) {
        console.log('更新现有人设:', editingPreset.id)
        enqueueSnackbar('正在更新人设...', { variant: 'info', autoHideDuration: 2000 })
        await presetsApi.update(editingPreset.id, data)
        enqueueSnackbar('更新成功', { variant: 'success', autoHideDuration: 3000 })
      } else {
        console.log('创建新人设')
        enqueueSnackbar('正在创建人设...', { variant: 'info', autoHideDuration: 2000 })
        const result = await presetsApi.create(data)
        console.log('创建人设API响应:', result)
        enqueueSnackbar('创建成功', { variant: 'success', autoHideDuration: 3000 })
      }
      fetchData()
    } catch (error) {
      console.error('保存失败', error)
      const errorMessage = error instanceof Error ? error.message : String(error)
      enqueueSnackbar(`保存失败: ${errorMessage}`, { variant: 'error', autoHideDuration: 10000 })
      showError(`保存失败: ${errorMessage}`)
      throw error // 传递错误以便上层组件处理
    }
  }

  const handleDeleteClick = (id: number) => {
    setConfirmDelete(id)
  }

  const handleDeleteConfirm = async () => {
    if (confirmDelete === null) return

    try {
      enqueueSnackbar('正在删除人设...', { variant: 'info', autoHideDuration: 2000 })
      await presetsApi.delete(confirmDelete)
      enqueueSnackbar('删除成功', { variant: 'success', autoHideDuration: 3000 })
      fetchData()
      if (expandedId === confirmDelete) {
        setExpandedId(null)
      }
    } catch (error) {
      console.error('删除失败', error)
      const errorMessage = error instanceof Error ? error.message : String(error)
      enqueueSnackbar(`删除失败: ${errorMessage}`, { variant: 'error', autoHideDuration: 10000 })
      showError(`删除失败: ${errorMessage}`)
    } finally {
      setConfirmDelete(null)
    }
  }

  const handleSyncClick = async (id: number): Promise<void> => {
    try {
      const response = await presetsApi.sync(id)
      if (response.code === 200) {
        showSuccess('同步成功')
        if (response.msg) {
          showSuccess(response.msg)
        }
        // 强制刷新数据
        await fetchData()
        // 如果当前有展开的详情，也需要刷新
        if (expandedId === id) {
          setExpandedId(null) // 先收起
          setTimeout(() => setExpandedId(id), 100) // 再展开以刷新详情
        }
      } else {
        const errorMsg = response.msg || '未知错误'
        showError(`同步失败: ${errorMsg}`)
        throw new Error(errorMsg)
      }
    } catch (error) {
      console.error('同步失败', error)
      const errorMessage = error instanceof Error ? error.message : String(error)
      showError(`同步失败: ${errorMessage}`)
      throw error
    }
  }

  // 添加刷新共享状态的函数
  const handleRefreshSharedStatus = async () => {
    try {
      setRefreshingShared(true)
      enqueueSnackbar('正在刷新共享状态...', { variant: 'info', autoHideDuration: 2000 })
      const response = await presetsApi.refreshSharedStatus()
      if (response.code === 200) {
        enqueueSnackbar(response.msg || '刷新共享状态成功', {
          variant: 'success',
          autoHideDuration: 3000,
        })
        if (response.data) {
          enqueueSnackbar(
            `更新了${response.data.updated_count}个人设的共享状态，云端共有${response.data.total_cloud_presets}个人设`,
            { variant: 'info', autoHideDuration: 5000 }
          )
        }
        // 刷新人设列表
        await fetchData()
      } else {
        enqueueSnackbar(`刷新失败: ${response.msg}`, { variant: 'error', autoHideDuration: 10000 })
        showError(`刷新失败: ${response.msg}`)
      }
    } catch (error) {
      console.error('刷新共享状态失败', error)
      const errorMessage = error instanceof Error ? error.message : String(error)
      enqueueSnackbar(`刷新失败: ${errorMessage}`, { variant: 'error', autoHideDuration: 10000 })
      showError(`刷新失败: ${errorMessage}`)
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
            size={isSmall ? 'small' : 'medium'}
            placeholder="搜索人设"
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
              '刷新状态'
            ) : (
              '刷新共享状态'
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
            创建人设
          </Button>
        </Box>
      </Box>

      {loading && presets.length === 0 ? (
        <Box sx={{ display: 'flex', justifyContent: 'center', py: 8 }}>
          <CircularProgress />
        </Box>
      ) : presets.length > 0 ? (
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
            没有找到人设
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
            创建新人设
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
      <Dialog open={confirmDelete !== null} onClose={() => setConfirmDelete(null)}>
        <DialogTitle>确认删除</DialogTitle>
        <DialogContent>
          <Typography>确定要删除这个人设吗？此操作不可恢复。</Typography>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setConfirmDelete(null)}>取消</Button>
          <Button onClick={handleDeleteConfirm} color="error">
            确认删除
          </Button>
        </DialogActions>
      </Dialog>

      {/* 全局错误提示 */}
      <Snackbar
        open={!!errorMessage}
        autoHideDuration={5000}
        onClose={() => setErrorMessage(null)}
        anchorOrigin={{ vertical: 'top', horizontal: 'center' }}
      >
        <Alert
          onClose={() => setErrorMessage(null)}
          severity={errorMessage?.type || 'error'}
          variant="filled"
          sx={{ width: '100%' }}
        >
          {errorMessage?.content}
        </Alert>
      </Snackbar>
    </Box>
  )
}
