/**
 * 通知系统Hook
 * 提供便捷的通知方法
 */
import { useSnackbar, VariantType, OptionsObject } from 'notistack'
import { notificationConfig } from '../components/common/config/notificationConfig'

interface NotificationOptions extends Partial<OptionsObject> {
  duration?: number
}

/**
 * 通知系统Hook
 * 提供统一的通知方法
 */
export function useNotification() {
  const { enqueueSnackbar, closeSnackbar } = useSnackbar()
  
  // 显示通知
  const notify = (
    message: string,
    variant: VariantType = 'default',
    options?: NotificationOptions
  ) => {
    return enqueueSnackbar(message, {
      variant,
      autoHideDuration: options?.duration || notificationConfig.autoHideDuration,
      ...options
    })
  }
  
  // 成功通知
  const success = (message: string, options?: NotificationOptions) => {
    return notify(message, 'success', options)
  }
  
  // 错误通知
  const error = (message: string, options?: NotificationOptions) => {
    return notify(message, 'error', {
      autoHideDuration: 5000, // 错误通知显示时间更长
      ...options
    })
  }
  
  // 警告通知
  const warning = (message: string, options?: NotificationOptions) => {
    return notify(message, 'warning', options)
  }
  
  // 信息通知
  const info = (message: string, options?: NotificationOptions) => {
    return notify(message, 'info', options)
  }

  // 关闭指定通知
  const close = (key: string | number) => {
    closeSnackbar(key)
  }
  
  // 关闭所有通知
  const closeAll = () => {
    closeSnackbar()
  }
  
  return {
    notify,
    success,
    error,
    warning,
    info,
    close,
    closeAll
  }
} 