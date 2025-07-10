import { Outlet, useNavigate, useLocation } from 'react-router-dom'
import { Box, Paper, Tabs, Tab, useTheme, useMediaQuery } from '@mui/material'

export default function SettingsLayout() {
  const navigate = useNavigate()
  const location = useLocation()
  const theme = useTheme()
  const isMobile = useMediaQuery(theme.breakpoints.down('md'))
  const isSmall = useMediaQuery(theme.breakpoints.down('sm'))

  // 获取当前激活的标签
  const getActiveTab = () => {
    const path = location.pathname
    if (path === '/settings') return 0
    if (path === '/settings/model-groups') return 1
    if (path === '/settings/theme') return 2
    return 0
  }

  // 处理标签切换
  const handleTabChange = (_: React.SyntheticEvent, newValue: number) => {
    switch (newValue) {
      case 0:
        navigate('/settings')
        break
      case 1:
        navigate('/settings/model-groups')
        break
      case 2:
        navigate('/settings/theme')
        break
      default:
        navigate('/settings')
    }
  }

  return (
    <Box sx={{ 
      height: '100%', 
      display: 'flex', 
      flexDirection: 'column',
      overflow: 'hidden',
    }}>
      {/* 标签页导航 */}
      <Paper sx={{ mb: 2, flexShrink: 0 }}>
        <Tabs 
          value={getActiveTab()} 
          onChange={handleTabChange}
          variant={isMobile ? "fullWidth" : "standard"}
          centered={!isMobile}
          sx={{
            '& .MuiTab-root': {
              minHeight: isSmall ? 40 : 48,
              fontSize: isSmall ? '0.8rem' : 'inherit',
              minWidth: 0,
              px: isSmall ? 1 : 2,
            }
          }}
        >
          <Tab label="基本配置" />
          <Tab label="模型组" />
          <Tab label="主题设置" />
        </Tabs>
      </Paper>

      {/* 内容区域 */}
      <Box
        sx={{
          flex: 1,
          minHeight: 0,
          overflow: 'hidden',
          display: 'flex',
          flexDirection: 'column',
        }}
      >
        <Outlet />
      </Box>
    </Box>
  )
}
