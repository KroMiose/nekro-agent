import { useState, useEffect, useRef } from 'react'
import {
  Box,
  Alert,
  FormControlLabel,
  Switch,
  Stack,
  Paper,
} from '@mui/material'
import { LoadingButton } from '@mui/lab'
import { useQuery } from '@tanstack/react-query'
import { oneBotV11Api } from '../../../services/api/adapters/onebot_v11'
import { useTranslation } from 'react-i18next'
import {
  RestartAlt,
  Delete as DeleteIcon,
  ContentCopy as ContentCopyIcon,
} from '@mui/icons-material'
import { useNotification } from '../../../hooks/useNotification'
import { copyText } from '../../../utils/clipboard'
import ActionButton from '../../../components/common/ActionButton'
import IconActionButton from '../../../components/common/IconActionButton'

// 格式化时间
const formatTime = (isoTime: string, locale?: string) => {
  try {
    const date = new Date(isoTime)
    return date.toLocaleString(locale || 'zh-CN', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
      hour12: false,
    })
  } catch {
    return isoTime
  }
}

// WebUI Token 提取
const extractWebuiToken = (logs: string[]): string | undefined => {
  if (!logs?.length) return undefined
  const tokenRegex = /WebUi Local Panel Url: http:\/\/[^?]+\?token=([^\s]+)/
  for (let i = logs.length - 1; i >= 0; i--) {
    const match = logs[i].match(tokenRegex)
    if (match) return match[1]
  }
  return undefined
}

export default function OneBotV11LogsPage() {
  const [autoScroll, setAutoScroll] = useState(true)
  const [logs, setLogs] = useState<string[]>([])
  const [isRestarting, setIsRestarting] = useState(false)
  const [isReconnecting, setIsReconnecting] = useState(false)
  const [webuiToken, setWebuiToken] = useState<string>()
  const tableContainerRef = useRef<HTMLDivElement>(null)
  const notification = useNotification()
  const { t, i18n } = useTranslation('adapter')

  // 查询状态
  const { data: status } = useQuery({
    queryKey: ['onebot-v11-container-status'],
    queryFn: () => oneBotV11Api.getContainerStatus(),
    refetchInterval: isRestarting ? 1000 : 5000,
  })

  // 实时日志订阅 - 参考原版简单逻辑
  useEffect(() => {
    let cleanup: (() => void) | undefined

    const connect = () => {
      try {
        cleanup = oneBotV11Api.streamContainerLogs(
          data => {
            setLogs(prev => {
              const newLogs = [...prev, data].slice(-1000)
              setWebuiToken(extractWebuiToken(newLogs))
              return newLogs
            })
            setIsReconnecting(false)
          },
          error => {
            notification.error(
              error instanceof Error ? error.message : t('logs.connectFailed')
            )
            setIsReconnecting(true)
            // 5秒后尝试重连
            setTimeout(() => {
              connect()
            }, 5000)
          }
        )
      } catch (error) {
        notification.error(error instanceof Error ? error.message : t('logs.connectFailed'))
        setIsReconnecting(true)
      }
    }

    // 初始化日志
    oneBotV11Api
      .getContainerLogs(500)
      .then(logs => {
        setLogs(logs || [])
        setWebuiToken(extractWebuiToken(logs || []))
      })
      .catch(error => {
        notification.error(error instanceof Error ? error.message : t('logs.connectFailed'))
      })

    connect()

    return () => {
      cleanup?.()
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  // 自动滚动
  useEffect(() => {
    if (autoScroll && tableContainerRef.current) {
      requestAnimationFrame(() => {
        if (tableContainerRef.current) {
          const { scrollHeight, clientHeight } = tableContainerRef.current
          tableContainerRef.current.scrollTop = scrollHeight - clientHeight
        }
      })
    }
  }, [logs, autoScroll])

  // 容器重启
  const handleRestart = async () => {
    try {
      setIsRestarting(true)
      notification.info(t('logs.restarting'))
      setLogs([])
      setWebuiToken(undefined)

      await oneBotV11Api.restartContainer()

      // 等待容器重启完成
      let lastStartTime = ''
      const checkInterval = setInterval(async () => {
        try {
          const status = await oneBotV11Api.getContainerStatus()
          // 检查启动时间是否更新，说明容器已经重新启动
          if (status.running && (!lastStartTime || status.started_at > lastStartTime)) {
            clearInterval(checkInterval)
            setIsRestarting(false)
            notification.success(t('logs.restartSuccess'))
            // 等待容器日志系统就绪
            setTimeout(async () => {
              try {
                const logs = await oneBotV11Api.getContainerLogs(100)
                setLogs(logs || [])
                setWebuiToken(extractWebuiToken(logs || []))
              } catch (error) {
                notification.error(
                  error instanceof Error ? error.message : t('logs.connectFailed')
                )
              }
            }, 2000)
          }
          lastStartTime = status.started_at
        } catch (error) {
          notification.error(
            error instanceof Error ? error.message : t('logs.connectFailed')
          )
        }
      }, 2000)

      // 设置超时
      setTimeout(() => {
        clearInterval(checkInterval)
        if (isRestarting) {
          setIsRestarting(false)
          notification.error(t('logs.restartTimeout'))
        }
      }, 30000)
    } catch (error) {
      setIsRestarting(false)
      notification.error(error instanceof Error ? error.message : t('logs.restartFailed'))
    }
  }

  const handleAutoScrollChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    setAutoScroll(event.target.checked)
  }

  const handleClearLogs = () => {
    setLogs([])
    notification.success(t('logs.cleared'))
  }

  const handleCopyToken = async () => {
    if (webuiToken) {
      const success = await copyText(webuiToken)
      if (success) {
        notification.success(t('logs.tokenCopied'))
      } else {
        notification.error(t('logs.copyFailed'))
      }
    }
  }

  return (
    <Box sx={{ p: { xs: 1.25, sm: 2 }, height: '100%', display: 'flex', flexDirection: 'column', gap: { xs: 1.25, sm: 2 }, boxSizing: 'border-box', minWidth: 0 }}>
      <Stack spacing={2}>
        <Alert
          severity={status?.running ? 'success' : 'error'}
          action={
            <LoadingButton
              size="small"
              color="warning"
              variant="outlined"
              onClick={handleRestart}
              loading={isRestarting}
              loadingPosition="start"
              startIcon={<RestartAlt />}
              disabled={!status?.running}
            >
              {t('logs.restartContainer')}
            </LoadingButton>
          }
        >
          {t('logs.status')}: {status?.running ? 'running' : 'stopped'} | {t('logs.startTime')}:{' '}
          {status?.started_at ? formatTime(status.started_at, i18n.language) : t('logs.unknown')}
        </Alert>

        <Stack direction={{ xs: 'column', md: 'row' }} spacing={1.5} alignItems={{ xs: 'stretch', md: 'center' }}>
          <Box sx={{ minWidth: 0, flex: '1 1 auto' }}>
            <Alert
              severity={isReconnecting ? 'warning' : webuiToken ? 'success' : 'info'}
              sx={{
                maxWidth: { xs: '100%', md: '360px' },
                '& .MuiAlert-message': {
                  overflow: 'hidden',
                  textOverflow: 'ellipsis',
                  whiteSpace: 'nowrap',
                },
              }}
              action={
                !isReconnecting &&
                webuiToken && (
                  <ActionButton
                    tone="secondary"
                    size="small"
                    startIcon={<ContentCopyIcon />}
                    onClick={handleCopyToken}
                  >
                    {t('logs.copy')}
                  </ActionButton>
                )
              }
            >
              {isReconnecting ? (
                t('logs.disconnected')
              ) : webuiToken ? (
                <>
                  WebUI Token: <strong>{webuiToken}</strong>
                </>
              ) : (
                t('logs.tokenNotFound')
              )}
            </Alert>
          </Box>
          <Box sx={{ flex: '0 0 auto' }}>
            <Stack direction="row" spacing={1} alignItems="center" justifyContent="space-between" useFlexGap flexWrap="wrap">
              <FormControlLabel
                control={<Switch checked={autoScroll} onChange={handleAutoScrollChange} />}
                label={t('logs.autoScroll')}
              />
              <IconActionButton
                onClick={handleClearLogs}
                size="small"
                title={t('logs.clearLogs', '清空日志')}
              >
                <DeleteIcon />
              </IconActionButton>
            </Stack>
          </Box>
        </Stack>
      </Stack>

      <Paper
        ref={tableContainerRef}
        sx={{
          p: { xs: 1, sm: 2 },
          flexGrow: 1,
          overflow: 'auto',
          bgcolor: theme => (theme.palette.mode === 'dark' ? '#1a1a1a' : '#f5f5f5'),
          '& pre': {
            margin: 0,
            fontFamily: '"Courier New", Consolas, monospace',
            fontSize: { xs: '12px', sm: '14px' },
            lineHeight: { xs: 1.35, sm: 1.2 },
            letterSpacing: 0,
            whiteSpace: 'pre-wrap',
            wordWrap: 'break-word',
            wordBreak: 'break-all',
          },
        }}
      >
        {logs.map((log, index) => (
          <pre key={index}>{log}</pre>
        ))}
      </Paper>
    </Box>
  )
}
