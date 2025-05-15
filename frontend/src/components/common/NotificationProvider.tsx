/**
 * 通知系统提供者
 * 整合notistack库和自定义通知组件
 */
import { ReactNode } from 'react'
import { SnackbarProvider } from 'notistack'
import NekroNotification from './NekroNotification'
import { notificationConfig } from './config/notificationConfig'

interface NotificationProviderProps {
  children: ReactNode
}

// 通知提供者组件
export default function NotificationProvider({ children }: NotificationProviderProps) {
  return (
    <SnackbarProvider
      maxSnack={notificationConfig.maxSnack}
      autoHideDuration={notificationConfig.autoHideDuration}
      anchorOrigin={notificationConfig.anchorOrigin}
      // 使用自定义组件
      Components={{
        success: NekroNotification,
        error: NekroNotification,
        warning: NekroNotification,
        info: NekroNotification,
        default: NekroNotification
      }}
      // 自定义类名
      classes={{
        containerRoot: 'nekro-notification-container'
      }}
    >
      {children}
    </SnackbarProvider>
  )
} 