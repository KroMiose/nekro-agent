import React, { useState } from 'react'
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  TextField,
  Box,
  useTheme,
  useMediaQuery,
  Typography,
} from '@mui/material'
import { UserFormData } from '../../../services/api/user-manager'
import { useTranslation } from 'react-i18next'

interface UserFormProps {
  open: boolean
  onClose: () => void
  onSubmit: (data: UserFormData) => Promise<void>
}

const UserForm: React.FC<UserFormProps> = ({ open, onClose, onSubmit }) => {
  const { t } = useTranslation('user-manager')
  const theme = useTheme()
  const isSmall = useMediaQuery(theme.breakpoints.down('sm'))

  const [formData, setFormData] = useState<UserFormData>({
    username: '',
    password: '',
    adapter_key: '',
    platform_userid: '',
    access_key: '',
  })
  const [confirmPassword, setConfirmPassword] = useState('')
  const [errors, setErrors] = useState<Record<string, string>>({})
  const [isSubmitting, setIsSubmitting] = useState(false)

  const handleChange = (
    e: React.ChangeEvent<HTMLInputElement | { name?: string; value: unknown }>
  ) => {
    const { name, value } = e.target
    if (name) {
      setFormData(prev => ({
        ...prev,
        [name]: value,
      }))

      // 清除对应字段的错误
      if (errors[name]) {
        setErrors(prev => {
          const newErrors = { ...prev }
          delete newErrors[name]
          return newErrors
        })
      }
    }
  }

  const validateForm = () => {
    const newErrors: Record<string, string> = {}

    if (!formData.username.trim()) {
      newErrors.username = t('validation.usernameRequired')
    }

    if (!formData.password) {
      newErrors.password = t('validation.passwordRequired')
    } else if (formData.password.length < 6) {
      newErrors.password = t('validation.passwordLength')
    }

    if (formData.password !== confirmPassword) {
      newErrors.confirmPassword = t('validation.passwordMismatch')
    }

    if (!formData.adapter_key.trim()) {
      newErrors.adapter_key = t('validation.adapterKeyRequired')
    }

    if (!formData.platform_userid.trim()) {
      newErrors.platform_userid = t('validation.platformUserIdRequired')
    }

    if (!formData.access_key) {
      newErrors.access_key = t('validation.accessKeyRequired')
    }

    setErrors(newErrors)
    return Object.keys(newErrors).length === 0
  }

  const handleSubmit = async () => {
    if (!validateForm()) return

    setIsSubmitting(true)
    try {
      await onSubmit(formData)
      handleReset()
      onClose()
    } catch (error) {
      console.error('创建用户失败:', error)
    } finally {
      setIsSubmitting(false)
    }
  }

  const handleReset = () => {
    setFormData({
      username: '',
      password: '',
      adapter_key: '',
      platform_userid: '',
      access_key: '',
    })
    setConfirmPassword('')
    setErrors({})
  }

  const handleClose = () => {
    handleReset()
    onClose()
  }

  return (
    <Dialog open={open} onClose={handleClose} maxWidth="sm" fullWidth fullScreen={isSmall}>
      <DialogTitle>
        <Typography variant={isSmall ? 'h6' : 'h5'}>{t('actions.create')}</Typography>
      </DialogTitle>
      <DialogContent dividers>
        <Box sx={{ mt: isSmall ? 0.5 : 1 }}>
          <TextField
            fullWidth
            margin="normal"
            label={t('form.username')}
            name="username"
            value={formData.username}
            onChange={handleChange}
            error={!!errors.username}
            helperText={errors.username}
            required
            size={isSmall ? 'small' : 'medium'}
            InputLabelProps={{
              shrink: true,
              sx: { fontSize: isSmall ? '0.9rem' : '1rem' },
            }}
            sx={{ mb: isSmall ? 1.5 : 2 }}
          />

          <TextField
            fullWidth
            margin="normal"
            label={t('form.password')}
            name="password"
            type="password"
            value={formData.password}
            onChange={handleChange}
            error={!!errors.password}
            helperText={errors.password}
            required
            size={isSmall ? 'small' : 'medium'}
            InputLabelProps={{
              shrink: true,
              sx: { fontSize: isSmall ? '0.9rem' : '1rem' },
            }}
            sx={{ mb: isSmall ? 1.5 : 2 }}
          />

          <TextField
            fullWidth
            margin="normal"
            label={t('form.confirmPassword')}
            type="password"
            value={confirmPassword}
            onChange={e => setConfirmPassword(e.target.value)}
            error={!!errors.confirmPassword}
            helperText={errors.confirmPassword}
            required
            size={isSmall ? 'small' : 'medium'}
            InputLabelProps={{
              shrink: true,
              sx: { fontSize: isSmall ? '0.9rem' : '1rem' },
            }}
            sx={{ mb: isSmall ? 1.5 : 2 }}
          />

          <TextField
            fullWidth
            margin="normal"
            label={t('form.adapterKey')}
            name="adapter_key"
            value={formData.adapter_key}
            onChange={handleChange}
            error={!!errors.adapter_key}
            helperText={errors.adapter_key}
            required
            size={isSmall ? 'small' : 'medium'}
            InputLabelProps={{
              shrink: true,
              sx: { fontSize: isSmall ? '0.9rem' : '1rem' },
            }}
            sx={{ mb: isSmall ? 1.5 : 2 }}
          />

          <TextField
            fullWidth
            margin="normal"
            label={t('form.platformUserId')}
            name="platform_userid"
            value={formData.platform_userid}
            onChange={handleChange}
            error={!!errors.platform_userid}
            helperText={errors.platform_userid}
            required
            size={isSmall ? 'small' : 'medium'}
            InputLabelProps={{
              shrink: true,
              sx: { fontSize: isSmall ? '0.9rem' : '1rem' },
            }}
            sx={{ mb: isSmall ? 1.5 : 2 }}
          />

          <TextField
            fullWidth
            margin="normal"
            label={t('form.accessKey')}
            name="access_key"
            type="password"
            value={formData.access_key}
            onChange={handleChange}
            error={!!errors.access_key}
            helperText={errors.access_key || t('form.createAccessKeyHelper')}
            required
            size={isSmall ? 'small' : 'medium'}
            InputLabelProps={{
              shrink: true,
              sx: { fontSize: isSmall ? '0.9rem' : '1rem' },
            }}
            sx={{ mb: isSmall ? 1 : 1.5 }}
          />
        </Box>
      </DialogContent>
      <DialogActions sx={{ px: isSmall ? 2 : 3, py: isSmall ? 1.5 : 2 }}>
        <Button onClick={handleClose} size={isSmall ? 'small' : 'medium'}>
          {t('actions.cancel', { ns: 'common' })}
        </Button>
        <Button
          onClick={handleSubmit}
          color="primary"
          variant="contained"
          disabled={isSubmitting}
          size={isSmall ? 'small' : 'medium'}
        >
          {isSubmitting ? t('actions.create') + '...' : t('actions.create')}
        </Button>
      </DialogActions>
    </Dialog>
  )
}

export default UserForm
