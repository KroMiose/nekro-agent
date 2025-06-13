import { useState, useEffect, useRef } from 'react'
import {
  Box,
  Alert,
  FormControlLabel,
  Switch,
  Stack,
  IconButton,
  Button,
  Paper,
} from '@mui/material'
import { LoadingButton } from '@mui/lab'
import { useQuery } from '@tanstack/react-query'
import { oneBotV11Api } from '../../../services/api/onebot_v11'
import {
  RestartAlt,
  Delete as DeleteIcon,
  ContentCopy as ContentCopyIcon,
} from '@mui/icons-material'
import { useNotification } from '../../../hooks/useNotification'

// 格式化时间
const formatTime = (isoTime: string) => {
  try {
    const date = new Date(isoTime)
    return date.toLocaleString('zh-CN', {
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

  // 查询状态
  const { data: status } = useQuery({
    queryKey: ['onebot-v11-container-status'],
    queryFn: () => oneBotV11Api.getContainerStatus(),
    refetchInterval: isRestarting ? 1000 : 5000,
  })

  // 实时日志订阅 - 参考原版简单逻辑
  useEffect(() => {
    console.log('Starting real-time log subscription...')
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
            console.error('EventSource error:', error)
            setIsReconnecting(true)
            // 5秒后尝试重连
            setTimeout(() => {
              connect()
            }, 5000)
          }
        )
      } catch (error) {
        console.error('Failed to create EventSource:', error)
        notification.error(error instanceof Error ? error.message : '连接日志流失败')
        setIsReconnecting(true)
      }
    }

    // 初始化日志
    oneBotV11Api.getContainerLogs(500).then(logs => {
      setLogs(logs || [])
      setWebuiToken(extractWebuiToken(logs || []))
    })

    connect()

    return () => {
      console.log('Closing real-time log subscription...')
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
      notification.info('正在重启容器...')
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
            notification.success('容器已成功重启！')
            // 等待容器日志系统就绪
            setTimeout(async () => {
              try {
                const logs = await oneBotV11Api.getContainerLogs(100)
                setLogs(logs || [])
                setWebuiToken(extractWebuiToken(logs || []))
              } catch (error) {
                console.error('Failed to fetch initial logs:', error)
              }
            }, 2000)
          }
          lastStartTime = status.started_at
        } catch (error) {
          console.error('Failed to check status:', error)
        }
      }, 2000)

      // 设置超时
      setTimeout(() => {
        clearInterval(checkInterval)
        if (isRestarting) {
          setIsRestarting(false)
          notification.error('容器重启超时，请检查状态')
        }
      }, 30000)
    } catch (error) {
      console.error('Failed to restart:', error)
      setIsRestarting(false)
      notification.error('重启失败，请重试')
    }
  }

  const handleAutoScrollChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    setAutoScroll(event.target.checked)
  }

  const handleClearLogs = () => {
    setLogs([])
    notification.success('日志已清空')
  }

  const handleCopyToken = async () => {
    if (webuiToken) {
      try {
        await navigator.clipboard.writeText(webuiToken)
        notification.success('Token 已复制到剪贴板')
      } catch (error) {
        console.error('复制失败:', error)
        notification.error('复制失败，请手动复制')
      }
    }
  }

  return (
    <Box sx={{ p: 2, height: '100%', display: 'flex', flexDirection: 'column', gap: 2 }}>
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
              重启容器
            </LoadingButton>
          }
        >
          状态: {status?.running ? 'running' : 'stopped'} | 启动时间:{' '}
          {status?.started_at ? formatTime(status.started_at) : '未知'}
        </Alert>

        <Stack direction="row" spacing={2} alignItems="center">
          <Box sx={{ minWidth: 0, flex: '1 1 auto' }}>
            <Alert
              severity={isReconnecting ? 'warning' : webuiToken ? 'success' : 'info'}
              sx={{
                maxWidth: '360px',
                '& .MuiAlert-message': {
                  overflow: 'hidden',
                  textOverflow: 'ellipsis',
                  whiteSpace: 'nowrap',
                },
              }}
              action={
                !isReconnecting &&
                webuiToken && (
                  <Button size="small" startIcon={<ContentCopyIcon />} onClick={handleCopyToken}>
                    复制
                  </Button>
                )
              }
            >
              {isReconnecting ? (
                '日志流连接已断开，正在尝试重新连接...'
              ) : webuiToken ? (
                <>
                  WebUI Token: <strong>{webuiToken}</strong>
                </>
              ) : (
                '未找到 WebUI Token，如需获取请重启容器'
              )}
            </Alert>
          </Box>
          <Box sx={{ flex: '0 0 auto' }}>
            <Stack direction="row" spacing={2} alignItems="center">
              <FormControlLabel
                control={<Switch checked={autoScroll} onChange={handleAutoScrollChange} />}
                label="自动滚动"
              />
              <IconButton onClick={handleClearLogs} size="small">
                <DeleteIcon />
              </IconButton>
            </Stack>
          </Box>
        </Stack>
      </Stack>

      <Paper
        ref={tableContainerRef}
        sx={{
          p: 2,
          flexGrow: 1,
          overflow: 'auto',
          bgcolor: theme => (theme.palette.mode === 'dark' ? '#1a1a1a' : '#f5f5f5'),
          '& pre': {
            margin: 0,
            fontFamily: '"Courier New", Consolas, monospace',
            fontSize: '14px',
            lineHeight: '1.2',
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
