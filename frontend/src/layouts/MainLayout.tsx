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
  Collapse,
  Button,
  Chip,
  Link,
  useMediaQuery,
  useTheme,
} from '@mui/material'
import {
  Logout as LogoutIcon,
  ExpandLess as ExpandLessIcon,
  ExpandMore as ExpandMoreIcon,
  GitHub as GitHubIcon,
  Menu as MenuIcon,
  ChevronLeft as ChevronLeftIcon,
} from '@mui/icons-material'
import { useAuthStore } from '../stores/auth'
import { configApi } from '../services/api/config'
import { motion } from 'framer-motion'
import { UI_STYLES, getAnimationDuration } from '../theme/themeApi'
import ThemeToggleButton from '../theme/ThemeToggleButton'
import { useNotification } from '../hooks/useNotification'
import { alpha } from '@mui/material/styles'
import { CHIP_VARIANTS } from '../theme/variants'
import { useWallpaperStore } from '../stores/wallpaper'
import WallpaperBackground from '../components/common/WallpaperBackground'
import {
  createMenuItems,
  getCurrentPageFromConfigs,
  getCurrentTitleFromConfigs,
} from '../config/navigation'

// 获取菜单项配置
const menuItems = createMenuItems()

export default function MainLayout() {
  const navigate = useNavigate()
  const location = useLocation()
  const { userInfo, logout } = useAuthStore()
  const theme = useTheme()
  const [starCount, setStarCount] = useState<number | null>(null)
  const [version, setVersion] = useState('0.0.0')
  const [openMenus, setOpenMenus] = useState<Record<string, boolean>>({})
  const [drawerOpen, setDrawerOpen] = useState(true)
  const isMobile = useMediaQuery(theme.breakpoints.down('md'))
  const isSmall = useMediaQuery(theme.breakpoints.down('sm'))
  const notification = useNotification()

  // 使用壁纸store
  const { mainWallpaper, mainWallpaperMode, mainWallpaperBlur, mainWallpaperDim } =
    useWallpaperStore()

  // 当检测到移动设备时，默认关闭抽屉
  useEffect(() => {
    setDrawerOpen(!isMobile)
  }, [isMobile])

  // 自动展开包含当前路由的菜单项
  useEffect(() => {
    menuItems.forEach(item => {
      if (item.children && item.key) {
        const hasActiveChild = item.children.some(child => 
          location.pathname === child.path || 
          location.pathname.startsWith(child.path + '/')
        )
        if (hasActiveChild) {
          setOpenMenus(prev => ({
            ...prev,
            [item.key]: true,
          }))
        }
      }
    })
  }, [location.pathname])

  const getCurrentPage = () => {
    return getCurrentPageFromConfigs(location.pathname)
  }

  const getCurrentTitle = () => {
    return getCurrentTitleFromConfigs(location.pathname)
  }

  const handleLogout = () => {
    logout()
    navigate('/login')
    notification.info('已退出登录')
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
                  '0 0 10px rgba(255,255,255,0.1), 0 0 20px rgba(255,100,100,0.05), 0 0 30px rgba(255,100,100,0.05)',
                '&:not(:hover)': {
                  animation: 'none',
                  transform: 'translateY(0)',
                  transition: 'all 0.3s ease-out',
                },
              },
              '& .text': {
                fontWeight: 800,
                fontSize: '1.2rem',
                textShadow: '0 0 5px rgba(255,255,255,0.15)',
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
              className="version-tag absolute -top-3.5 -right-9 h-4"
              sx={{
                ...CHIP_VARIANTS.base(true),
                fontSize: '0.65rem',
                letterSpacing: '-0.02em',
                backgroundColor: theme.palette.background.paper,
                borderColor: 'rgba(255,255,255,0.2)',
                color: theme.palette.primary.light,
                transition: 'transform 0.3s ease',
                transform: 'scale(1)',
                height: '18px',
                minWidth: 'auto',
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
                selected={Boolean(!item.children && (
                  location.pathname === item.path || 
                  (item.path && location.pathname.startsWith(item.path + '/'))
                ))}
                sx={{
                  '&.Mui-selected': {
                    backgroundColor: UI_STYLES.SELECTED,
                    borderLeft: UI_STYLES.BORDERS.MENU.ACTIVE,
                    '&:hover': {
                      backgroundColor: UI_STYLES.SELECTED_HOVER,
                    },
                  },
                  '&:hover': {
                    backgroundColor: UI_STYLES.HOVER,
                  },
                  py: 1,
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
                      selected={Boolean(
                        location.pathname === child.path ||
                        location.pathname.startsWith(child.path + '/')
                      )}
                      sx={{
                        pl: 4,
                        py: isSmall ? 0.75 : 1,
                        '&.Mui-selected': {
                          backgroundColor: UI_STYLES.SELECTED,
                          borderLeft: UI_STYLES.BORDERS.MENU.ACTIVE,
                          '&:hover': {
                            backgroundColor: UI_STYLES.SELECTED_HOVER,
                          },
                        },
                        '&:hover': {
                          backgroundColor: UI_STYLES.HOVER,
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
                backgroundColor: UI_STYLES.HOVER,
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
      <Box
        className="pb-2 -mt-2 text-center border-t"
        sx={{ borderColor: 'rgba(128,128,128,0.2)' }}
      >
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
        position: 'relative',
        background: UI_STYLES.BACKGROUND.PRIMARY,
        backgroundColor: theme.palette.mode === 'dark' ? '#181818' : '#f8f8f8',
        minHeight: '100vh',
        transition: 'background 0.5s ease',
        padding: 0,
      }}
    >
      {/* 壁纸背景组件 */}
      {mainWallpaper && (
        <Box
          sx={{
            position: 'absolute',
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            zIndex: 0,
            overflow: 'hidden',
          }}
        >
          <WallpaperBackground
            wallpaperUrl={mainWallpaper}
            mode={mainWallpaperMode as 'cover' | 'contain' | 'repeat' | 'center'}
            blur={mainWallpaperBlur}
            dim={mainWallpaperDim}
          />
        </Box>
      )}

      {/* 其余布局内容，添加相对定位确保在壁纸上层 */}
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
          backdropFilter: 'blur(12px)',
          backgroundColor: 'transparent',
          backgroundImage: `linear-gradient(90deg, ${alpha(theme.palette.primary.dark, 0.75)}, ${alpha(theme.palette.primary.main, 0.75)})`,
          boxShadow:
            '0 4px 15px rgba(0, 0, 0, 0.12), 0 1px 3px rgba(0, 0, 0, 0.05), 0 0 10px rgba(0, 0, 0, 0.03)',
          borderBottom:
            theme.palette.mode === 'dark' ? `1px solid rgba(255, 255, 255, 0.08)` : 'none',
          color: 'inherit',
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
                textShadow: '0 0 2px rgba(255,255,255,0.15)',
              }}
            >
              {getCurrentTitle()}
            </Typography>
          </Box>

          <ThemeToggleButton />

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
                backgroundColor: 'rgba(255, 255, 255, 0.2)',
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
              backgroundColor: theme =>
                theme.palette.mode === 'dark'
                  ? alpha(theme.palette.background.paper, 0.68)
                  : alpha(theme.palette.background.paper, 0.86),
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
        className="flex-grow h-screen overflow-hidden flex flex-col"
        sx={{
          position: 'relative',
          zIndex: 1, // 确保主内容在壁纸上层
          width: {
            xs: '100%',
            md: drawerOpen ? 'calc(100% - 240px)' : '100%',
          },
          padding: 0,
          transition: theme =>
            theme.transitions.create('width', {
              easing: theme.transitions.easing.sharp,
              duration: theme.transitions.duration.enteringScreen,
            }),
        }}
      >
        <Toolbar sx={{ flexShrink: 0, minHeight: { xs: 56, sm: 64 } }} />
        <motion.div
          key={location.pathname.split('/').slice(0, 3).join('/')}
          initial={{ opacity: 0, x: 20, scale: 0.98 }}
          animate={{ opacity: 1, x: 0, scale: 1 }}
          transition={{
            duration: getAnimationDuration(0.36),
            ease: [0.4, 0, 0.2, 1],
          }}
          className="h-full flex-grow overflow-auto rounded-xl performance-adaptive motion-div"
          style={{
            position: 'relative',
            overflow: 'hidden',
          }}
        >
          <div
            style={{
              position: 'absolute',
              top: 0,
              left: 0,
              right: 0,
              height: '2px',
              background: `linear-gradient(90deg, 
                ${alpha(theme.palette.primary.main, 0.3)}, 
                ${alpha(theme.palette.secondary.main, 0.3)})`,
              opacity: 0.4,
              zIndex: 1,
            }}
          />
          <Outlet />
        </motion.div>
      </Box>
    </Box>
  )
}
