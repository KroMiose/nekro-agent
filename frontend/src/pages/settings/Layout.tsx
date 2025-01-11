import { useState } from 'react'
import { Outlet, useNavigate, useLocation } from 'react-router-dom'
import {
  Box,
  Paper,
  Tabs,
  Tab,
  Alert,
  Snackbar,
} from '@mui/material'

export default function SettingsLayout() {
  const navigate = useNavigate()
  const location = useLocation()
  const [message, setMessage] = useState<string>('')

  // 获取当前激活的标签
  const currentTab = location.pathname === '/settings' ? 0 : 1

  // 处理标签切换
  const handleTabChange = (_: React.SyntheticEvent, newValue: number) => {
    navigate(newValue === 0 ? '/settings' : '/settings/model-groups')
  }

  return (
    <Box>
      {/* 标签页导航 */}
      <Paper sx={{ mb: 2 }}>
        <Tabs value={currentTab} onChange={handleTabChange}>
          <Tab label="基本配置" />
          <Tab label="模型组" />
        </Tabs>
      </Paper>

      {/* 内容区域 */}
      <Paper
        elevation={0}
        sx={{
          minHeight: 'calc(100vh - 250px)',
          backgroundColor: 'transparent',
          '& > *': {
            height: '100%',
          },
        }}
      >
        <Outlet />
      </Paper>

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
