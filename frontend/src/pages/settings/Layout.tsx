import { useState } from 'react'
import { Outlet, useNavigate, useLocation } from 'react-router-dom'
import { Box, Paper, Tabs, Tab, Alert, Snackbar, useTheme, useMediaQuery } from '@mui/material'

export default function SettingsLayout() {
  const navigate = useNavigate()
  const location = useLocation()
  const [message, setMessage] = useState<string>('')
  const theme = useTheme()
  const isMobile = useMediaQuery(theme.breakpoints.down('md'))
  const isSmall = useMediaQuery(theme.breakpoints.down('sm'))

  // 获取当前激活的标签
  const currentTab = location.pathname === '/settings' ? 0 : 1

  // 处理标签切换
  const handleTabChange = (_: React.SyntheticEvent, newValue: number) => {
    navigate(newValue === 0 ? '/settings' : '/settings/model-groups')
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
          value={currentTab} 
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

      {/* 消息提示 */}
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
