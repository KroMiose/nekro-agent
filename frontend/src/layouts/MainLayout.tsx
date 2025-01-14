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
  Person as PersonIcon,
  GitHub as GitHubIcon,
} from '@mui/icons-material'
import { useAuthStore } from '../stores/auth'
import { useTheme } from '@mui/material/styles'
import { useColorMode } from '../stores/theme'
import { configApi } from '../services/api/config'
import { motion } from 'framer-motion'

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
  { path: '/logs', text: '系统日志', icon: <TerminalIcon /> },
  { path: '/extensions', text: '扩展管理', icon: <ExtensionIcon /> },
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
  { path: '/profile', text: '个人中心', icon: <PersonIcon /> },
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
  const [openMenus, setOpenMenus] = useState<Record<string, boolean>>({
    protocols: true,
    settings: true,
  })

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

  const drawer = (
    <Box className="h-full flex flex-col">
      <Toolbar sx={{ overflow: 'visible' }}>
        <Box
          className="flex items-center w-full justify-center relative -ml-3"
          sx={{ overflow: 'visible' }}
        >
          <Typography
            variant="h6"
            noWrap
            className="relative font-sans font-black tracking-[0.2rem] select-none cursor-default text-[1.3rem] transition-transform duration-300 hover:scale-105"
            sx={{
              overflow: 'visible',
              '@keyframes bounce': {
                '0%': { transform: 'translateY(0)' },
                '100%': { transform: 'translateY(-3px)' },
              },
              '@keyframes wave': {
                '0%, 100%': { transform: 'rotate(-2deg)' },
                '50%': { transform: 'rotate(2deg)' },
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
                    ? '0 0 2px rgba(255,255,255,0.2), 0 0 2px rgba(255,255,255,0.2), 0 0 3px rgba(255,255,255,0.1)'
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
              className="version-tag absolute -top-1.5 -right-10 h-4"
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
      <List className="flex-grow">
        {menuItems.map(item => (
          <Box key={item.text}>
            <ListItem disablePadding>
              <ListItemButton
                onClick={() => {
                  if (item.children && item.key) {
                    setOpenMenus(prev => ({
                      ...prev,
                      [item.key]: !prev[item.key],
                    }))
                  } else {
                    navigate(item.path!)
                  }
                }}
                selected={!item.children && location.pathname === item.path}
                sx={{
                  '&.Mui-selected': {
                    backgroundColor:
                      theme.palette.mode === 'dark' ? 'rgba(255,255,255,0.08)' : 'rgba(0,0,0,0.05)',
                    '&:hover': {
                      backgroundColor:
                        theme.palette.mode === 'dark'
                          ? 'rgba(255,255,255,0.12)'
                          : 'rgba(0,0,0,0.08)',
                    },
                  },
                  '&:hover': {
                    backgroundColor:
                      theme.palette.mode === 'dark' ? 'rgba(255,255,255,0.05)' : 'rgba(0,0,0,0.03)',
                  },
                }}
              >
                <ListItemIcon>{item.icon}</ListItemIcon>
                <ListItemText primary={item.text} />
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
                      onClick={() => navigate(child.path)}
                      selected={location.pathname === child.path}
                      sx={{
                        pl: 4,
                        '&.Mui-selected': {
                          backgroundColor:
                            theme.palette.mode === 'dark'
                              ? 'rgba(255,255,255,0.08)'
                              : 'rgba(0,0,0,0.05)',
                          '&:hover': {
                            backgroundColor:
                              theme.palette.mode === 'dark'
                                ? 'rgba(255,255,255,0.12)'
                                : 'rgba(0,0,0,0.08)',
                          },
                        },
                        '&:hover': {
                          backgroundColor:
                            theme.palette.mode === 'dark'
                              ? 'rgba(255,255,255,0.05)'
                              : 'rgba(0,0,0,0.03)',
                        },
                      }}
                    >
                      <ListItemIcon>{child.icon}</ListItemIcon>
                      <ListItemText primary={child.text} />
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
              '&:hover': {
                backgroundColor:
                  theme.palette.mode === 'dark' ? 'rgba(255,255,255,0.05)' : 'rgba(0,0,0,0.03)',
              },
            }}
          >
            <ListItemIcon>
              <LogoutIcon />
            </ListItemIcon>
            <ListItemText primary="退出登录" secondary={userInfo?.username} />
          </ListItemButton>
        </ListItem>
      </List>
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
    <Box className="flex">
      <AppBar
        position="fixed"
        sx={{
          width: { xs: '100%', sm: `calc(100% - 240px)` },
          ml: { xs: 0, sm: '240px' },
          backdropFilter: 'blur(8px)',
          backgroundColor:
            theme.palette.mode === 'dark'
              ? theme.palette.background.default
              : theme.palette.primary.main,
          boxShadow:
            theme.palette.mode === 'dark'
              ? '0 1px 3px 0 rgba(0, 0, 0, 0.4)'
              : '0 1px 3px 0 rgba(0, 0, 0, 0.1)',
          color:
            theme.palette.mode === 'dark'
              ? theme.palette.text.primary
              : theme.palette.primary.contrastText,
          zIndex: theme.zIndex.drawer + 1,
        }}
      >
        <Toolbar>
          <Box className="flex items-center gap-2 flex-grow select-none">
            {getCurrentPage()?.icon}
            <Typography
              variant="h6"
              noWrap
              component="div"
              className="font-medium select-none"
              sx={{
                color: 'inherit',
                textShadow:
                  theme.palette.mode === 'dark'
                    ? '0 0 2px rgba(255,255,255,0.1)'
                    : '0 0 2px rgba(0,0,0,0.1)',
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
            size="large"
            startIcon={<GitHubIcon />}
            onClick={() => window.open('https://github.com/KroMiose/nekro-agent', '_blank')}
            className="mr-1 normal-case min-w-[100px] transition-colors"
            sx={{
              '&:hover': {
                backgroundColor:
                  theme.palette.mode === 'dark'
                    ? 'rgba(255, 255, 255, 0.1)'
                    : 'rgba(255, 255, 255, 0.2)',
              },
            }}
          >
            Stars {starCount !== null ? starCount : '...'}
          </Button>
        </Toolbar>
      </AppBar>
      <Box component="nav" sx={{ width: { sm: 240 }, flexShrink: { sm: 0 } }}>
        <Drawer
          variant="permanent"
          sx={{
            '& .MuiDrawer-paper': {
              boxSizing: 'border-box',
              width: 240,
            },
          }}
          open
        >
          {drawer}
        </Drawer>
      </Box>
      <Box
        component="main"
        className="flex-grow p-3 sm:w-[calc(100%-240px)] h-screen overflow-hidden flex flex-col"
      >
        <Toolbar className="flex-shrink-0" />
        <motion.div
          key={location.key}
          initial={{ opacity: 0, x: 20, scale: 0.93 }}
          animate={{ opacity: 1, x: 0, scale: 1 }}
          transition={{
            duration: 0.36,
            ease: [0.4, 0, 0.2, 1],
          }}
          className="h-full flex-grow overflow-auto"
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
