import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  Box,
  Paper,
  TextField,
  Button,
  Typography,
  Alert,
  useTheme,
  useMediaQuery,
  InputAdornment,
  IconButton,
  CircularProgress,
  Link,
} from '@mui/material'
import {
  Person as PersonIcon,
  Lock as LockIcon,
  Visibility as VisibilityIcon,
  VisibilityOff as VisibilityOffIcon,
} from '@mui/icons-material'
import { authApi } from '../../services/api/auth'
import { useAuthStore } from '../../stores/auth'
import { GRADIENTS, SHADOWS, BORDERS, BORDER_RADIUS, CARD_LAYOUT } from '../../theme/constants'

export default function LoginPage() {
  const navigate = useNavigate()
  const { setToken, setUserInfo } = useAuthStore()
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const [showPassword, setShowPassword] = useState(false)
  const theme = useTheme()
  const isMobile = useMediaQuery(theme.breakpoints.down('sm'))
  const isDark = theme.palette.mode === 'dark'

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

  const toggleShowPassword = () => {
    setShowPassword(!showPassword)
  }

  return (
    <Box
      sx={{
        height: '100vh',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        background: isDark ? GRADIENTS.BACKGROUND.DARK.PRIMARY : GRADIENTS.BACKGROUND.LIGHT.PRIMARY,
        backgroundSize: 'cover',
        backgroundPosition: 'center',
        position: 'relative',
        overflow: 'hidden',
        p: 2,
      }}
    >
      {/* 装饰性背景元素 */}
      <Box
        sx={{
          position: 'absolute',
          top: '-10%',
          left: '-5%',
          width: '120%',
          height: '120%',
          backgroundImage: `radial-gradient(circle at 30% 30%, ${theme.palette.primary.light}20 0%, transparent 25%), 
                            radial-gradient(circle at 70% 70%, ${theme.palette.primary.main}15 0%, transparent 30%)`,
          opacity: 0.8,
          zIndex: 0,
        }}
      />

      <Paper
        elevation={0}
        sx={{
          p: isMobile ? 3 : 4,
          width: '100%',
          maxWidth: 420,
          position: 'relative',
          zIndex: 1,
          boxShadow: isDark ? SHADOWS.CARD.DARK.DEFAULT : SHADOWS.CARD.LIGHT.DEFAULT,
          borderRadius: BORDER_RADIUS.MEDIUM,
          background: isDark ? GRADIENTS.CARD.DARK : GRADIENTS.CARD.LIGHT,
          backdropFilter: CARD_LAYOUT.BACKDROP_FILTER,
          border: isDark ? BORDERS.CARD.DARK : BORDERS.CARD.LIGHT,
          transition: 'all 0.3s ease',
          '&:hover': {
            boxShadow: isDark ? SHADOWS.CARD.DARK.HOVER : SHADOWS.CARD.LIGHT.HOVER,
          },
        }}
      >
        <Box sx={{ textAlign: 'center', mb: 4 }}>
          <Box
            sx={{
              display: 'flex',
              justifyContent: 'center',
              alignItems: 'center',
              mb: 2,
            }}
          >
            <Box
              component="img"
              src="/logo.png"
              alt="Nekro Agent Logo"
              sx={{
                width: isMobile ? 90 : 120,
                height: 'auto',
                mb: 1,
                objectFit: 'contain',
                filter: isDark
                  ? 'drop-shadow(0 2px 2px rgba(255,255,255,0.2))'
                  : 'drop-shadow(0 2px 2px rgba(0,0,0,0.1))',
                transition: 'all 0.3s ease',
              }}
            />
          </Box>
          <Typography
            variant={isMobile ? 'h5' : 'h4'}
            sx={{
              fontWeight: 500,
              color: theme.palette.primary.main,
              mb: 1,
            }}
          >
            Nekro Agent
          </Typography>
          <Typography
            variant="subtitle1"
            color="text.disabled"
            sx={{ fontSize: isMobile ? '0.9rem' : '1rem' }}
          >
            ~开始极致优雅的智能体交互之旅~
          </Typography>
        </Box>

        <Box component="form" sx={{ mt: 2 }}>
          <TextField
            fullWidth
            label="用户名"
            value={username}
            onChange={e => setUsername(e.target.value)}
            onKeyPress={handleKeyPress}
            margin="normal"
            autoFocus
            size={isMobile ? 'small' : 'medium'}
            InputProps={{
              startAdornment: (
                <InputAdornment position="start">
                  <PersonIcon color="action" fontSize={isMobile ? 'small' : 'medium'} />
                </InputAdornment>
              ),
            }}
            sx={{
              '& .MuiOutlinedInput-root': {
                '& fieldset': {
                  borderColor: 'divider',
                  transition: 'all 0.2s',
                },
                '&:hover fieldset': {
                  borderColor: 'primary.light',
                },
                '&.Mui-focused fieldset': {
                  borderColor: 'primary.main',
                },
              },
            }}
          />
          <TextField
            fullWidth
            label="密码"
            type={showPassword ? 'text' : 'password'}
            value={password}
            onChange={e => setPassword(e.target.value)}
            onKeyPress={handleKeyPress}
            margin="normal"
            size={isMobile ? 'small' : 'medium'}
            InputProps={{
              startAdornment: (
                <InputAdornment position="start">
                  <LockIcon color="action" fontSize={isMobile ? 'small' : 'medium'} />
                </InputAdornment>
              ),
              endAdornment: (
                <InputAdornment position="end">
                  <IconButton
                    aria-label="toggle password visibility"
                    onClick={toggleShowPassword}
                    edge="end"
                    size={isMobile ? 'small' : 'medium'}
                  >
                    {showPassword ? <VisibilityOffIcon /> : <VisibilityIcon />}
                  </IconButton>
                </InputAdornment>
              ),
            }}
            sx={{
              '& .MuiOutlinedInput-root': {
                '& fieldset': {
                  borderColor: 'divider',
                  transition: 'all 0.2s',
                },
                '&:hover fieldset': {
                  borderColor: 'primary.light',
                },
                '&.Mui-focused fieldset': {
                  borderColor: 'primary.main',
                },
              },
            }}
          />

          {error && (
            <Alert
              severity="error"
              sx={{
                mt: 2,
                '& .MuiAlert-message': {
                  fontSize: isMobile ? '0.8rem' : '0.9rem',
                },
              }}
            >
              {error}
            </Alert>
          )}

          <Button
            fullWidth
            variant="contained"
            onClick={handleLogin}
            disabled={loading || !username || !password}
            sx={{
              mt: 3,
              mb: 2,
              py: 1.2,
              background: theme.palette.primary.main,
              boxShadow: isDark ? SHADOWS.BUTTON.DARK.DEFAULT : SHADOWS.BUTTON.LIGHT.DEFAULT,
              '&:hover': {
                background: theme.palette.primary.dark,
                boxShadow: isDark ? SHADOWS.BUTTON.DARK.HOVER : SHADOWS.BUTTON.LIGHT.HOVER,
              },
              borderRadius: BORDER_RADIUS.DEFAULT,
              textTransform: 'none',
              fontSize: '1rem',
              minHeight: 48,
              position: 'relative',
            }}
          >
            {loading ? (
              <CircularProgress
                size={24}
                sx={{
                  color: 'white',
                  position: 'absolute',
                  top: '50%',
                  left: '50%',
                  marginTop: '-12px',
                  marginLeft: '-12px',
                }}
              />
            ) : (
              '登录'
            )}
          </Button>

          <Box
            sx={{
              display: 'flex',
              justifyContent: 'center',
              mt: 3,
              opacity: 0.8,
              fontSize: isMobile ? '0.7rem' : '0.8rem',
            }}
          >
            <Typography
              variant="caption"
              color="text.secondary"
              sx={{
                display: 'flex',
                alignItems: 'center',
                gap: 0.5,
              }}
            >
              © {new Date().getFullYear()}
              <Link
                href="https://github.com/KroMiose/nekro-agent"
                target="_blank"
                rel="noopener noreferrer"
              >
                Nekro Agent
              </Link>
              . 版权所有.
            </Typography>
          </Box>
        </Box>
      </Paper>
    </Box>
  )
}
