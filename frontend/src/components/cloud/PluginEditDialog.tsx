import { useState, useEffect } from 'react'
import {
  Box,
  Button,
  Checkbox,
  CircularProgress,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  Divider,
  FormControl,
  FormControlLabel,
  Grid,
  IconButton,
  Link,
  MenuItem,
  TextField,
  Typography,
} from '@mui/material'
import { Close as CloseIcon, Edit as EditIcon, Extension as ExtensionIcon } from '@mui/icons-material'
import { useTranslation } from 'react-i18next'
import { CloudPlugin, PluginUpdateRequest } from '../../services/api/cloud/plugins_market'

interface PluginEditDialogProps {
  open: boolean
  onClose: () => void
  plugin: CloudPlugin | null
  onSubmit: (data: PluginUpdateRequest, moduleName: string) => void
  isSubmitting: boolean
}

export default function PluginEditDialog({
  open,
  onClose,
  plugin,
  onSubmit,
  isSubmitting,
}: PluginEditDialogProps) {
  const { t } = useTranslation(['cloud'])
  const [formData, setFormData] = useState<PluginUpdateRequest>({
    name: '',
    description: '',
    author: '',
    hasWebhook: false,
    homepageUrl: '',
    githubUrl: '',
    cloneUrl: '',
    licenseType: 'MIT',
    isSfw: true,
    icon: '',
    minNaVersion: '',
    maxNaVersion: '',
  })
  const [errors, setErrors] = useState<Record<string, string>>({})
  const [iconPreview, setIconPreview] = useState<string | null>(null)
  // 添加确认选择框状态
  const [confirmSafeContent, setConfirmSafeContent] = useState(false)
  const [agreeToTerms, setAgreeToTerms] = useState(false)

  // 初始化表单数据
  useEffect(() => {
    if (open && plugin) {
      setFormData({
        name: plugin.name || '',
        description: plugin.description || '',
        author: plugin.author || '',
        hasWebhook: plugin.hasWebhook || false,
        homepageUrl: plugin.homepageUrl || '',
        githubUrl: plugin.githubUrl || '',
        cloneUrl: plugin.cloneUrl || '',
        licenseType: plugin.licenseType || 'MIT',
        isSfw: true,
        icon: plugin.icon || '',
        minNaVersion: plugin.minNaVersion || '',
        maxNaVersion: plugin.maxNaVersion || '',
      })
      setIconPreview(plugin.icon || null)
      setErrors({})
      // 重置确认状态
      setConfirmSafeContent(false)
      setAgreeToTerms(false)
    }
  }, [open, plugin])

  // 处理输入变化
  const handleChange = (
    e: React.ChangeEvent<
      HTMLInputElement | HTMLTextAreaElement | { name?: string; value: unknown }
    >
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

  // 处理SFW确认变更
  const handleSfwChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setConfirmSafeContent(e.target.checked)
    // 同时更新formData中的isSfw值
    setFormData(prev => ({ ...prev, isSfw: e.target.checked }))
  }

  // 验证表单
  const validateForm = (): boolean => {
    const newErrors: Record<string, string> = {}

    if (!formData.name?.trim()) {
      newErrors.name = '插件名称不能为空'
    }

    if (!formData.description?.trim()) {
      newErrors.description = '插件描述不能为空'
    }

    if (!formData.author?.trim()) {
      newErrors.author = '作者不能为空'
    }

    if (formData.githubUrl && !/^https?:\/\/github\.com\//.test(formData.githubUrl)) {
      newErrors.githubUrl = 'GitHub URL 格式不正确'
    }

    if (formData.cloneUrl && !/\.git$/.test(formData.cloneUrl)) {
      newErrors.cloneUrl = '克隆URL格式不正确，应以.git结尾'
    }

    if (formData.minNaVersion?.trim() && !/^\d+\.\d+\.\d+$/.test(formData.minNaVersion.trim())) {
      newErrors.minNaVersion = t('pluginsMarket.versionFormatError') || '版本格式应为 x.x.x'
    }

    if (formData.maxNaVersion?.trim() && !/^\d+\.\d+\.\d+$/.test(formData.maxNaVersion.trim())) {
      newErrors.maxNaVersion = t('pluginsMarket.versionFormatError') || '版本格式应为 x.x.x'
    }

    setErrors(newErrors)
    return Object.keys(newErrors).length === 0
  }

  // 处理提交
  const handleSubmit = () => {
    if (!plugin) return
    if (validateForm()) {
      onSubmit(formData, plugin.moduleName)
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
    } catch (_error) {
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

  if (!plugin) return null

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
        编辑插件信息
        <IconButton
          aria-label="close"
          onClick={onClose}
          sx={{
            position: 'absolute',
            right: 8,
            top: 8,
          }}
          size="small"
        >
          <CloseIcon />
        </IconButton>
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

            <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
              模块名: <b>{plugin.moduleName}</b> (不可修改)
            </Typography>
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
                <Button
                  variant="outlined"
                  component="label"
                  disabled={isSubmitting}
                  sx={{ mb: 1 }}
                >
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
              error={!!errors.cloneUrl}
              helperText={errors.cloneUrl}
              placeholder="https://github.com/username/repo.git"
              disabled={isSubmitting}
            />
          </Grid>
          <Grid item xs={12} sm={6}>
            <TextField
              name="minNaVersion"
              label={t('pluginsMarket.minNaVersion')}
              value={formData.minNaVersion}
              onChange={handleChange}
              fullWidth
              error={!!errors.minNaVersion}
              helperText={errors.minNaVersion}
              placeholder="2.3.0"
              disabled={isSubmitting}
            />
          </Grid>
          <Grid item xs={12} sm={6}>
            <TextField
              name="maxNaVersion"
              label={t('pluginsMarket.maxNaVersion')}
              value={formData.maxNaVersion}
              onChange={handleChange}
              fullWidth
              error={!!errors.maxNaVersion}
              helperText={errors.maxNaVersion || t('pluginsMarket.maxNaVersionHint')}
              placeholder="3.0.0"
              disabled={isSubmitting}
            />
          </Grid>

          {/* 添加分割线和确认选项 */}
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
                    href="https://cloud.nekro.ai/terms"
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
          startIcon={isSubmitting ? <CircularProgress size={20} /> : <EditIcon />}
        >
          {isSubmitting ? '提交中...' : '更新信息'}
        </Button>
      </DialogActions>
    </Dialog>
  )
}
