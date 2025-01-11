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
  Menu as MenuIcon,
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

const drawerWidth = 240

const menuItems = [
  { text: '系统日志', icon: <TerminalIcon />, path: '/logs' },
  { text: '扩展管理', icon: <ExtensionIcon />, path: '/extensions' },
  { text: '沙盒日志', icon: <CodeIcon />, path: '/sandbox-logs' },
  {
    text: '协议端',
    icon: <ChatIcon />,
    path: undefined,
    children: [{ text: 'NapCat', icon: <ChatIcon />, path: '/protocols/napcat' }],
  },
  {
    text: '系统配置',
    icon: <SettingsIcon />,
    path: undefined,
    children: [
      { text: '基本配置', icon: <TuneIcon />, path: '/settings' },
      { text: '模型组', icon: <StorageIcon />, path: '/settings/model-groups' },
    ],
  },
  { text: '个人中心', icon: <PersonIcon />, path: '/profile' },
]

export default function MainLayout() {
  const navigate = useNavigate()
  const location = useLocation()
  const [mobileOpen, setMobileOpen] = useState(false)
  const [settingsOpen, setSettingsOpen] = useState(true)
  const [protocolsOpen, setProtocolsOpen] = useState(true)
  const { userInfo, logout } = useAuthStore()
  const theme = useTheme()
  const { toggleColorMode } = useColorMode()
  const [message, setMessage] = useState<string>('')
  const [starCount, setStarCount] = useState<number | null>(null)
  const [version, setVersion] = useState('0.0.0')

  const getCurrentTitle = () => {
    const currentPath = location.pathname
    if (currentPath.startsWith('/settings/model-groups')) {
      return '模型组'
    }
    if (currentPath === '/settings') {
      return '基本配置'
    }
    if (currentPath === '/extensions') {
      return '扩展管理'
    }
    if (currentPath === '/protocols/napcat') {
      return 'NapCat'
    }
    if (currentPath === '/sandbox-logs') {
      return '沙盒日志'
    }
    if (currentPath === '/profile') {
      return '个人中心'
    }
    const currentMenu = menuItems.find(item => item.path && currentPath.startsWith(item.path))
    return currentMenu?.text || '管理面板'
  }

  const handleDrawerToggle = () => {
    setMobileOpen(!mobileOpen)
  }

  const handleLogout = () => {
    logout()
    navigate('/login')
  }

  const drawer = (
    <Box sx={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
      <Toolbar>
        <Box sx={{ 
          display: 'flex', 
          alignItems: 'center', 
          width: '100%', 
          justifyContent: 'center',
          position: 'relative',
          overflow: 'visible',
          ml: -0.75,
        }}>
          <Typography
            variant="h6"
            noWrap
            sx={{
              position: 'relative',
              overflow: 'visible',
              fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif',
              fontWeight: 900,
              letterSpacing: '.2rem',
              userSelect: 'none',
              cursor: 'default',
              fontSize: '1.3rem',
              transition: 'transform 0.3s ease',
              '&:hover': {
                transform: 'scale(1.05)',
                '& .highlight': {
                  animation: 'bounce 0.5s ease infinite alternate'
                },
                '& .text': {
                  animation: 'wave 1s ease infinite'
                },
                '& .version-tag': {
                  transform: 'scale(1.05) translateY(-1px)'
                }
              },
              '@keyframes bounce': {
                '0%': {
                  transform: 'translateY(0)'
                },
                '100%': {
                  transform: 'translateY(-3px)'
                }
              },
              '@keyframes wave': {
                '0%, 100%': {
                  transform: 'rotate(-2deg)'
                },
                '50%': {
                  transform: 'rotate(2deg)'
                }
              },
              '& .highlight, & .text': {
                display: 'inline-block',
                transition: 'transform 0.3s ease-out',
                transformOrigin: 'center',
                willChange: 'transform'
              },
              '& .highlight': {
                color: theme.palette.primary.main,
                fontWeight: 900,
                fontSize: '1.5rem',
                textShadow: theme.palette.mode === 'dark' 
                  ? '0 0 10px rgba(255,255,255,0.3), 0 0 20px rgba(255,255,255,0.2), 0 0 30px rgba(255,255,255,0.1)'
                  : '0 0 10px rgba(0,0,0,0.2), 0 0 20px rgba(0,0,0,0.1)',
                '&:not(:hover)': {
                  animation: 'none',
                  transform: 'translateY(0)',
                  transition: 'all 0.3s ease-out'
                }
              },
              '& .text': {
                fontWeight: 800,
                fontSize: '1.2rem',
                textShadow: theme.palette.mode === 'dark'
                  ? '0 0 5px rgba(255,255,255,0.2)'
                  : '0 0 5px rgba(0,0,0,0.1)',
                '&:not(:hover)': {
                  animation: 'none',
                  transform: 'rotate(0)',
                  transition: 'all 0.3s ease-out'
                }
              }
            }}
          >
            <span className="highlight">N</span>
            <span className="text">ekro</span>
            {' '}
            <span className="highlight">A</span>
            <span className="text">gent</span>
            <Chip
              label={`v ${version}`}
              size="small"
              variant="outlined"
              className="version-tag"
              sx={{
                position: 'absolute',
                top: '-6px',
                right: '-32px',
                height: '16px',
                fontSize: '0.65rem',
                letterSpacing: '-0.02em',
                backgroundColor: 'transparent',
                borderColor: theme.palette.mode === 'dark' 
                  ? 'rgba(255,255,255,0.2)' 
                  : 'rgba(0,0,0,0.15)',
                color: theme.palette.mode === 'dark'
                  ? theme.palette.primary.light
                  : theme.palette.primary.main,
                transition: 'transform 0.3s ease',
                transform: 'scale(1)',
                '.MuiChip-label': {
                  px: 0.5,
                  py: 0,
                  lineHeight: 1
                }
              }}
            />
          </Typography>
        </Box>
      </Toolbar>
      <List sx={{ flexGrow: 1 }}>
        {menuItems.map(item => (
          <Box key={item.text}>
            <ListItem disablePadding>
              <ListItemButton
                onClick={() => {
                  if (item.children) {
                    if (item.text === '系统配置') {
                      setSettingsOpen(!settingsOpen)
                    } else if (item.text === '协议端') {
                      setProtocolsOpen(!protocolsOpen)
                    }
                  } else {
                    navigate(item.path)
                  }
                }}
                selected={!item.children && location.pathname === item.path}
              >
                <ListItemIcon>{item.icon}</ListItemIcon>
                <ListItemText primary={item.text} />
                {item.children &&
                  (item.text === '系统配置' ? (
                    settingsOpen ? (
                      <ExpandLessIcon />
                    ) : (
                      <ExpandMoreIcon />
                    )
                  ) : protocolsOpen ? (
                    <ExpandLessIcon />
                  ) : (
                    <ExpandMoreIcon />
                  ))}
              </ListItemButton>
            </ListItem>
            {item.children && (
              <Collapse
                in={item.text === '系统配置' ? settingsOpen : protocolsOpen}
                timeout="auto"
                unmountOnExit
              >
                <List component="div" disablePadding>
                  {item.children.map(child => (
                    <ListItemButton
                      key={child.text}
                      sx={{ pl: 4 }}
                      onClick={() => navigate(child.path)}
                      selected={location.pathname === child.path}
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
          <ListItemButton onClick={handleLogout}>
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
    configApi.getVersion()
      .then(version => {
        setVersion(version)
      })
      .catch(() => {
        setVersion('0.0.0')
      })
  }, [])

  return (
    <Box sx={{ display: 'flex' }}>
      <AppBar
        position="fixed"
        sx={{
          width: { sm: `calc(100% - ${drawerWidth}px)` },
          ml: { sm: `${drawerWidth}px` },
        }}
      >
        <Toolbar>
          <IconButton
            color="inherit"
            edge="start"
            onClick={handleDrawerToggle}
            sx={{ mr: 2, display: { sm: 'none' } }}
          >
            <MenuIcon />
          </IconButton>
          <Typography variant="h6" noWrap component="div" sx={{ flexGrow: 1 }}>
            {getCurrentTitle()}
          </Typography>
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
            sx={{
              mr: 1,
              textTransform: 'none',
              minWidth: '100px',
              '&:hover': {
                backgroundColor: 'rgba(255, 255, 255, 0.1)',
              },
            }}
          >
            Stars {starCount !== null ? starCount : '...'}
          </Button>
        </Toolbar>
      </AppBar>
      <Box component="nav" sx={{ width: { sm: drawerWidth }, flexShrink: { sm: 0 } }}>
        <Drawer
          variant="temporary"
          open={mobileOpen}
          onClose={handleDrawerToggle}
          ModalProps={{
            keepMounted: true,
          }}
          sx={{
            display: { xs: 'block', sm: 'none' },
            '& .MuiDrawer-paper': {
              boxSizing: 'border-box',
              width: drawerWidth,
            },
          }}
        >
          {drawer}
        </Drawer>
        <Drawer
          variant="permanent"
          sx={{
            display: { xs: 'none', sm: 'block' },
            '& .MuiDrawer-paper': {
              boxSizing: 'border-box',
              width: drawerWidth,
            },
          }}
          open
        >
          {drawer}
        </Drawer>
      </Box>
      <Box
        component="main"
        sx={{
          flexGrow: 1,
          p: 3,
          width: { sm: `calc(100% - ${drawerWidth}px)` },
          height: '100vh',
          overflow: 'hidden',
          display: 'flex',
          flexDirection: 'column',
        }}
      >
        <Toolbar sx={{ flexShrink: 0 }} />
        <Box sx={{ flexGrow: 1, overflow: 'hidden', minHeight: 0 }}>
          <Outlet />
        </Box>
      </Box>

      <Snackbar
        open={!!message}
        autoHideDuration={3000}
        onClose={() => setMessage('')}
        anchorOrigin={{ vertical: 'top', horizontal: 'center' }}
      >
        <Alert
          onClose={() => setMessage('')}
          severity="info"
          variant="filled"
          sx={{ width: '100%' }}
        >
          {message}
        </Alert>
      </Snackbar>
    </Box>
  )
}
