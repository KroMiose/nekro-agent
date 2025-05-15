/**
 * 通知系统配置
 * 独立出来避免影响React Fast Refresh
 */

// 通知系统默认配置
export const notificationConfig = {
  // 配置项
  maxSnack: 5, // 最大显示数量
  autoHideDuration: 3000, // 自动隐藏时间
  anchorOrigin: {
    vertical: 'top' as const,
    horizontal: 'center' as const
  }
} 