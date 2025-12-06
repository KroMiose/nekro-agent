import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  Box,
  Paper,
  TextField,
  Button,
  Typography,
  useTheme,
  useMediaQuery,
  InputAdornment,
  IconButton,
  CircularProgress,
  Link,
  Container,
  Fade,
  Checkbox,
  FormControlLabel,
} from '@mui/material'
import {
  Person as PersonIcon,
  Lock as LockIcon,
  Visibility as VisibilityIcon,
  VisibilityOff as VisibilityOffIcon,
} from '@mui/icons-material'
import { authApi } from '../../services/api/auth'
import { useAuthStore } from '../../stores/auth'
import { UI_STYLES, getCurrentThemeMode } from '../../theme/themeApi'
import { BORDER_RADIUS, INPUT_VARIANTS, BUTTON_VARIANTS } from '../../theme/variants'
import { ThemeToggleButton } from '../../theme'
import { motion } from 'framer-motion'
import { useNotification } from '../../hooks/useNotification'
import { useWallpaperStore } from '../../stores/wallpaper'
import WallpaperBackground from '../../components/common/WallpaperBackground'
import { useGitHubStarStore } from '../../stores/githubStar'
<<<<<<< HEAD
import logoImage from '../../assets/logo.png'
=======
<<<<<<< HEAD
import logoImage from '../../assets/logo.png'
=======
<<<<<<< HEAD
import logoImage from '../../assets/logo.png'
=======
>>>>>>> 6cf9d37 (增加PYPI源自定义和代理功能)
>>>>>>> a776096 (增加PYPI源自定义和代理功能)
>>>>>>> e26199f (增加PYPI源自定义和代理功能)

export default function LoginPage() {
  const navigate = useNavigate()
  const { setToken, setUserInfo } = useAuthStore()
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [loading, setLoading] = useState(false)
  const [showPassword, setShowPassword] = useState(false)
  const [showForm, setShowForm] = useState(false)
  const [agreeTerms, setAgreeTerms] = useState(false)
  const theme = useTheme()
  const themeMode = getCurrentThemeMode()
  const isMobile = useMediaQuery(theme.breakpoints.down('sm'))
  const isTablet = useMediaQuery(theme.breakpoints.down('md'))
  const notification = useNotification()

  // 使用壁纸store
  const { loginWallpaper, loginWallpaperMode, loginWallpaperBlur, loginWallpaperDim } =
    useWallpaperStore()

  // 延迟显示表单，创建更流畅的加载体验
  useEffect(() => {
    const timer = setTimeout(() => setShowForm(true), 300)
    return () => clearTimeout(timer)
  }, [])

  // 从localStorage读取协议同意状态
  useEffect(() => {
    const savedAgreement = localStorage.getItem('nekro_terms_agreed')
    if (savedAgreement === 'true') {
      setAgreeTerms(true)
    }
  }, [])

  // 保存协议同意状态到localStorage
  const handleAgreeTermsChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    const newValue = event.target.checked
    setAgreeTerms(newValue)
    localStorage.setItem('nekro_terms_agreed', newValue.toString())
  }

  const handleLogin = async () => {
    if (!username || !password) {
      notification.warning('请输入用户名和密码')
      return
    }

    try {
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

      // 提示登录成功
      notification.success('登录成功')

      // 异步检查GitHub Star状态，不阻塞登录流程
      const checkGitHubStar = async () => {
        try {
          const { checkStarStatus } = useGitHubStarStore.getState()

          // 异步检查，不显示通知，检查失败也不影响登录
          await checkStarStatus(
            { force: false, clearCache: false, showNotification: false },
            {
              resetDefaults: true,
              onStarred: () => {},
              onNotStarred: () => {},
              onError: () => {},
            }
          )
        } catch (error) {
          console.error('GitHub Star状态检查异常:', error)
        }
      }

      // 启动异步检查
      checkGitHubStar()

      // 跳转到首页
      navigate('/')
      console.log('Navigation triggered')
    } catch (error) {
      console.error('Login error:', error)
      if (error instanceof Error) {
        notification.error(error.message || '登录失败，请检查用户名和密码')
      } else {
        notification.error('登录失败，请检查用户名和密码')
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
        minHeight: '100vh',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        background: UI_STYLES.BACKGROUND.PRIMARY,
        backgroundSize: 'cover',
        backgroundPosition: 'center',
        position: 'relative',
        overflow: 'hidden',
        p: { xs: 2, md: 4 },
      }}
    >
      {/* 壁纸背景 */}
      {loginWallpaper ? (
        <Box
          sx={{
            position: 'absolute',
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            zIndex: 0,
          }}
        >
          <WallpaperBackground
            wallpaperUrl={loginWallpaper}
            mode={loginWallpaperMode as 'cover' | 'contain' | 'repeat' | 'center'}
            blur={loginWallpaperBlur}
            dim={loginWallpaperDim}
          />
        </Box>
      ) : (
        // 默认背景元素 - 当没有设置壁纸时显示
        <Box
          sx={{
            position: 'absolute',
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            overflow: 'hidden',
            zIndex: 0,
            backgroundColor: theme.palette.background.default,
          }}
        >
          {/* 新的、性能优化的动态背景 */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ duration: 2, ease: 'easeIn' }}
            style={{
              position: 'absolute',
              top: 0,
              left: 0,
              right: 0,
              bottom: 0,
            }}
          >
            {/* 旋转的渐变背景 */}
            <motion.div
              animate={{
                rotate: [0, 360],
              }}
              transition={{
                duration: 50,
                repeat: Infinity,
                ease: 'linear',
              }}
              style={{
                position: 'absolute',
                top: '50%',
                left: '50%',
                width: '200vmax',
                height: '200vmax',
                x: '-50%',
                y: '-50%',
                backgroundImage: `radial-gradient(ellipse at 70% 30%, ${theme.palette.primary.main}2A 0%, transparent 40%),
                  radial-gradient(ellipse at 30% 70%, ${theme.palette.secondary.main}3A 0%, transparent 50%)`,
                willChange: 'transform',
              }}
            />
            {/* 星星点点的效果 */}
            <Box
              sx={{
                position: 'absolute',
                top: 0,
                left: 0,
                width: '100%',
                height: '100%',
                backgroundImage:
                  themeMode === 'dark'
                    ? `url('data:image/svg+xml;utf8,<svg width="200" height="200" viewBox="0 0 200 200" xmlns="http://www.w3.org/2000/svg"><g fill="rgba(255,255,255,0.1)"><circle cx="20" cy="20" r="1" /><circle cx="50" cy="80" r="1" /><circle cx="90" cy="30" r="1" /><circle cx="10" cy="70" r="1" /><circle cx="80" cy="90" r="1" /><circle cx="150" cy="50" r="1" /><circle cx="180" cy="150" r="1" /><circle cx="120" cy="180" r="1" /><circle cx="30" cy="160" r="1" /><circle cx="190" cy="90" r="1.5" /></g></svg>')`
                    : `url('data:image/svg+xml;utf8,<svg width="200" height="200" viewBox="0 0 200 200" xmlns="http://www.w3.org/2000/svg"><g fill="rgba(0,0,0,0.08)"><circle cx="20" cy="20" r="1" /><circle cx="50" cy="80" r="1" /><circle cx="90" cy="30" r="1" /><circle cx="10" cy="70" r="1" /><circle cx="80" cy="90" r="1" /><circle cx="150" cy="50" r="1" /><circle cx="180" cy="150" r="1" /><circle cx="120" cy="180" r="1" /><circle cx="30" cy="160" r="1" /><circle cx="190" cy="90" r="1.5" /></g></svg>')`,
                animation:
                  'move-background 40s linear infinite alternate, shimmer 8s ease-in-out infinite alternate',
                '@keyframes move-background': {
                  from: { backgroundPosition: '0 0' },
                  to: { backgroundPosition: '200px 400px' },
                },
                '@keyframes shimmer': {
                  '0%, 100%': { opacity: 0.7 },
                  '50%': { opacity: 1 },
                },
                willChange: 'background-position, opacity',
              }}
            />
          </motion.div>
        </Box>
      )}

      {/* 主题切换按钮 - 顶部右侧 */}
      <Box
        sx={{
          position: 'absolute',
          top: { xs: 12, md: 20 },
          right: { xs: 12, md: 20 },
          zIndex: 10,
        }}
      >
        <ThemeToggleButton />
      </Box>

      <Container maxWidth="lg" sx={{ display: 'flex', justifyContent: 'center', zIndex: 2 }}>
        <Box
          sx={{
            display: 'flex',
            flexDirection: { xs: 'column', md: 'row' },
            alignItems: 'center',
            justifyContent: 'center',
            gap: { xs: 3, md: 6 },
            width: '100%',
            maxWidth: { xs: '100%', md: '1000px' },
          }}
        >
          {/* 左侧品牌区域 - 仅在平板及以上尺寸显示 */}
          {!isMobile && (
            <Fade in={showForm} timeout={800}>
              <Box
                sx={{
                  flex: { md: 1 },
                  textAlign: 'center',
                  display: { xs: 'none', sm: 'flex' },
                  flexDirection: 'column',
                  alignItems: 'center',
                  justifyContent: 'center',
                  p: { sm: 2, md: 4 },
                }}
              >
                <motion.div
                  initial={{ opacity: 0, scale: 0.9 }}
                  animate={{ opacity: 1, scale: 1 }}
                  transition={{ duration: 0.5, ease: 'easeOut' }}
                >
                  <Box
                    component="img"
<<<<<<< HEAD
                    src={logoImage}
=======
<<<<<<< HEAD
                    src={logoImage}
=======
<<<<<<< HEAD
                    src={logoImage}
=======
                    src="/logo.png"
>>>>>>> 6cf9d37 (增加PYPI源自定义和代理功能)
>>>>>>> a776096 (增加PYPI源自定义和代理功能)
>>>>>>> e26199f (增加PYPI源自定义和代理功能)
                    alt="Nekro Agent Logo"
                    sx={{
                      width: { sm: 180, md: 240 },
                      height: 'auto',
                      objectFit: 'contain',
                      filter:
                        theme.palette.mode === 'dark'
                          ? 'drop-shadow(0 0 20px rgba(255,255,255,0.2))'
                          : 'drop-shadow(0 0 20px rgba(0,0,0,0.1))',
                      mb: 3,
                      padding: { sm: 0.8, md: 1 },
                      backgroundColor: 'rgba(255, 192, 203, 0.15)',
                      borderRadius: '24px',
                      backdropFilter: 'blur(8px)',
                      WebkitBackdropFilter: 'blur(8px)',
                      border: `1px solid rgba(255, 192, 203, ${themeMode === 'dark' ? '0.2' : '0.15'})`,
                      boxShadow: `0 0 15px rgba(255, 192, 203, ${themeMode === 'dark' ? '0.2' : '0.1'})`,
                      transition: 'all 0.3s ease',
                    }}
                  />
                </motion.div>

                <motion.div
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.5, delay: 0.2, ease: 'easeOut' }}
                >
                  <Typography
                    variant={isTablet ? 'h5' : 'h3'}
                    sx={{
                      fontWeight: 700,
                      background: `linear-gradient(90deg, ${theme.palette.primary.main}, ${theme.palette.secondary.main})`,
                      backgroundClip: 'text',
                      WebkitBackgroundClip: 'text',
                      color: 'transparent',
                      textShadow:
                        themeMode === 'dark'
                          ? '0 0 30px rgba(255,255,255,0.1)'
                          : '0 0 30px rgba(0,0,0,0.05)',
                      letterSpacing: '0.05em',
                      py: 1,
                    }}
                  >
                    Nekro Agent
                  </Typography>
                </motion.div>

                <motion.div
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 0.8, y: 0 }}
                  transition={{ duration: 0.5, delay: 0.4, ease: 'easeOut' }}
                >
                  <Typography
                    variant="h6"
                    color="text.secondary"
                    sx={{
                      mt: 2,
                      fontWeight: 400,
                      fontSize: { sm: '0.9rem', md: '1.1rem' },
                      whiteSpace: 'nowrap',
                      mx: 'auto',
                      lineHeight: 1.5,
                    }}
                  >
                    开启优雅智能交互之旅
                  </Typography>
                </motion.div>
              </Box>
            </Fade>
          )}

          {/* 右侧登录表单 */}
          <Fade in={showForm} timeout={500}>
            <Paper
              elevation={0}
              sx={{
                p: { xs: 3, sm: 4 },
                width: '100%',
                maxWidth: { xs: '100%', sm: 450 },
                position: 'relative',
                zIndex: 2,
                boxShadow: UI_STYLES.getShadow('medium'),
                borderRadius: BORDER_RADIUS.MEDIUM,
                background:
                  themeMode === 'dark'
                    ? 'linear-gradient(135deg, rgba(40, 40, 45, 0.65), rgba(25, 25, 30, 0.7))'
                    : 'linear-gradient(135deg, rgba(255, 255, 255, 0.75), rgba(255, 255, 255, 0.6))',
                backdropFilter: 'blur(20px)',
                WebkitBackdropFilter: 'blur(20px)',
                border: UI_STYLES.getBorder(themeMode === 'dark' ? 0.15 : 0.08),
                transition: 'all 0.3s ease',
                '&::before': {
                  content: '""',
                  position: 'absolute',
                  inset: 0,
                  borderRadius: BORDER_RADIUS.MEDIUM,
                  padding: '1px',
                  background:
                    themeMode === 'dark'
                      ? `linear-gradient(135deg, ${theme.palette.primary.main}40, ${theme.palette.secondary.main}30)`
                      : `linear-gradient(135deg, ${theme.palette.primary.main}30, ${theme.palette.secondary.main}20)`,
                  WebkitMask: 'linear-gradient(#fff 0 0) content-box, linear-gradient(#fff 0 0)',
                  WebkitMaskComposite: 'xor',
                  maskComposite: 'exclude',
                  pointerEvents: 'none',
                },
                '&::after': {
                  content: '""',
                  position: 'absolute',
                  inset: 0,
                  borderRadius: BORDER_RADIUS.MEDIUM,
                  boxShadow: 'inset 0 0 20px rgba(255, 255, 255, 0.08)',
                  pointerEvents: 'none',
                },
                '&:hover': {
                  boxShadow: UI_STYLES.getShadow('deep'),
                  backdropFilter: 'blur(25px)',
                  WebkitBackdropFilter: 'blur(25px)',
                },
              }}
            >
              {/* 移动端专用标题区域 */}
              {isMobile && (
                <Box sx={{ textAlign: 'center', mb: 3 }}>
                  <Box
                    sx={{
                      display: 'flex',
                      justifyContent: 'center',
                      alignItems: 'center',
                      mb: 1.5,
                    }}
                  >
                    <Box
                      component="img"
<<<<<<< HEAD
                      src={logoImage}
=======
<<<<<<< HEAD
                      src={logoImage}
=======
<<<<<<< HEAD
                      src={logoImage}
=======
                      src="/logo.png"
>>>>>>> 6cf9d37 (增加PYPI源自定义和代理功能)
>>>>>>> a776096 (增加PYPI源自定义和代理功能)
>>>>>>> e26199f (增加PYPI源自定义和代理功能)
                      alt="Nekro Agent Logo"
                      sx={{
                        width: 120,
                        height: 'auto',
                        objectFit: 'contain',
                        filter:
                          theme.palette.mode === 'dark'
                            ? 'drop-shadow(0 2px 2px rgba(255,255,255,0.2))'
                            : 'drop-shadow(0 2px 2px rgba(0,0,0,0.1))',
                        padding: 0.6,
                        backgroundColor: 'rgba(255, 192, 203, 0.15)',
                        borderRadius: '18px',
                        backdropFilter: 'blur(8px)',
                        WebkitBackdropFilter: 'blur(8px)',
                        border: `1px solid rgba(255, 192, 203, ${themeMode === 'dark' ? '0.2' : '0.15'})`,
                        boxShadow: `0 0 10px rgba(255, 192, 203, ${themeMode === 'dark' ? '0.2' : '0.1'})`,
                      }}
                    />
                  </Box>
                  <Typography
                    variant="h5"
                    sx={{
                      fontWeight: 600,
                      background: `linear-gradient(90deg, ${theme.palette.primary.main}, ${theme.palette.secondary.main})`,
                      backgroundClip: 'text',
                      WebkitBackgroundClip: 'text',
                      color: 'transparent',
                    }}
                  >
                    Nekro Agent
                  </Typography>
                </Box>
              )}

              <Typography
                variant={isMobile ? 'subtitle1' : 'h6'}
                sx={{
                  mb: 3,
                  fontWeight: 500,
                  color: 'text.primary',
                  textAlign: 'center',
                }}
              >
                欢迎回来
              </Typography>

              <Box component="form" sx={{ mt: 1 }}>
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
                    ...INPUT_VARIANTS.default.styles,
                    '.MuiOutlinedInput-root': {
                      backdropFilter: 'blur(5px)',
                      backgroundColor:
                        themeMode === 'dark' ? 'rgba(45, 45, 50, 0.5)' : 'rgba(255, 255, 255, 0.5)',
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
                    ...INPUT_VARIANTS.default.styles,
                    '.MuiOutlinedInput-root': {
                      backdropFilter: 'blur(5px)',
                      backgroundColor:
                        themeMode === 'dark' ? 'rgba(45, 45, 50, 0.5)' : 'rgba(255, 255, 255, 0.5)',
                    },
                  }}
                />

                {/* 协议同意复选框 */}
                <FormControlLabel
                  control={
                    <Checkbox
                      checked={agreeTerms}
                      onChange={handleAgreeTermsChange}
                      size={isMobile ? 'small' : 'medium'}
                      color="primary"
                    />
                  }
                  label={
                    <Typography variant="caption" color="text.secondary" sx={{ lineHeight: 1.5 }}>
                      我已阅读并同意{' '}
                      <Link
                        href="https://github.com/KroMiose/nekro-agent/blob/main/LICENSE"
                        target="_blank"
                        rel="noopener noreferrer"
                        sx={{ color: theme.palette.primary.main }}
                      >
                        项目开源协议
                      </Link>{' '}
                      和{' '}
                      <Link
                        href="https://community.nekro.ai/terms"
                        target="_blank"
                        rel="noopener noreferrer"
                        sx={{ color: theme.palette.primary.main }}
                      >
                        NekroAI 社区共享协议
                      </Link>
                    </Typography>
                  }
                  sx={{
                    mt: 1,
                    mb: 0.5,
                    display: 'flex',
                    color: theme.palette.text.secondary,
                    '.MuiFormControlLabel-label': {
                      fontSize: isMobile ? '0.7rem' : '0.75rem',
                    },
                  }}
                />

                <Button
                  fullWidth
                  variant="contained"
                  onClick={handleLogin}
                  disabled={loading || !username || !password || !agreeTerms}
                  sx={{
                    ...BUTTON_VARIANTS.primary.styles,
                    mt: 3,
                    mb: 2,
                    py: isMobile ? 1 : 1.5,
                    boxShadow: `0 8px 16px ${theme.palette.primary.main}30`,
                    background: UI_STYLES.GRADIENTS.BUTTON.PRIMARY,
                    '&:hover': {
                      transform: 'translateY(-2px)',
                      boxShadow: `0 12px 20px ${theme.palette.primary.main}40`,
                    },
                    minHeight: isMobile ? 40 : 48,
                    position: 'relative',
                    letterSpacing: '0.05em',
                    fontWeight: 500,
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
                    mt: 2,
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
                      sx={{
                        color: theme.palette.primary.main,
                        textDecoration: 'none',
                        '&:hover': {
                          textDecoration: 'underline',
                        },
                      }}
                    >
                      Nekro Agent
                    </Link>
                    . 版权所有.
                  </Typography>
                </Box>
              </Box>
            </Paper>
          </Fade>
        </Box>
      </Container>
    </Box>
  )
}
