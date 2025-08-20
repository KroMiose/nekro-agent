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
import {
  CARD_VARIANTS,
  INPUT_VARIANTS,
  BUTTON_VARIANTS,
  BORDER_RADIUS,
} from '../../theme/variants'
import { useNotification } from '../../hooks/useNotification'

export default function ProfilePage() {
  const [newPassword, setNewPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [loading, setLoading] = useState(false)
  const notification = useNotification()

  // 获取用户信息
  const { data: userInfo } = useQuery({
    queryKey: ['userInfo'],
    queryFn: () => authApi.getUserInfo(),
  })

  const isAdminUser = userInfo?.username === 'admin'

  // 处理修改密码
  const handleChangePassword = async () => {
    if (isAdminUser) {
      notification.info('管理员账号暂不支持修改密码')
      return
    }
    if (!newPassword || !confirmPassword) {
      notification.error('请填写所有密码字段')
      return
    }

    if (newPassword !== confirmPassword) {
      notification.error('新密码和确认密码不匹配')
      return
    }

    try {
      setLoading(true)
      await authApi.updatePassword({
        password: newPassword,
      })
      notification.success('密码修改成功')
      // 清空输入框
      setNewPassword('')
      setConfirmPassword('')
    } catch (error) {
      if (error instanceof Error) {
        notification.error(error.message)
      } else {
        notification.error('密码修改失败')
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
            个人信息
          </Typography>
          <Divider sx={{ my: 2 }} />
          <Stack spacing={2}>
            <Box>
              <Typography variant="subtitle2" color="text.secondary">
                用户名
              </Typography>
              <Typography variant="body1">{userInfo?.username}</Typography>
            </Box>
            <Box>
              <Typography variant="subtitle2" color="text.secondary">
                用户ID
              </Typography>
              <Typography variant="body1">{userInfo?.userId}</Typography>
            </Box>
            <Box>
              <Typography variant="subtitle2" color="text.secondary">
                权限等级
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
            修改密码
          </Typography>
          <Divider sx={{ my: 2 }} />
          <Stack spacing={3}>
            {isAdminUser && (
              <Typography variant="body2" color="text.secondary">
                管理员账号暂不支持在此修改密码，请在系统环境变量中修改
              </Typography>
            )}
            <TextField
              fullWidth
              type="password"
              label="新密码"
              value={newPassword}
              onChange={e => setNewPassword(e.target.value)}
              disabled={isAdminUser}
              sx={INPUT_VARIANTS.default.styles}
            />
            <TextField
              fullWidth
              type="password"
              label="确认新密码"
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
              {loading ? '提交中...' : '修改密码'}
            </Button>
          </Stack>
        </CardContent>
      </Card>
    </Box>
  )
}
