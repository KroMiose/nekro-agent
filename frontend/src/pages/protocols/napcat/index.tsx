import { useState, useRef, useEffect, useCallback } from 'react'
import {
  Box,
  Paper,
  Tabs,
  Tab,
  Alert,
  FormControlLabel,
  Switch,
  CircularProgress,
  Typography,
  Snackbar,
  Stack,
  IconButton,
  Button,
} from '@mui/material'
import { LoadingButton } from '@mui/lab'
import { useQuery } from '@tanstack/react-query'
import { napCatApi } from '../../../services/api/napcat'
import {
  RestartAlt,
  Delete as DeleteIcon,
  ContentCopy as ContentCopyIcon,
} from '@mui/icons-material'
import { configApi } from '../../../services/api/config'

interface TabPanelProps {
  children?: React.ReactNode
  index: number
  value: number
}

function TabPanel(props: TabPanelProps) {
  const { children, value, index, ...other } = props
  return (
    <div
      role="tabpanel"
      hidden={value !== index}
      id={`napcat-tabpanel-${index}`}
      aria-labelledby={`napcat-tab-${index}`}
      {...other}
      style={{ height: '100%', overflow: 'auto' }}
    >
      <Box sx={{ height: '100%' }}>{children}</Box>
    </div>
  )
}

export default function NapCatPage() {
  // 状态管理
  const [tabValue, setTabValue] = useState(0)
  const [autoScroll, setAutoScroll] = useState(true)
  const [logs, setLogs] = useState<string[]>([])
  const [iframeLoaded, setIframeLoaded] = useState(false)
  const [isRestarting, setIsRestarting] = useState(false)
  const [isReconnecting, setIsReconnecting] = useState(false)
  const [webuiToken, setWebuiToken] = useState<string>()
  const [message, setMessage] = useState<{ text: string; severity: 'success' | 'error' | 'info' }>()

  // Refs
  const logsContainerRef = useRef<HTMLDivElement>(null)
  const eventSourceRef = useRef<EventSource | null>(null)
  const reconnectTimeoutRef = useRef<ReturnType<typeof setTimeout>>()

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

  // 查询
  const { data: status } = useQuery({
    queryKey: ['napcat-status'],
    queryFn: () => napCatApi.getStatus(),
    refetchInterval: isRestarting ? 1000 : 5000,
  })

  const { data: napCatConfig } = useQuery({
    queryKey: ['config', 'NAPCAT_ACCESS_URL'],
    queryFn: async () => {
      const response = await configApi.getConfig('NAPCAT_ACCESS_URL')
      return response.value as string
    },
  })

  const { data: onebotToken } = useQuery({
    queryKey: ['napcat-onebot-token'],
    queryFn: () => napCatApi.getOneBotToken(),
  })

  // WebUI Token 提取
  const extractWebuiToken = (logs: string[]) => {
    if (!logs?.length) return undefined
    const tokenRegex = /WebUi Local Panel Url: http:\/\/[^?]+\?token=([^\s]+)/
    for (let i = logs.length - 1; i >= 0; i--) {
      const match = logs[i].match(tokenRegex)
      if (match) return match[1]
    }
    return undefined
  }

  // 日志流连接
  const connectEventSource = useCallback(() => {
    if (eventSourceRef.current) {
      eventSourceRef.current.close()
    }

    const eventSource = napCatApi.streamLogs()
    eventSourceRef.current = eventSource

    eventSource.onmessage = event => {
      const newLog = event.data
      if (newLog.startsWith('[ERROR]')) {
        console.error(newLog)
        return
      }
      setLogs(prev => {
        const newLogs = [...(prev || []), newLog].slice(-1000)
        setWebuiToken(extractWebuiToken(newLogs))
        return newLogs
      })
      setIsReconnecting(false)
    }

    eventSource.onerror = () => {
      console.error('EventSource failed')
      eventSource.close()
      setIsReconnecting(true)

      if (!isRestarting) {
        if (reconnectTimeoutRef.current) {
          clearTimeout(reconnectTimeoutRef.current)
        }
        reconnectTimeoutRef.current = setTimeout(
          () => {
            napCatApi.getLogs(100).then(logs => {
              setLogs(logs || [])
              setWebuiToken(extractWebuiToken(logs || []))
              connectEventSource()
            })
          },
          isReconnecting ? 5000 : 0
        )
      }
    }
  }, [isRestarting, isReconnecting])

  // 初始化
  useEffect(() => {
    napCatApi.getLogs(500).then(logs => {
      setLogs(logs || [])
      setWebuiToken(extractWebuiToken(logs || []))
    })
    connectEventSource()

    return () => {
      if (eventSourceRef.current) {
        eventSourceRef.current.close()
      }
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current)
      }
    }
  }, [connectEventSource])

  // 自动滚动
  useEffect(() => {
    if (autoScroll && logsContainerRef.current) {
      requestAnimationFrame(() => {
        if (logsContainerRef.current) {
          const { scrollHeight, clientHeight } = logsContainerRef.current
          logsContainerRef.current.scrollTop = scrollHeight - clientHeight
        }
      })
    }
  }, [logs, autoScroll])

  // 容器重启
  const handleRestart = async () => {
    try {
      setIsRestarting(true)
      setMessage({ text: '正在重启容器...', severity: 'info' })
      setLogs([])
      setWebuiToken(undefined)

      if (eventSourceRef.current) {
        eventSourceRef.current.close()
      }

      await napCatApi.restart()

      // 等待容器重启完成
      let lastStartTime = ''
      const checkInterval = setInterval(async () => {
        try {
          const status = await napCatApi.getStatus()
          // 检查启动时间是否更新，说明容器已经重新启动
          if (status.running && (!lastStartTime || status.started_at > lastStartTime)) {
            clearInterval(checkInterval)
            setIsRestarting(false)
            setMessage({ text: '容器已成功重启！', severity: 'success' })
            // 等待容器日志系统就绪
            setTimeout(async () => {
              try {
                const logs = await napCatApi.getLogs(100)
                setLogs(logs || [])
                setWebuiToken(extractWebuiToken(logs || []))
                connectEventSource()
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
          setMessage({ text: '容器重启超时，请检查状态', severity: 'error' })
        }
      }, 30000)
    } catch (error) {
      console.error('Failed to restart:', error)
      setIsRestarting(false)
      setMessage({ text: '重启失败，请重试', severity: 'error' })
    }
  }

  // 事件处理
  const handleTabChange = (_: React.SyntheticEvent, newValue: number) => {
    setTabValue(newValue)
  }

  const handleAutoScrollChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    setAutoScroll(event.target.checked)
  }

  const handleClearLogs = () => {
    setLogs([])
    setMessage({ text: '日志已清空', severity: 'success' })
  }

  const handleCopyToken = () => {
    if (webuiToken) {
      navigator.clipboard.writeText(webuiToken)
      setMessage({ text: 'Token 已复制到剪贴板', severity: 'success' })
    }
  }

  return (
    <Box sx={{ height: 'calc(100vh - 140px)', display: 'flex', flexDirection: 'column' }}>
      <Box sx={{ borderBottom: 1, borderColor: 'divider' }}>
        <Tabs value={tabValue} onChange={handleTabChange}>
          <Tab label="WEBUI" />
          <Tab label="容器日志" />
        </Tabs>
      </Box>

      <TabPanel value={tabValue} index={0}>
        <Box sx={{ p: 2 }}>
          {onebotToken && (
            <Alert
              severity="info"
              sx={{ mb: 2 }}
              action={
                <Button
                  size="small"
                  startIcon={<ContentCopyIcon />}
                  onClick={() => {
                    navigator.clipboard.writeText(onebotToken)
                    setMessage({ text: '访问密钥已复制到剪贴板', severity: 'success' })
                  }}
                >
                  复制
                </Button>
              }
            >
              OneBot 服务访问密钥: <strong>{onebotToken}</strong>
            </Alert>
          )}
          <Box
            sx={{
              position: 'relative',
              height: onebotToken ? 'calc(100vh - 300px)' : 'calc(100vh - 240px)',
              '& iframe': {
                width: '100%',
                height: '100%',
                border: 'none',
                opacity: iframeLoaded ? 1 : 0,
                transition: 'opacity 0.3s',
              },
            }}
          >
            {napCatConfig && <iframe src={napCatConfig} onLoad={() => setIframeLoaded(true)} />}
            <Box
              sx={{
                position: 'absolute',
                top: 0,
                left: 0,
                right: 0,
                bottom: 0,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                bgcolor: theme => theme.palette.background.paper,
                transition: 'opacity 0.3s',
                opacity: iframeLoaded && napCatConfig ? 0 : 1,
                pointerEvents: iframeLoaded && napCatConfig ? 'none' : 'auto',
              }}
            >
              {!napCatConfig ? (
                <Typography color="error">无法获取 NapCat 访问地址</Typography>
              ) : !status?.running ? (
                <Typography color="error">NapCat 服务未运行</Typography>
              ) : (
                <CircularProgress />
              )}
            </Box>
          </Box>
        </Box>
      </TabPanel>

      <TabPanel value={tabValue} index={1}>
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
                      <Button
                        size="small"
                        startIcon={<ContentCopyIcon />}
                        onClick={handleCopyToken}
                      >
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
            ref={logsContainerRef}
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
      </TabPanel>

      <Snackbar
        open={!!message}
        autoHideDuration={6000}
        onClose={() => setMessage(undefined)}
        anchorOrigin={{ vertical: 'top', horizontal: 'center' }}
      >
        {message && (
          <Alert
            onClose={() => setMessage(undefined)}
            severity={message.severity}
            variant="filled"
            sx={{ width: '100%' }}
          >
            {message.text}
          </Alert>
        )}
      </Snackbar>
    </Box>
  )
}
