import { useState } from 'react'
import {
  Box,
  TextField,
  Button,
  Typography,
  Stack,
  Card,
  CardContent,
  Divider,
} from '@mui/material'
import { useQuery } from '@tanstack/react-query'
import { authApi } from '../../services/api/auth'
import { CARD_VARIANTS, INPUT_VARIANTS, BUTTON_VARIANTS, BORDER_RADIUS } from '../../theme/variants'
import { useNotification } from '../../hooks/useNotification'
import { useTranslation } from 'react-i18next'

export default function ProfilePage() {
  const [newPassword, setNewPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [loading, setLoading] = useState(false)
  const notification = useNotification()
  const { t } = useTranslation('profile')

  // 获取用户信息
  const { data: userInfo } = useQuery({
    queryKey: ['userInfo'],
    queryFn: () => authApi.getUserInfo(),
  })

  const isAdminUser = userInfo?.username === 'admin'

  // 处理修改密码
  const handleChangePassword = async () => {
    if (isAdminUser) {
      notification.info(t('notifications.adminCannotChangePassword'))
      return
    }
    if (!newPassword || !confirmPassword) {
      notification.error(t('notifications.fillAllFields'))
      return
    }

    if (newPassword !== confirmPassword) {
      notification.error(t('notifications.passwordMismatch'))
      return
    }

    try {
      setLoading(true)
      await authApi.updatePassword({
        password: newPassword,
      })
      notification.success(t('notifications.passwordChangeSuccess'))
      // 清空输入框
      setNewPassword('')
      setConfirmPassword('')
    } catch (error) {
      if (error instanceof Error) {
        notification.error(error.message)
      } else {
        notification.error(t('notifications.passwordChangeFailed'))
      }
    } finally {
      setLoading(false)
    }
  }

  return (
    <Box sx={{ maxWidth: 800, mx: 'auto', p: 3 }}>
      {/* 用户信息卡片 */}
      <Card sx={{ ...CARD_VARIANTS.default.styles, borderRadius: BORDER_RADIUS.LARGE, mb: 4 }}>
        <CardContent>
          <Typography variant="h6" gutterBottom>
            {t('personalInfo.title')}
          </Typography>
          <Divider sx={{ my: 2 }} />
          <Stack spacing={2}>
            <Box>
              <Typography variant="subtitle2" color="text.secondary">
                {t('personalInfo.username')}
              </Typography>
              <Typography variant="body1">{userInfo?.username}</Typography>
            </Box>
            <Box>
              <Typography variant="subtitle2" color="text.secondary">
                {t('personalInfo.userId')}
              </Typography>
              <Typography variant="body1">{userInfo?.userId}</Typography>
            </Box>
            <Box>
              <Typography variant="subtitle2" color="text.secondary">
                {t('personalInfo.permissionLevel')}
              </Typography>
              <Typography variant="body1">{userInfo?.perm_role}</Typography>
            </Box>
          </Stack>
        </CardContent>
      </Card>

      {/* 修改密码卡片 */}
      <Card sx={{ ...CARD_VARIANTS.default.styles, borderRadius: BORDER_RADIUS.LARGE }}>
        <CardContent>
          <Typography variant="h6" gutterBottom>
            {t('changePassword.title')}
          </Typography>
          <Divider sx={{ my: 2 }} />
          <Stack spacing={3}>
            {isAdminUser && (
              <Typography variant="body2" color="text.secondary">
                {t('changePassword.adminNotice')}
              </Typography>
            )}
            <TextField
              fullWidth
              type="password"
              label={t('changePassword.newPassword')}
              value={newPassword}
              onChange={e => setNewPassword(e.target.value)}
              disabled={isAdminUser}
              sx={INPUT_VARIANTS.default.styles}
            />
            <TextField
              fullWidth
              type="password"
              label={t('changePassword.confirmPassword')}
              value={confirmPassword}
              onChange={e => setConfirmPassword(e.target.value)}
              disabled={isAdminUser}
              sx={INPUT_VARIANTS.default.styles}
            />
            <Button
              variant="contained"
              onClick={handleChangePassword}
              disabled={isAdminUser || loading || !newPassword || !confirmPassword}
              sx={BUTTON_VARIANTS.primary.styles}
            >
              {loading ? t('changePassword.submitting') : t('changePassword.submit')}
            </Button>
          </Stack>
        </CardContent>
      </Card>
    </Box>
  )
}
