import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Box, Paper, TextField, Button, Typography, Alert } from '@mui/material'
import { authApi } from '../../services/api/auth'
import { useAuthStore } from '../../stores/auth'

export default function LoginPage() {
  const navigate = useNavigate()
  const { setToken, setUserInfo } = useAuthStore()
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  const handleLogin = async () => {
    if (!username || !password) {
      setError('请输入用户名和密码')
      return
    }

    try {
      setError('')
      setLoading(true)

      // 登录获取token
      console.log('Attempting login...')
      const loginRes = await authApi.login({ username, password })
      console.log('Login successful:', loginRes)

      // 设置token
      setToken(loginRes.access_token)
      console.log('Token set:', loginRes.access_token)

      // 获取用户信息
      console.log('Fetching user info...')
      const userInfo = await authApi.getUserInfo()
      console.log('User info received:', userInfo)

      // 设置用户信息
      setUserInfo(userInfo)
      console.log('User info set, preparing to navigate...')

      // 跳转到首页
      navigate('/')
      console.log('Navigation triggered')
    } catch (error) {
      console.error('Login error:', error)
      if (error instanceof Error) {
        setError(error.message || '登录失败，请检查用户名和密码')
      } else {
        setError('登录失败，请检查用户名和密码')
      }
    } finally {
      setLoading(false)
    }
  }

  const handleKeyPress = (event: React.KeyboardEvent) => {
    if (event.key === 'Enter' && !loading) {
      handleLogin()
    }
  }

  return (
    <Box
      sx={{
        height: '100vh',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        bgcolor: 'background.default',
      }}
    >
      <Paper
        elevation={3}
        sx={{
          p: 4,
          width: '100%',
          maxWidth: 400,
        }}
      >
        <Typography variant="h5" align="center" gutterBottom>
          Nekro Agent 管理面板
        </Typography>

        <Box component="form" sx={{ mt: 2 }}>
          <TextField
            fullWidth
            label="用户名"
            value={username}
            onChange={e => setUsername(e.target.value)}
            onKeyPress={handleKeyPress}
            margin="normal"
            autoFocus
          />
          <TextField
            fullWidth
            label="密码"
            type="password"
            value={password}
            onChange={e => setPassword(e.target.value)}
            onKeyPress={handleKeyPress}
            margin="normal"
          />

          {error && (
            <Alert severity="error" sx={{ mt: 2 }}>
              {error}
            </Alert>
          )}

          <Button
            fullWidth
            variant="contained"
            onClick={handleLogin}
            disabled={loading || !username || !password}
            sx={{ mt: 3 }}
          >
            {loading ? '登录中...' : '登录'}
          </Button>
        </Box>
      </Paper>
    </Box>
  )
}
