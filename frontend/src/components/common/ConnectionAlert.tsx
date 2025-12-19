import { useEffect } from 'react'
import { useTranslation } from 'react-i18next'
import { Alert, Snackbar } from '@mui/material'
import { useAppStore } from '../../stores/app'
import { healthApi } from '../../services/api/health'

// 健康检查间隔（毫秒）
const CHECK_INTERVAL = 5000

let checkInterval: number | null = null

export default function ConnectionAlert() {
  const { isConnected, setConnected } = useAppStore()
  const { t } = useTranslation('common')

  useEffect(() => {
    // 如果已经存在定时器，不重复创建
    if (checkInterval) return

    const checkHealth = async () => {
      try {
        await healthApi.check()
        if (!isConnected) {
          setConnected(true)
        }
      } catch {
        setConnected(false)
      }
    }

    // 立即执行一次
    checkHealth()

    // 设置定时器
    checkInterval = window.setInterval(checkHealth, CHECK_INTERVAL)

    // 清理函数
    return () => {
      if (checkInterval) {
        window.clearInterval(checkInterval)
        checkInterval = null
      }
    }
  }, [isConnected, setConnected])

  return (
    <Snackbar open={!isConnected} anchorOrigin={{ vertical: 'top', horizontal: 'center' }}>
      <Alert severity="error" variant="filled">
        {t('messages.connectionLost')}
      </Alert>
    </Snackbar>
  )
}
