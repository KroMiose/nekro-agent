import { RouterProvider } from 'react-router-dom'
import router from './router'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { ThemeProvider } from './theme'
import NotificationProvider from './components/common/NotificationProvider'
import CopyableTextDialogProvider from './components/common/CopyableTextDialogProvider'
import './config/i18n' // 初始化 i18n

// 创建查询客户端实例
const queryClient = new QueryClient()

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <ThemeProvider>
        <NotificationProvider>
          <CopyableTextDialogProvider>
            <RouterProvider router={router} />
          </CopyableTextDialogProvider>
        </NotificationProvider>
      </ThemeProvider>
    </QueryClientProvider>
  )
}

export default App
