import { useState } from 'react'
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
} from '@mui/icons-material'
import { useAuthStore } from '../stores/auth'
import { useTheme } from '@mui/material/styles'
import { useColorMode } from '../stores/theme'

const drawerWidth = 240

const menuItems = [
  { text: '系统日志', icon: <TerminalIcon />, path: '/logs' },
  { text: '扩展管理', icon: <ExtensionIcon />, path: '/extensions' },
  // { text: '沙盒日志', icon: <CodeIcon />, path: '/sandbox-logs' },
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
        <Typography variant="h6" noWrap>
          Nekro Agent
        </Typography>
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
        }}
      >
        <Toolbar />
        <Outlet />
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
