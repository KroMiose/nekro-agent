import { useState } from 'react'
import {
  Box,
  TextField,
  Button,
  Typography,
  Alert,
  Snackbar,
  Stack,
  Card,
  CardContent,
  Divider,
} from '@mui/material'
import { useQuery } from '@tanstack/react-query'
import { authApi } from '../../services/api/auth'

export default function ProfilePage() {
  const [newPassword, setNewPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [message, setMessage] = useState<{ type: 'success' | 'error'; content: string } | null>(
    null
  )
  const [loading, setLoading] = useState(false)

  // 获取用户信息
  const { data: userInfo } = useQuery({
    queryKey: ['userInfo'],
    queryFn: () => authApi.getUserInfo(),
  })

  // 处理修改密码
  const handleChangePassword = async () => {
    if (!newPassword || !confirmPassword) {
      setMessage({ type: 'error', content: '请填写所有密码字段' })
      return
    }

    if (newPassword !== confirmPassword) {
      setMessage({ type: 'error', content: '新密码和确认密码不匹配' })
      return
    }

    try {
      setLoading(true)
      await authApi.updatePassword({
        password: newPassword,
      })
      setMessage({ type: 'success', content: '密码修改成功' })
      // 清空输入框
      setNewPassword('')
      setConfirmPassword('')
    } catch (error) {
      if (error instanceof Error) {
        setMessage({ type: 'error', content: error.message })
      } else {
        setMessage({ type: 'error', content: '密码修改失败' })
      }
    } finally {
      setLoading(false)
    }
  }

  return (
    <Box sx={{ maxWidth: 800, mx: 'auto', p: 3 }}>
      {/* 用户信息卡片 */}
      <Card sx={{ mb: 4 }}>
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
      <Card>
        <CardContent>
          <Typography variant="h6" gutterBottom>
            修改密码
          </Typography>
          <Divider sx={{ my: 2 }} />
          <Stack spacing={3}>
            <TextField
              fullWidth
              type="password"
              label="新密码"
              value={newPassword}
              onChange={e => setNewPassword(e.target.value)}
            />
            <TextField
              fullWidth
              type="password"
              label="确认新密码"
              value={confirmPassword}
              onChange={e => setConfirmPassword(e.target.value)}
            />
            <Button
              variant="contained"
              onClick={handleChangePassword}
              disabled={loading || !newPassword || !confirmPassword}
            >
              {loading ? '提交中...' : '修改密码'}
            </Button>
          </Stack>
        </CardContent>
      </Card>

      {/* 消息提示 */}
      <Snackbar
        open={!!message}
        autoHideDuration={3000}
        onClose={() => setMessage(null)}
        anchorOrigin={{ vertical: 'top', horizontal: 'center' }}
      >
        <Alert
          onClose={() => setMessage(null)}
          severity={message?.type || 'info'}
          variant="filled"
          sx={{ width: '100%' }}
        >
          {message?.content}
        </Alert>
      </Snackbar>
    </Box>
  )
}
