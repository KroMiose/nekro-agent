import { useState, useEffect, useCallback } from 'react'
import {
  Box,
  Typography,
  Alert,
  Grid,
  Card,
  CardContent,
  CardActions,
  Button,
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
  Switch,
  FormControlLabel,
  FormControl,
  MenuItem,
  Checkbox,
  Link,
  Snackbar,
} from '@mui/material'
import {
  Search as SearchIcon,
  CloudDownload as CloudDownloadIcon,
  Done as DoneIcon,
  Info as InfoIcon,
  Update as UpdateIcon,
  GitHub as GitHubIcon,
  Link as LinkIcon,
  Code as CodeIcon,
  Add as AddIcon,
  Extension as ExtensionIcon,
  RemoveCircle as RemoveCircleIcon,
} from '@mui/icons-material'
import {
  pluginsMarketApi,
  CloudPlugin,
  PluginCreateRequest,
} from '../../services/api/cloud/plugins_market'
import { formatLastActiveTime } from '../../utils/time'
import PaginationStyled from '../../components/common/PaginationStyled'

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

// 插件卡片组件
const PluginCard = ({
  plugin,
  onDownload,
  onUpdate,
  onUnpublish,
  onShowDetail,
}: {
  plugin: CloudPlugin
  onDownload: () => void
  onUpdate: () => void
  onUnpublish?: () => void
  onShowDetail: () => void
}) => {
  const theme = useTheme()
  const [iconError, setIconError] = useState(false)

  return (
    <Card
      sx={{
        display: 'flex',
        flexDirection: 'column',
        height: '100%',
        transition: 'all 0.3s',
        borderRadius: 2,
        overflow: 'hidden',
        '&:hover': {
          boxShadow: theme.shadows[6],
          transform: 'translateY(-2px)',
        },
        position: 'relative',
      }}
    >
      <CardContent sx={{ flexGrow: 1, p: 2.5, pb: 1 }}>
        <Box
          sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', mb: 1 }}
        >
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5, width: '100%' }}>
            {/* 插件图标 */}
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
                sx={{
                  fontWeight: 600,
                  fontSize: '1.1rem',
                  lineHeight: 1.4,
                  overflow: 'hidden',
                  textOverflow: 'ellipsis',
                  whiteSpace: 'nowrap',
                }}
              >
                {plugin.name}
              </Typography>
            </Box>
          </Box>

          {plugin.hasWebhook && (
            <Chip
              size="small"
              label="WebHook"
              color="primary"
              variant="outlined"
              sx={{ height: 24, fontSize: '0.7rem', ml: 1, flexShrink: 0 }}
            />
          )}
        </Box>

        <Typography
          variant="body2"
          color="text.secondary"
          sx={{
            my: 1.5,
            overflow: 'hidden',
            textOverflow: 'ellipsis',
            display: '-webkit-box',
            WebkitLineClamp: 3,
            WebkitBoxOrient: 'vertical',
          }}
        >
          {plugin.description || '无描述'}
        </Typography>

        <Box sx={{ display: 'flex', justifyContent: 'space-between', mt: 'auto' }}>
          <Typography variant="caption" color="text.secondary">
            作者: {plugin.author || '未知'}
          </Typography>
          {plugin.version && (
            <Typography variant="caption" color="primary">
              版本: {plugin.version}
            </Typography>
          )}
        </Box>

        <Box sx={{ mt: 1 }}>
          {plugin.licenseType && (
            <Chip
              label={plugin.licenseType}
              size="small"
              sx={{
                height: 24,
                fontSize: '0.75rem',
                mr: 0.75,
                bgcolor: theme =>
                  theme.palette.mode === 'dark' ? 'rgba(255,255,255,0.12)' : 'rgba(0,0,0,0.08)',
              }}
            />
          )}
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
          bgcolor: theme =>
            theme.palette.mode === 'dark' ? 'rgba(255,255,255,0.03)' : 'rgba(0,0,0,0.02)',
          borderTop: '1px solid',
          borderColor: 'divider',
        }}
      >
        <Box sx={{ display: 'flex', gap: 0.5 }}>
          <Button size="small" variant="text" startIcon={<InfoIcon />} onClick={onShowDetail}>
            详情
          </Button>

          {onUnpublish && (
            <Button
              size="small"
              variant="text"
              startIcon={<RemoveCircleIcon />}
              onClick={onUnpublish}
              color="error"
            >
              下架
            </Button>
          )}
        </Box>

        {plugin.is_local ? (
          plugin.can_update ? (
            <Button
              size="small"
              variant="contained"
              startIcon={<UpdateIcon />}
              onClick={onUpdate}
              color="primary"
            >
              更新
            </Button>
          ) : (
            <Button size="small" variant="text" startIcon={<DoneIcon />} disabled>
              已获取
            </Button>
          )
        ) : (
          <Button
            size="small"
            variant="contained"
            startIcon={<CloudDownloadIcon />}
            onClick={onDownload}
            color="primary"
          >
            获取
          </Button>
        )}
      </CardActions>
    </Card>
  )
}

// 详情对话框组件
const PluginDetailDialog = ({
  open,
  onClose,
  plugin,
  onUnpublish,
  onDownload,
  onUpdate,
}: {
  open: boolean
  onClose: () => void
  plugin: CloudPlugin | null
  onUnpublish?: () => void
  onDownload?: () => void
  onUpdate?: () => void
}) => {
  const theme = useTheme()
  const [iconError, setIconError] = useState(false)

  if (!plugin) return null

  return (
    <Dialog
      open={open}
      onClose={onClose}
      maxWidth="md"
      fullWidth
      scroll="paper"
      PaperProps={{
        sx: {
          borderRadius: 2,
          overflow: 'hidden',
        },
      }}
    >
      <DialogTitle
        sx={{
          px: 3,
          py: 2,
          background: theme.palette.mode === 'dark' ? 'rgba(255,255,255,0.03)' : 'rgba(0,0,0,0.02)',
          borderBottom: '1px solid',
          borderColor: 'divider',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
        }}
      >
        <Typography variant="h6">插件详情：{plugin.name}</Typography>
        {plugin.isOwner && (
          <IconButton color="error" onClick={onUnpublish} size="small" title="下架插件">
            <RemoveCircleIcon />
          </IconButton>
        )}
      </DialogTitle>
      <DialogContent dividers sx={{ p: 3 }}>
        <Grid container spacing={3}>
          <Grid item xs={12} sm={4} md={3}>
            <Box sx={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 2.5 }}>
              {/* 插件图标 */}
              <Box
                sx={{
                  width: '100%',
                  aspectRatio: '1',
                  borderRadius: 2,
                  overflow: 'hidden',
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
                      fontSize: 64,
                      opacity: 0.7,
                      color: theme => theme.palette.primary.main,
                    }}
                  />
                )}
              </Box>
            </Box>
          </Grid>

          <Grid item xs={12} sm={8} md={9}>
            <Typography variant="h5" gutterBottom fontWeight={600}>
              {plugin.name}{' '}
              <Typography component="span" color="text.secondary">
                ({plugin.moduleName})
              </Typography>
            </Typography>

            <Box sx={{ mb: 3 }}>
              <Typography variant="subtitle1" color="text.secondary" gutterBottom>
                作者: {plugin.author || '未知'}
                {plugin.version && (
                  <Typography component="span" ml={2} color="primary.main">
                    版本: {plugin.version}
                  </Typography>
                )}
              </Typography>
              <Typography
                variant="body1"
                paragraph
                sx={{
                  backgroundColor:
                    theme.palette.mode === 'dark' ? 'rgba(255,255,255,0.03)' : 'rgba(0,0,0,0.02)',
                  p: 2,
                  borderRadius: 1,
                  borderLeft: '4px solid',
                  borderColor: 'primary.main',
                  mt: 1,
                }}
              >
                {plugin.description || '无描述'}
              </Typography>
              <Box sx={{ display: 'flex', gap: 3, flexWrap: 'wrap', mb: 2, mt: 3 }}>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                  <Typography variant="body2" color="text.secondary" fontWeight={500}>
                    创建时间:
                  </Typography>
                  <Typography variant="body2">
                    {formatLastActiveTime(new Date(plugin.createdAt).getTime() / 1000)}
                  </Typography>
                </Box>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                  <Typography variant="body2" color="text.secondary" fontWeight={500}>
                    更新时间:
                  </Typography>
                  <Typography variant="body2">
                    {formatLastActiveTime(new Date(plugin.updatedAt).getTime() / 1000)}
                  </Typography>
                </Box>
              </Box>
            </Box>

            <Divider sx={{ mb: 2.5 }} />

            <Box sx={{ mb: 3 }}>
              <Typography variant="h6" gutterBottom>
                链接与信息
              </Typography>
              <Grid container spacing={2}>
                {plugin.homepageUrl && (
                  <Grid item xs={12} sm={6}>
                    <Button
                      fullWidth
                      variant="outlined"
                      startIcon={<LinkIcon />}
                      onClick={() => window.open(plugin.homepageUrl, '_blank')}
                      sx={{ justifyContent: 'flex-start', textTransform: 'none' }}
                    >
                      插件主页
                    </Button>
                  </Grid>
                )}
                {plugin.githubUrl && (
                  <Grid item xs={12} sm={6}>
                    <Button
                      fullWidth
                      variant="outlined"
                      startIcon={<GitHubIcon />}
                      onClick={() => window.open(plugin.githubUrl, '_blank')}
                      sx={{ justifyContent: 'flex-start', textTransform: 'none' }}
                    >
                      GitHub 仓库
                    </Button>
                  </Grid>
                )}
                {plugin.cloneUrl && (
                  <Grid item xs={12} sm={6}>
                    <Button
                      fullWidth
                      variant="outlined"
                      startIcon={<CodeIcon />}
                      onClick={() => navigator.clipboard.writeText(plugin.cloneUrl)}
                      sx={{ justifyContent: 'flex-start', textTransform: 'none' }}
                    >
                      复制克隆链接
                    </Button>
                  </Grid>
                )}
                {plugin.licenseType && (
                  <Grid item xs={12} sm={6}>
                    <Button
                      fullWidth
                      variant="outlined"
                      disabled
                      sx={{ justifyContent: 'flex-start', textTransform: 'none' }}
                    >
                      许可证: {plugin.licenseType}
                    </Button>
                  </Grid>
                )}
              </Grid>
            </Box>

            <Box sx={{ mt: 3 }}>
              <Typography color="text.secondary" variant="body2">
                {plugin.hasWebhook ? '✅ 此插件使用 Webhook 支持' : '❌ 此插件不使用 Webhook'}
              </Typography>
            </Box>
          </Grid>
        </Grid>
      </DialogContent>
      <DialogActions sx={{ px: 3, py: 2, display: 'flex', justifyContent: 'space-between' }}>
        <Button variant="outlined" onClick={onClose}>
          关闭
        </Button>

        <Box sx={{ display: 'flex', gap: 1 }}>
          {plugin.is_local ? (
            plugin.can_update ? (
              <Button
                variant="contained"
                startIcon={<UpdateIcon />}
                color="primary"
                onClick={onUpdate}
              >
                更新插件
              </Button>
            ) : (
              <Button variant="contained" disabled startIcon={<DoneIcon />}>
                已获取
              </Button>
            )
          ) : (
            <Button
              variant="contained"
              startIcon={<CloudDownloadIcon />}
              color="primary"
              onClick={onDownload}
            >
              获取插件
            </Button>
          )}
        </Box>
      </DialogActions>
    </Dialog>
  )
}

// 创建插件表单对话框
const CreatePluginDialog = ({
  open,
  onClose,
  onSubmit,
  isSubmitting,
}: {
  open: boolean
  onClose: () => void
  onSubmit: (data: PluginCreateRequest) => void
  isSubmitting: boolean
}) => {
  const [formData, setFormData] = useState<PluginCreateRequest>({
    name: '',
    moduleName: '',
    description: '',
    author: '',
    hasWebhook: false,
    homepageUrl: '',
    githubUrl: '',
    cloneUrl: '',
    licenseType: 'MIT',
    isSfw: true,
    icon: '', // 添加图标字段
  })
  const [errors, setErrors] = useState<Record<string, string>>({})
  const [iconPreview, setIconPreview] = useState<string | null>(null)
  const [agreeToTerms, setAgreeToTerms] = useState(false)
  const [confirmSafeContent, setConfirmSafeContent] = useState(false)

  // 重置表单
  useEffect(() => {
    if (open) {
      setFormData({
        name: '',
        moduleName: '',
        description: '',
        author: '',
        hasWebhook: false,
        homepageUrl: '',
        githubUrl: '',
        cloneUrl: '',
        licenseType: 'MIT',
        isSfw: true,
        icon: '',
      })
      setErrors({})
      setIconPreview(null)
      setAgreeToTerms(false)
      setConfirmSafeContent(false)
    }
  }, [open])

  // 处理输入变化
  const handleChange = (
    e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | { name?: string; value: unknown }>
  ) => {
    const { name, value } = e.target
    if (name) {
      setFormData(prev => ({ ...prev, [name]: value }))

      // GitHub URL自动填充Git克隆URL的逻辑
      if (name === 'githubUrl' && typeof value === 'string') {
        const githubUrl = value.trim()
        // 如果Git克隆URL为空或等于旧的GitHub URL + .git，则自动填充
        if (!formData.cloneUrl || formData.cloneUrl === formData.githubUrl + '.git') {
          if (githubUrl) {
            setFormData(prev => ({ ...prev, cloneUrl: githubUrl + '.git' }))

            // 当自动填充克隆URL时，同时清除克隆URL的错误
            if (errors.cloneUrl) {
              setErrors(prev => {
                const newErrors = { ...prev }
                delete newErrors.cloneUrl
                return newErrors
              })
            }
          } else {
            setFormData(prev => ({ ...prev, cloneUrl: '' }))
          }
        }
      }

      // 清除错误
      if (errors[name]) {
        setErrors(prev => {
          const newErrors = { ...prev }
          delete newErrors[name]
          return newErrors
        })
      }
    }
  }

  // 处理切换变化
  const handleSwitchChange = (name: string) => (e: React.ChangeEvent<HTMLInputElement>) => {
    setFormData(prev => ({ ...prev, [name]: e.target.checked }))
  }

  // 处理SFW确认变更
  const handleSfwChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setConfirmSafeContent(e.target.checked)
    // 同时更新formData中的isSfw值
    setFormData(prev => ({ ...prev, isSfw: e.target.checked }))
  }

  // 验证表单
  const validateForm = (): boolean => {
    const newErrors: Record<string, string> = {}

    if (!formData.name.trim()) {
      newErrors.name = '插件名称不能为空'
    }

    if (!formData.moduleName.trim()) {
      newErrors.moduleName = '模块名不能为空'
    } else if (!/^[a-zA-Z0-9_]+$/.test(formData.moduleName)) {
      newErrors.moduleName = '模块名只能包含英文、数字和下划线，并且在插件市场唯一'
    }

    if (!formData.description.trim()) {
      newErrors.description = '插件描述不能为空'
    }

    if (!formData.author.trim()) {
      newErrors.author = '作者不能为空'
    }

    if (!formData.githubUrl) {
      newErrors.githubUrl = 'GitHub 仓库 URL 不能为空'
    } else if (!/^https?:\/\/github\.com\//.test(formData.githubUrl)) {
      newErrors.githubUrl = 'GitHub URL 格式不正确'
    }

    if (!formData.cloneUrl) {
      newErrors.cloneUrl = 'Git 克隆 URL 不能为空'
    } else if (!/\.git$/.test(formData.cloneUrl)) {
      newErrors.cloneUrl = '克隆URL格式不正确，应以.git结尾'
    }

    setErrors(newErrors)
    return Object.keys(newErrors).length === 0
  }

  // 处理提交
  const handleSubmit = () => {
    if (validateForm()) {
      onSubmit(formData)
    }
  }

  // 处理图标上传
  const handleIconUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return

    if (file.size > 10 * 1024 * 1024) {
      setErrors(prev => ({
        ...prev,
        icon: '图片太大啦，最大支持10MB～',
      }))
      return
    }

    try {
      const base64Icon = await imageToBase64(file)
      setFormData(prev => ({ ...prev, icon: base64Icon }))
      setIconPreview(base64Icon)

      // 清除错误
      if (errors.icon) {
        setErrors(prev => {
          const newErrors = { ...prev }
          delete newErrors.icon
          return newErrors
        })
      }
    } catch (error) {
      console.error('图标转换失败:', error)
      setErrors(prev => ({
        ...prev,
        icon: '图标处理失败，请重试',
      }))
    }
  }

  // 图片转Base64函数
  const imageToBase64 = (file: File): Promise<string> => {
    return new Promise((resolve, reject) => {
      const reader = new FileReader()
      reader.readAsDataURL(file)
      reader.onload = () => resolve(reader.result as string)
      reader.onerror = error => reject(error)
    })
  }

  return (
    <Dialog
      open={open}
      onClose={onClose}
      maxWidth="md"
      fullWidth
      PaperProps={{
        sx: {
          borderRadius: 2,
          overflow: 'hidden',
        },
      }}
    >
      <DialogTitle sx={{ borderBottom: '1px solid', borderColor: 'divider' }}>
        发布新插件
      </DialogTitle>
      <DialogContent sx={{ pt: 3, mt: 3 }}>
        <Grid container spacing={3}>
          {/* 基本信息（左）和图标上传（右）并排布局 */}
          <Grid item xs={12} sm={6}>
            <Typography variant="subtitle1" gutterBottom fontWeight={500} sx={{ mb: 2 }}>
              基本信息
            </Typography>

            <TextField
              name="name"
              label="插件名称"
              value={formData.name}
              onChange={handleChange}
              fullWidth
              required
              error={!!errors.name}
              helperText={errors.name}
              disabled={isSubmitting}
              sx={{ mb: 2 }}
            />

            <TextField
              name="moduleName"
              label="模块名"
              value={formData.moduleName}
              onChange={handleChange}
              fullWidth
              required
              error={!!errors.moduleName}
              helperText={errors.moduleName || '模块名只能包含英文、数字和下划线，并且在插件市场唯一'}
              disabled={isSubmitting}
            />
          </Grid>

          {/* 插件图标上传 */}
          <Grid item xs={12} sm={6}>
            <Typography variant="subtitle1" gutterBottom fontWeight={500} sx={{ mb: 2 }}>
              插件图标
            </Typography>

            <Box
              sx={{
                display: 'flex',
                alignItems: 'center',
                gap: 2,
              }}
            >
              <Box
                sx={{
                  width: 100,
                  height: 100,
                  borderRadius: 2,
                  border: '1px solid',
                  borderColor: 'divider',
                  overflow: 'hidden',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  backgroundColor: theme =>
                    theme.palette.mode === 'dark' ? 'rgba(255,255,255,0.05)' : 'rgba(0,0,0,0.02)',
                }}
              >
                {iconPreview ? (
                  <img
                    src={iconPreview}
                    alt="插件图标预览"
                    style={{ width: '100%', height: '100%', objectFit: 'cover' }}
                  />
                ) : (
                  <ExtensionIcon
                    sx={{
                      fontSize: 48,
                      opacity: 0.7,
                      color: theme => theme.palette.primary.main,
                    }}
                  />
                )}
              </Box>
              <Box>
                <Button variant="outlined" component="label" disabled={isSubmitting} sx={{ mb: 1 }}>
                  选择图标
                  <input
                    type="file"
                    hidden
                    accept="image/*"
                    onChange={handleIconUpload}
                    disabled={isSubmitting}
                  />
                </Button>
                <Typography variant="caption" color="text.secondary" display="block">
                  建议尺寸: 128x128像素
                  <br />
                  支持格式: PNG, JPG, GIF
                  <br />
                  大小限制: 10MB (自动压缩至 500 KB)
                </Typography>
                {errors.icon && (
                  <Typography variant="caption" color="error" sx={{ mt: 1 }}>
                    {errors.icon}
                  </Typography>
                )}
              </Box>
            </Box>
          </Grid>

          <Grid item xs={12}>
            <TextField
              name="description"
              label="插件描述"
              value={formData.description}
              onChange={handleChange}
              fullWidth
              required
              multiline
              rows={3}
              error={!!errors.description}
              helperText={errors.description}
              disabled={isSubmitting}
            />
          </Grid>
          <Grid item xs={12} sm={6}>
            <TextField
              name="author"
              label="作者"
              value={formData.author}
              onChange={handleChange}
              fullWidth
              required
              error={!!errors.author}
              helperText={errors.author}
              disabled={isSubmitting}
            />
          </Grid>
          <Grid item xs={12} sm={6}>
            <FormControl fullWidth disabled={isSubmitting}>
              <TextField
                select
                name="licenseType"
                label="许可证类型"
                value={formData.licenseType}
                onChange={handleChange}
                fullWidth
              >
                <MenuItem value="MIT">MIT</MenuItem>
                <MenuItem value="Apache-2.0">Apache-2.0</MenuItem>
                <MenuItem value="GPL-3.0">GPL-3.0</MenuItem>
                <MenuItem value="BSD-3-Clause">BSD-3-Clause</MenuItem>
                <MenuItem value="UNLICENSED">UNLICENSED</MenuItem>
                <MenuItem value="CUSTOM">自定义（参考描述）</MenuItem>
              </TextField>
            </FormControl>
          </Grid>
          <Grid item xs={12}>
            <TextField
              name="githubUrl"
              label="GitHub 仓库URL"
              value={formData.githubUrl}
              onChange={handleChange}
              fullWidth
              required
              error={!!errors.githubUrl}
              helperText={errors.githubUrl}
              placeholder="https://github.com/username/repo"
              disabled={isSubmitting}
            />
          </Grid>
          <Grid item xs={12}>
            <TextField
              name="cloneUrl"
              label="Git 克隆URL"
              value={formData.cloneUrl}
              onChange={handleChange}
              fullWidth
              required
              error={!!errors.cloneUrl}
              helperText={errors.cloneUrl}
              placeholder="https://github.com/username/repo.git"
              disabled={isSubmitting}
            />
          </Grid>
          <Grid item xs={12} sm={6}>
            <FormControlLabel
              control={
                <Switch
                  checked={formData.hasWebhook}
                  onChange={handleSwitchChange('hasWebhook')}
                  color="primary"
                  disabled={isSubmitting}
                />
              }
              label="含有 Webhook 触发功能"
            />
          </Grid>

          {/* 分割线和确认选项 */}
          <Grid item xs={12}>
            <Divider sx={{ my: 2 }} />
            <Typography variant="subtitle1" color="text.secondary" gutterBottom>
              发布确认
            </Typography>
          </Grid>

          <Grid item xs={12}>
            <FormControlLabel
              control={
                <Checkbox
                  checked={confirmSafeContent}
                  onChange={handleSfwChange}
                  disabled={isSubmitting}
                />
              }
              label="我确认这是符合社区内容规则的安全内容(SFW)"
            />
          </Grid>

          <Grid item xs={12}>
            <FormControlLabel
              control={
                <Checkbox
                  checked={agreeToTerms}
                  onChange={e => setAgreeToTerms(e.target.checked)}
                  disabled={isSubmitting}
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
          </Grid>
        </Grid>
      </DialogContent>
      <DialogActions sx={{ px: 3, py: 2, borderTop: '1px solid', borderColor: 'divider' }}>
        <Button onClick={onClose} disabled={isSubmitting}>
          取消
        </Button>
        <Button
          onClick={handleSubmit}
          variant="contained"
          color="primary"
          disabled={isSubmitting || !agreeToTerms || !confirmSafeContent}
          startIcon={isSubmitting ? <CircularProgress size={20} /> : <AddIcon />}
        >
          {isSubmitting ? '提交中...' : '发布插件'}
        </Button>
      </DialogActions>
    </Dialog>
  )
}

export default function PluginsMarket() {
  const [plugins, setPlugins] = useState<CloudPlugin[]>([])
  const [loading, setLoading] = useState(true)
  const [searchKeyword, setSearchKeyword] = useState('')
  const debouncedSearchKeyword = useDebounce(searchKeyword, 800)
  const [currentPage, setCurrentPage] = useState(1)
  const [totalPages, setTotalPages] = useState(1)
  const [error, setError] = useState<string | null>(null)
  const [selectedPlugin, setSelectedPlugin] = useState<CloudPlugin | null>(null)
  const [processingId, setProcessingId] = useState<string | null>(null)
  const [confirmDialog, setConfirmDialog] = useState<{
    open: boolean
    plugin: CloudPlugin | null
    action: 'download' | 'update' | 'unpublish'
  }>({
    open: false,
    plugin: null,
    action: 'download',
  })
  const [filterWebhook, setFilterWebhook] = useState(false)
  const [createDialogOpen, setCreateDialogOpen] = useState(false)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const pageSize = 12
  // 添加全局消息状态
  const [messageInfo, setMessageInfo] = useState<{
    type: 'success' | 'error' | 'info' | 'warning'
    content: string
  } | null>(null)

  // 全局错误显示函数
  const showError = useCallback((message: string) => {
    console.error(message)
    setMessageInfo({ type: 'error', content: message })
    setTimeout(() => setMessageInfo(null), 5000) // 5秒后自动关闭
  }, [])

  // 全局成功显示函数
  const showSuccess = useCallback((message: string) => {
    console.log(message)
    setMessageInfo({ type: 'success', content: message })
    setTimeout(() => setMessageInfo(null), 2000) // 2秒后自动关闭
  }, [])

  // 全局警告显示函数
  const showWarning = useCallback((message: string) => {
    console.warn(message)
    setMessageInfo({ type: 'warning', content: message })
    setTimeout(() => setMessageInfo(null), 4000) // 4秒后自动关闭
  }, [])

  const fetchPlugins = useCallback(
    async (page: number, keyword: string = '', hasWebhook: boolean | undefined = undefined) => {
      try {
        setLoading(true)
        setError(null)

        const data = await pluginsMarketApi.getList({
          page,
          page_size: pageSize,
          keyword: keyword || undefined,
          has_webhook: hasWebhook,
        })

        setPlugins(data.items)
        setTotalPages(data.totalPages)

        if (data.items.length === 0 && data.total > 0 && page > 1) {
          // 如果当前页没有数据但总数大于0，说明可能是删除后的页码问题，回到第一页
          setCurrentPage(1)
          fetchPlugins(1, keyword, hasWebhook)
        }
      } catch (error) {
        console.error('获取云端插件列表失败', error)
        setError('获取插件列表失败，请检查网络连接或联系管理员')
      } finally {
        setLoading(false)
      }
    },
    [pageSize, setCurrentPage, setLoading, setError, setPlugins, setTotalPages]
  )

  useEffect(() => {
    fetchPlugins(currentPage, debouncedSearchKeyword, filterWebhook || undefined)
  }, [fetchPlugins, currentPage, debouncedSearchKeyword, filterWebhook])

  // 监听防抖后的搜索关键词变化，重置到第一页
  useEffect(() => {
    // 当搜索关键词变化时重置页码到第一页
    setCurrentPage(1)
  }, [debouncedSearchKeyword, filterWebhook])

  const handlePageChange = (_event: React.ChangeEvent<unknown>, page: number) => {
    if (loading) return // 加载中禁止翻页
    setCurrentPage(page)
  }

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault()
    if (loading) return // 加载中禁止搜索
    setCurrentPage(1)
    fetchPlugins(1, searchKeyword, filterWebhook || undefined)
  }

  const handleSearchInputClear = () => {
    if (loading) return // 加载中禁止清空
    setSearchKeyword('')
    setCurrentPage(1)
    fetchPlugins(1, '', filterWebhook || undefined)
  }

  const handleShowDetail = (plugin: CloudPlugin) => {
    setSelectedPlugin(plugin)
  }

  const handleDownloadClick = (plugin: CloudPlugin) => {
    setConfirmDialog({ open: true, plugin, action: 'download' })
  }

  const handleUpdateClick = (plugin: CloudPlugin) => {
    setConfirmDialog({ open: true, plugin, action: 'update' })
  }

  const handleUnpublishClick = (plugin: CloudPlugin) => {
    setConfirmDialog({ open: true, plugin, action: 'unpublish' })
  }

  const handleConfirm = async () => {
    if (!confirmDialog.plugin) return

    try {
      setProcessingId(confirmDialog.plugin.id)

      let response: { code: number; msg: string; data: null } | undefined

      if (confirmDialog.action === 'download') {
        response = await pluginsMarketApi.downloadPlugin(confirmDialog.plugin.moduleName)
      } else if (confirmDialog.action === 'update') {
        response = await pluginsMarketApi.updatePlugin(confirmDialog.plugin.moduleName)
      } else if (confirmDialog.action === 'unpublish') {
        response = await pluginsMarketApi.deleteUserPlugin(confirmDialog.plugin.moduleName)
      }

      if (response && response.code === 200) {
        let successMessage = '操作成功'
        if (confirmDialog.action === 'download') {
          successMessage = '插件获取成功'
        } else if (confirmDialog.action === 'update') {
          successMessage = '插件更新成功'
        } else if (confirmDialog.action === 'unpublish') {
          successMessage = '插件下架成功'
          // 下架成功后从列表中移除
          setPlugins(prev => prev.filter(p => p.id !== confirmDialog.plugin?.id))
          if (selectedPlugin?.id === confirmDialog.plugin.id) {
            setSelectedPlugin(null)
          }
          // 重新获取插件列表以更新状态
          fetchPlugins(currentPage, debouncedSearchKeyword, filterWebhook || undefined)
        }

        showSuccess(successMessage)

        // 更新本地状态（下载、更新）
        if (confirmDialog.action !== 'unpublish') {
          setPlugins(prev =>
            prev.map(p =>
              p.id === confirmDialog.plugin?.id ? { ...p, is_local: true, can_update: false } : p
            )
          )
          if (selectedPlugin?.id === confirmDialog.plugin.id) {
            setSelectedPlugin({
              ...selectedPlugin,
              is_local: true,
              can_update: false,
            })
          }
        }
      } else if (response) {
        showError(`操作失败: ${response.msg}`)
      } else {
        showError('操作失败: 未知错误')
      }
    } catch (error) {
      console.error('操作失败', error)
      showError('操作失败，请重试')
    } finally {
      setProcessingId(null)
      setConfirmDialog({ open: false, plugin: null, action: 'download' })
    }
  }

  const handleToggleWebhookFilter = () => {
    setFilterWebhook(!filterWebhook)
  }

  // 处理创建插件
  const handleCreatePlugin = async (data: PluginCreateRequest) => {
    try {
      setIsSubmitting(true)
      const response = await pluginsMarketApi.createPlugin(data)

      if (response.code === 200) {
        // 成功创建
        showSuccess('插件发布成功！')
        setCreateDialogOpen(false)
        // 刷新插件列表
        fetchPlugins(1, debouncedSearchKeyword, filterWebhook || undefined)
      } else {
        // 处理不同的错误情况
        const errorMsg = response.msg || '未知错误'
        showError(errorMsg)
      }
    } catch (error) {
      console.error('创建插件失败', error)

      // 网络错误或其他未处理的错误
      const errorMessage = error instanceof Error ? error.message : String(error)
      showError(`发布失败: ${errorMessage}`)

      // 显示重试建议
      setTimeout(() => {
        showWarning('请检查网络连接或稍后重试')
      }, 1000)
    } finally {
      setIsSubmitting(false)
    }
  }

  if (error && plugins.length === 0) {
    return (
      <Box sx={{ p: 3 }}>
        <Alert severity="error">{error}</Alert>
      </Box>
    )
  }

  return (
    <Box sx={{ p: 3 }}>
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
            overflow: 'hidden',
          }}
        >
          <TextField
            size="small"
            placeholder="搜索插件"
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
                    &times;
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
            {loading ? '搜索中...' : '搜索'}
          </Button>
        </Box>

        <Box sx={{ display: 'flex', gap: 2, alignItems: 'center' }}>
          <FormControlLabel
            control={
              <Switch
                checked={filterWebhook}
                onChange={handleToggleWebhookFilter}
                color="primary"
              />
            }
            label="只显示支持 Webhook 的插件"
          />

          <Button
            variant="contained"
            color="primary"
            startIcon={<AddIcon />}
            onClick={() => setCreateDialogOpen(true)}
          >
            发布插件
          </Button>
        </Box>
      </Box>

      {/* 插件内容区域 */}
      <Box position="relative" minHeight={plugins.length === 0 ? '300px' : 'auto'}>
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
              alignItems: plugins.length === 0 ? 'center' : 'flex-start',
              backgroundColor: 'transparent',
              zIndex: 10,
              borderRadius: 2,
              backdropFilter: 'blur(2px)',
              pt: plugins.length === 0 ? 0 : 3,
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
                加载中...
              </Typography>
            </Box>
          </Box>
        )}

        {plugins.length > 0 ? (
          <>
            <Grid container spacing={3}>
              {plugins.map(plugin => (
                <Grid item xs={12} sm={6} md={4} key={plugin.id}>
                  <PluginCard
                    plugin={plugin}
                    onDownload={() => handleDownloadClick(plugin)}
                    onUpdate={() => handleUpdateClick(plugin)}
                    onUnpublish={plugin.isOwner ? () => handleUnpublishClick(plugin) : undefined}
                    onShowDetail={() => handleShowDetail(plugin)}
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
                没有找到符合条件的插件
              </Typography>
              <Typography variant="body2" color="text.disabled" sx={{ maxWidth: 400 }}>
                尝试使用其他关键词搜索，或取消筛选条件后再次尝试。
                <br />
                新上传的插件可能需要一些时间才能被检索到。
              </Typography>
            </Box>
          )
        )}
      </Box>

      {/* 详情对话框 */}
      <PluginDetailDialog
        open={!!selectedPlugin}
        onClose={() => setSelectedPlugin(null)}
        plugin={selectedPlugin}
        onUnpublish={
          selectedPlugin?.isOwner ? () => handleUnpublishClick(selectedPlugin) : undefined
        }
        onDownload={
          selectedPlugin && !selectedPlugin.is_local
            ? () => handleDownloadClick(selectedPlugin)
            : undefined
        }
        onUpdate={selectedPlugin?.can_update ? () => handleUpdateClick(selectedPlugin) : undefined}
      />

      {/* 确认下载/更新/下架对话框 */}
      <Dialog
        open={confirmDialog.open}
        onClose={() => setConfirmDialog({ open: false, plugin: null, action: 'download' })}
      >
        <DialogTitle>
          {confirmDialog.action === 'download'
            ? '确认获取'
            : confirmDialog.action === 'update'
              ? '确认更新'
              : '确认下架'}
        </DialogTitle>
        <DialogContent>
          <Typography>
            {confirmDialog.action === 'download' &&
              `确定要获取插件 "${confirmDialog.plugin?.name}" 到本地库吗？`}
            {confirmDialog.action === 'update' &&
              `确定要更新插件 "${confirmDialog.plugin?.name}" 到最新版本吗？`}
            {confirmDialog.action === 'unpublish' && (
              <>
                <Alert severity="warning" sx={{ mb: 2 }}>
                  下架后此插件将从云端市场移除，其他用户将无法再下载。此操作不可恢复。
                </Alert>
                确定要从云端市场下架插件 "{confirmDialog.plugin?.name}" 吗？
              </>
            )}
          </Typography>
        </DialogContent>
        <DialogActions>
          <Button
            onClick={() => setConfirmDialog({ open: false, plugin: null, action: 'download' })}
            disabled={!!processingId}
          >
            取消
          </Button>
          <Button
            onClick={handleConfirm}
            color={confirmDialog.action === 'unpublish' ? 'error' : 'primary'}
            disabled={!!processingId}
          >
            {processingId ? <CircularProgress size={24} /> : '确认'}
          </Button>
        </DialogActions>
      </Dialog>

      {/* 创建插件对话框 */}
      <CreatePluginDialog
        open={createDialogOpen}
        onClose={() => setCreateDialogOpen(false)}
        onSubmit={handleCreatePlugin}
        isSubmitting={isSubmitting}
      />

      {/* 全局消息提示 */}
      <Snackbar
        open={!!messageInfo}
        autoHideDuration={messageInfo?.type === 'success' ? 2000 : 5000}
        onClose={() => setMessageInfo(null)}
        anchorOrigin={{ vertical: 'top', horizontal: 'center' }}
      >
        <Alert
          onClose={() => setMessageInfo(null)}
          severity={messageInfo?.type || 'error'}
          variant="filled"
          sx={{ width: '100%' }}
        >
          {messageInfo?.content}
        </Alert>
      </Snackbar>
    </Box>
  )
}
