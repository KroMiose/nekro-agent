import { useEffect } from 'react'
import { RouterProvider } from 'react-router-dom'
import router from './router'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { ThemeProvider } from './theme'
import NotificationProvider from './components/common/NotificationProvider'
import './config/i18n' // 初始化 i18n

// 创建查询客户端实例
const queryClient = new QueryClient()

function App() {
  useEffect(() => {
    const params = new URLSearchParams(window.location.search)
    const state = params.get('state')
    if (!params.get('code') || !state?.startsWith('email:') || window.location.hash) return
    window.history.replaceState(
      {},
      document.title,
      `${window.location.pathname}${window.location.search}#/adapters/email/accounts`
    )
  }, [])

  return (
    <QueryClientProvider client={queryClient}>
      <ThemeProvider>
        <NotificationProvider>
          <RouterProvider router={router} />
        </NotificationProvider>
      </ThemeProvider>
    </QueryClientProvider>
  )
}

export default App
