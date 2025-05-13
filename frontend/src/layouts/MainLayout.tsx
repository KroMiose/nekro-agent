import { useState, useEffect } from 'react'
import { Outlet, useNavigate, useLocation } from 'react-router-dom'
import {
  Box,
  Drawer,
  AppBar,
  Toolbar,
  Typography,
  List,
  ListItem,
  ListItemButton,
  ListItemIcon,
  ListItemText,
  IconButton,
  Tooltip,
  Collapse,
  Alert,
  Snackbar,
  Button,
  Chip,
  Link,
  useMediaQuery,
  useTheme,
} from '@mui/material'
import {
  Terminal as TerminalIcon,
  Settings as SettingsIcon,
  Logout as LogoutIcon,
  Brightness4 as Brightness4Icon,
  Brightness7 as Brightness7Icon,
  Storage as StorageIcon,
  ExpandLess as ExpandLessIcon,
  ExpandMore as ExpandMoreIcon,
  Tune as TuneIcon,
  Extension as ExtensionIcon,
  Chat as ChatIcon,
  Code as CodeIcon,
  GitHub as GitHubIcon,
  Dashboard as DashboardIcon,
  Group as GroupIcon,
  Face as FaceIcon,
  AccountCircle as AccountCircleIcon,
  CloudDownload as CloudDownloadIcon,
  Menu as MenuIcon,
  ChevronLeft as ChevronLeftIcon,
} from '@mui/icons-material'
import { useAuthStore } from '../stores/auth'
import { useColorMode } from '../stores/theme'
import { configApi } from '../services/api/config'
import { motion } from 'framer-motion'
import { GRADIENTS, SHADOWS } from '../theme/constants'

interface PageConfig {
  path: string
  text: string
  icon: JSX.Element
  parent?: string // 父菜单的 key
}

interface MenuGroup {
  key: string
  text: string
  icon: JSX.Element
  children: PageConfig[]
}

// 集中的页面配置
const PAGE_CONFIGS: (PageConfig | MenuGroup)[] = [
  {
    key: 'cloud',
    text: 'Nekro 云',
    icon: <CloudDownloadIcon />,
    children: [
      { path: '/cloud/telemetry', text: '社区观测', icon: <DashboardIcon />, parent: 'cloud' },
      { path: '/cloud/presets-market', text: '人设市场', icon: <FaceIcon />, parent: 'cloud' },
      { path: '/cloud/plugins-market', text: '插件市场', icon: <ExtensionIcon />, parent: 'cloud' },
    ],
  },
  { path: '/dashboard', text: '仪表盘', icon: <DashboardIcon /> },
  { path: '/chat-channel', text: '会话管理', icon: <ChatIcon /> },
  { path: '/user-manager', text: '用户管理', icon: <GroupIcon /> },
  { path: '/presets', text: '人设管理', icon: <FaceIcon /> },
  {
    key: 'plugins',
    text: '插件管理',
    icon: <ExtensionIcon />,
    children: [
      {
        path: '/plugins/management',
        text: '插件管理',
        icon: <ExtensionIcon />,
        parent: 'plugins',
      },
      { path: '/plugins/editor', text: '插件编辑器', icon: <CodeIcon />, parent: 'plugins' },
    ],
  },
  { path: '/logs', text: '系统日志', icon: <TerminalIcon /> },
  { path: '/sandbox-logs', text: '沙盒日志', icon: <CodeIcon /> },
  {
    key: 'protocols',
    text: '协议端',
    icon: <ChatIcon />,
    children: [
      { path: '/protocols/napcat', text: 'NapCat', icon: <ChatIcon />, parent: 'protocols' },
    ],
  },
  {
    key: 'settings',
    text: '系统配置',
    icon: <SettingsIcon />,
    children: [
      { path: '/settings', text: '基本配置', icon: <TuneIcon />, parent: 'settings' },
      { path: '/settings/model-groups', text: '模型组', icon: <StorageIcon />, parent: 'settings' },
    ],
  },
  { path: '/profile', text: '个人中心', icon: <AccountCircleIcon /> },
]

// 转换配置为菜单项
const menuItems = PAGE_CONFIGS.map(config => {
  if ('children' in config) {
    return {
      text: config.text,
      icon: config.icon,
      path: undefined,
      key: config.key,
      children: config.children.map(child => ({
        text: child.text,
        icon: child.icon,
        path: child.path,
      })),
    }
  }
  return {
    text: config.text,
    icon: config.icon,
    path: config.path,
  }
})

export default function MainLayout() {
  const navigate = useNavigate()
  const location = useLocation()
  const { userInfo, logout } = useAuthStore()
  const theme = useTheme()
  const { toggleColorMode } = useColorMode()
  const [message, setMessage] = useState<string>('')
  const [starCount, setStarCount] = useState<number | null>(null)
  const [version, setVersion] = useState('0.0.0')
  const [openMenus, setOpenMenus] = useState<Record<string, boolean>>({})
  const [drawerOpen, setDrawerOpen] = useState(true)
  const isMobile = useMediaQuery(theme.breakpoints.down('md'))
  const isSmall = useMediaQuery(theme.breakpoints.down('sm'))
  const isDark = theme.palette.mode === 'dark'

  // 当检测到移动设备时，默认关闭抽屉
  useEffect(() => {
    setDrawerOpen(!isMobile)
  }, [isMobile])

  const getCurrentPage = () => {
    const currentPath = location.pathname
    // 扁平化所有页面配置
    const allPages = PAGE_CONFIGS.flatMap(config =>
      'children' in config ? config.children : [config]
    )
    // 查找匹配的页面
    return allPages.find(
      page =>
        'path' in page &&
        (page.path === currentPath || (currentPath.startsWith(page.path) && page.path !== '/'))
    )
  }

  const getCurrentTitle = () => {
    return getCurrentPage()?.text || '管理面板'
  }

  const handleLogout = () => {
    logout()
    navigate('/login')
  }

  const handleMenuItemClick = (path?: string, key?: string) => {
    if (key && path === undefined) {
      // 如果是带子菜单的项，切换展开状态
      setOpenMenus(prev => ({
        ...prev,
        [key]: !prev[key],
      }))
    } else if (path) {
      // 如果是导航项，跳转到对应路径
      navigate(path)
      // 在移动端上，点击菜单项后自动收起侧边栏
      if (isMobile) {
        setDrawerOpen(false)
      }
    }
  }

  const drawer = (
    <Box className="h-full flex flex-col">
      <Toolbar sx={{ overflow: 'visible' }}>
        <Box
          className="flex items-center w-full justify-between relative pt-4"
          sx={{ overflow: 'visible' }}
        >
          <Typography
            variant="h6"
            noWrap
            className="relative font-sans font-black tracking-[0.2rem] select-none cursor-default text-[1.3rem] transition-transform duration-300 hover:scale-105 mx-auto"
            sx={{
              overflow: 'visible',
              '@keyframes bounce': {
                '0%': { transform: 'translateY(0)' },
                '100%': { transform: 'translateY(-3px)' },
              },
              '@keyframes wave': {
                '0%': { transform: 'rotate(-2deg)' },
                '50%': { transform: 'rotate(2deg)' },
                '100%': { transform: 'rotate(-2deg)' },
              },
              '& .highlight, & .text': {
                display: 'inline-block',
                transition: 'transform 0.3s ease-out',
                transformOrigin: 'center',
                willChange: 'transform',
              },
              '& .highlight': {
                color: theme.palette.primary.main,
                fontWeight: 900,
                fontSize: '1.5rem',
                textShadow:
                  theme.palette.mode === 'dark'
                    ? '0 0 3px rgba(255,255,255,0.15), 0 0 6px rgba(255,100,100,0.1), 0 0 10px rgba(255,100,100,0.1)'
                    : '0 0 10px rgba(0,0,0,0.2), 0 0 20px rgba(0,0,0,0.1)',
                '&:not(:hover)': {
                  animation: 'none',
                  transform: 'translateY(0)',
                  transition: 'all 0.3s ease-out',
                },
              },
              '& .text': {
                fontWeight: 800,
                fontSize: '1.2rem',
                textShadow:
                  theme.palette.mode === 'dark'
                    ? '0 0 3px rgba(255,255,255,0.2)'
                    : '0 0 3px rgba(0,0,0,0.1)',
                '&:not(:hover)': {
                  animation: 'none',
                  transform: 'rotate(0)',
                  transition: 'all 0.3s ease-out',
                },
              },
              '&:hover': {
                '& .highlight': {
                  animation: 'bounce 0.5s ease infinite alternate',
                },
                '& .text': {
                  animation: 'wave 1s ease infinite',
                },
                '& .version-tag': {
                  transform: 'scale(1.05) translateY(-1px)',
                },
              },
            }}
          >
            <span className="highlight">N</span>
            <span className="text">ekro</span> <span className="highlight">A</span>
            <span className="text">gent</span>
            <Chip
              label={`v ${version}`}
              size="small"
              variant="outlined"
              className="version-tag absolute -top-3.5 -right-11 h-4"
              sx={{
                fontSize: '0.65rem',
                letterSpacing: '-0.02em',
                backgroundColor: 'transparent',
                borderColor:
                  theme.palette.mode === 'dark' ? 'rgba(255,255,255,0.2)' : 'rgba(0,0,0,0.15)',
                color:
                  theme.palette.mode === 'dark'
                    ? theme.palette.primary.light
                    : theme.palette.primary.main,
                transition: 'transform 0.3s ease',
                transform: 'scale(1)',
                '.MuiChip-label': {
                  px: 0.5,
                  py: 0,
                  lineHeight: 1,
                },
              }}
            />
          </Typography>
        </Box>
      </Toolbar>
      <List className="flex-grow overflow-y-auto">
        {menuItems.map(item => (
          <Box key={item.text}>
            <ListItem disablePadding>
              <ListItemButton
                onClick={() => handleMenuItemClick(item.path, item.key)}
                selected={!item.children && location.pathname === item.path}
                sx={{
                  '&.Mui-selected': {
                    backgroundColor: isDark ? 'rgba(240, 84, 84, 0.15)' : 'rgba(234, 82, 82, 0.08)',
                    borderLeft: `3px solid ${theme.palette.primary.main}`,
                    '&:hover': {
                      backgroundColor: isDark
                        ? 'rgba(240, 84, 84, 0.25)'
                        : 'rgba(234, 82, 82, 0.12)',
                    },
                  },
                  '&:hover': {
                    backgroundColor:
                      theme.palette.mode === 'dark'
                        ? 'rgba(240, 84, 84, 0.08)'
                        : 'rgba(234, 82, 82, 0.05)',
                  },
                  py: isSmall ? 1 : 1.5,
                  borderLeft: '3px solid transparent',
                  transition: 'all 0.2s ease-in-out',
                }}
              >
                <ListItemIcon>{item.icon}</ListItemIcon>
                <ListItemText
                  primary={item.text}
                  primaryTypographyProps={{
                    fontSize: isSmall ? '0.9rem' : 'inherit',
                    whiteSpace: 'nowrap',
                  }}
                />
                {item.children &&
                  item.key &&
                  (openMenus[item.key] ? <ExpandLessIcon /> : <ExpandMoreIcon />)}
              </ListItemButton>
            </ListItem>
            {item.children && item.key && (
              <Collapse in={openMenus[item.key]} timeout="auto" unmountOnExit>
                <List component="div" disablePadding>
                  {item.children.map(child => (
                    <ListItemButton
                      key={child.text}
                      onClick={() => {
                        navigate(child.path)
                        if (isMobile) {
                          setDrawerOpen(false)
                        }
                      }}
                      selected={location.pathname === child.path}
                      sx={{
                        pl: 4,
                        py: isSmall ? 0.75 : 1.5,
                        '&.Mui-selected': {
                          backgroundColor: isDark
                            ? 'rgba(240, 84, 84, 0.15)'
                            : 'rgba(234, 82, 82, 0.08)',
                          borderLeft: `3px solid ${theme.palette.primary.main}`,
                          '&:hover': {
                            backgroundColor: isDark
                              ? 'rgba(240, 84, 84, 0.25)'
                              : 'rgba(234, 82, 82, 0.12)',
                          },
                        },
                        '&:hover': {
                          backgroundColor:
                            theme.palette.mode === 'dark'
                              ? 'rgba(240, 84, 84, 0.08)'
                              : 'rgba(234, 82, 82, 0.05)',
                        },
                        borderLeft: '3px solid transparent',
                        transition: 'all 0.2s ease-in-out',
                      }}
                    >
                      <ListItemIcon>{child.icon}</ListItemIcon>
                      <ListItemText
                        primary={child.text}
                        primaryTypographyProps={{
                          fontSize: isSmall ? '0.85rem' : 'inherit',
                          whiteSpace: 'nowrap',
                        }}
                      />
                    </ListItemButton>
                  ))}
                </List>
              </Collapse>
            )}
          </Box>
        ))}
      </List>
      <List>
        <ListItem disablePadding>
          <ListItemButton
            onClick={handleLogout}
            sx={{
              py: isSmall ? 1 : 1.5, // 在移动端调整垂直内边距
              '&:hover': {
                backgroundColor:
                  theme.palette.mode === 'dark' ? 'rgba(255,255,255,0.07)' : 'rgba(0,0,0,0.04)',
              },
              transition: 'all 0.2s ease-in-out',
            }}
          >
            <ListItemIcon>
              <LogoutIcon />
            </ListItemIcon>
            <ListItemText
              primary="退出登录"
              secondary={userInfo?.username}
              primaryTypographyProps={{
                fontSize: isSmall ? '0.9rem' : 'inherit',
              }}
              secondaryTypographyProps={{
                fontSize: isSmall ? '0.75rem' : 'inherit',
              }}
            />
          </ListItemButton>
        </ListItem>
      </List>
      <Box className="pb-2 -mt-2 text-center">
        <Typography variant="caption" color="text.secondary">
          © {new Date().getFullYear()}{' '}
          <Link
            href="https://github.com/KroMiose/nekro-agent"
            target="_blank"
            rel="noopener noreferrer"
          >
            NekroAgent
          </Link>
          . 版权所有.
        </Typography>
      </Box>
    </Box>
  )

  useEffect(() => {
    fetch('https://api.github.com/repos/KroMiose/nekro-agent')
      .then(response => response.json())
      .then(data => {
        if (data.stargazers_count) {
          setStarCount(data.stargazers_count)
        }
      })
      .catch(() => {
        // 如果获取失败，保持为 null
      })
  }, [])

  useEffect(() => {
    // 获取版本信息
    configApi
      .getVersion()
      .then(version => {
        setVersion(version)
      })
      .catch(() => {
        setVersion('0.0.0')
      })
  }, [])

  return (
    <Box
      className="flex"
      sx={{
        background: isDark ? GRADIENTS.BACKGROUND.DARK.PRIMARY : GRADIENTS.BACKGROUND.LIGHT.PRIMARY,
        minHeight: '100vh',
        transition: 'background 0.5s ease',
      }}
    >
      <AppBar
        position="fixed"
        sx={{
          width: {
            xs: '100%',
            md: drawerOpen ? `calc(100% - 240px)` : '100%',
          },
          ml: {
            xs: 0,
            md: drawerOpen ? '240px' : 0,
          },
          transition: theme =>
            theme.transitions.create(['width', 'margin-left'], {
              easing: theme.transitions.easing.sharp,
              duration: theme.transitions.duration.leavingScreen,
            }),
          backdropFilter: 'blur(8px)',
          backgroundColor: 'transparent',
          backgroundImage: isDark ? GRADIENTS.APP_BAR.DARK : GRADIENTS.APP_BAR.LIGHT,
          boxShadow: isDark ? SHADOWS.APP_BAR.DARK : SHADOWS.APP_BAR.LIGHT,
          borderBottom: isDark ? '1px solid rgba(234, 82, 82, 0.15)' : 'none',
          color: isDark ? theme.palette.text.primary : theme.palette.primary.contrastText,
          zIndex: theme.zIndex.drawer + 1,
        }}
      >
        <Toolbar sx={{ minHeight: { xs: 56, sm: 64 } }}>
          <IconButton
            color="inherit"
            edge="start"
            onClick={() => setDrawerOpen(!drawerOpen)}
            sx={{ mr: 2 }}
            aria-label={drawerOpen ? '收起侧边栏' : '展开侧边栏'}
          >
            {drawerOpen && isMobile ? <ChevronLeftIcon /> : <MenuIcon />}
          </IconButton>
          <Box className="flex items-center gap-2 flex-grow select-none overflow-hidden">
            {getCurrentPage()?.icon}
            <Typography
              variant="h6"
              noWrap
              component="div"
              className="font-medium select-none text-ellipsis overflow-hidden"
              sx={{
                color: 'inherit',
                fontSize: { xs: '1rem', sm: '1.25rem' },
                textShadow:
                  theme.palette.mode === 'dark'
                    ? '0 0 2px rgba(255,255,255,0.15)'
                    : '0 0 2px rgba(0,0,0,0.15)',
              }}
            >
              {getCurrentTitle()}
            </Typography>
          </Box>
          <Tooltip title={theme.palette.mode === 'dark' ? '切换到亮色模式' : '切换到暗色模式'}>
            <IconButton onClick={toggleColorMode} color="inherit">
              {theme.palette.mode === 'dark' ? <Brightness7Icon /> : <Brightness4Icon />}
            </IconButton>
          </Tooltip>
          <Button
            variant="text"
            color="inherit"
            size={isSmall ? 'small' : 'large'}
            startIcon={<GitHubIcon />}
            onClick={() => window.open('https://github.com/KroMiose/nekro-agent', '_blank')}
            className="normal-case transition-colors"
            sx={{
              mr: { xs: 0, sm: 1 },
              ml: { xs: 1, sm: 2 },
              minWidth: { xs: 'auto', sm: '100px' },
              '& .MuiButton-startIcon': {
                mr: { xs: 0, sm: 1 },
              },
              '&:hover': {
                backgroundColor:
                  theme.palette.mode === 'dark'
                    ? 'rgba(255, 255, 255, 0.1)'
                    : 'rgba(255, 255, 255, 0.2)',
              },
            }}
          >
            <Box sx={{ display: { xs: 'none', sm: 'block' } }}>
              Stars {starCount !== null ? starCount : '...'}
            </Box>
          </Button>
        </Toolbar>
      </AppBar>
      <Box
        component="nav"
        sx={{
          width: { sm: drawerOpen ? 240 : 0 },
          flexShrink: { sm: 0 },
          transition: theme =>
            theme.transitions.create('width', {
              easing: theme.transitions.easing.sharp,
              duration: theme.transitions.duration.enteringScreen,
            }),
        }}
      >
        <Drawer
          variant={isMobile ? 'temporary' : 'permanent'}
          open={drawerOpen}
          onClose={() => setDrawerOpen(false)}
          sx={{
            '& .MuiDrawer-paper': {
              boxSizing: 'border-box',
              width: 240,
              transition: theme =>
                theme.transitions.create('width', {
                  easing: theme.transitions.easing.sharp,
                  duration: theme.transitions.duration.enteringScreen,
                }),
            },
            display: { xs: 'block', sm: drawerOpen ? 'block' : 'none' },
          }}
        >
          {drawer}
        </Drawer>
      </Box>
      <Box
        component="main"
        className="flex-grow p-3 h-screen overflow-hidden flex flex-col"
        sx={{
          width: {
            xs: '100%',
            md: drawerOpen ? 'calc(100% - 240px)' : '100%',
          },
          transition: theme =>
            theme.transitions.create('width', {
              easing: theme.transitions.easing.sharp,
              duration: theme.transitions.duration.enteringScreen,
            }),
        }}
      >
        <Toolbar sx={{ flexShrink: 0, minHeight: { xs: 56, sm: 64 } }} />
        <motion.div
          key={location.key}
          initial={{ opacity: 0, x: 20, scale: 0.98 }}
          animate={{ opacity: 1, x: 0, scale: 1 }}
          transition={{
            duration: 0.36,
            ease: [0.4, 0, 0.2, 1],
          }}
          className="h-full flex-grow overflow-auto bg-transparent"
        >
          <Outlet />
        </motion.div>
      </Box>

      <Snackbar
        open={!!message}
        autoHideDuration={3000}
        onClose={() => setMessage('')}
        anchorOrigin={{ vertical: 'top', horizontal: 'center' }}
      >
        <Alert onClose={() => setMessage('')} severity="info" variant="filled" className="w-full">
          {message}
        </Alert>
      </Snackbar>
    </Box>
  )
}
