import { useState, useEffect, useCallback, useRef } from 'react'
import {
  Box,
  Button,
  Card,
  CardContent,
  Typography,
  CircularProgress,
  Alert,
  Stack,
  Divider,
  IconButton,
  Tooltip,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogContentText,
  DialogActions,
} from '@mui/material'
import {
  PlayArrow as PlayArrowIcon,
  Stop as StopIcon,
  Refresh as RefreshIcon,
  Build as BuildIcon,
  RestartAlt as RestartAltIcon,
  Clear as ClearIcon,
  Terminal as TerminalIcon,
  ViewList as LogsIcon,
} from '@mui/icons-material'
import { useQuery as _useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  workspaceApi,
  WorkspaceDetail,
  SandboxStatus,
  streamSandboxLogs,
  getSandboxTerminalWsUrl,
} from '../../../services/api/workspace'
import { useNotification } from '../../../hooks/useNotification'
import { CARD_VARIANTS, SCROLLBAR_VARIANTS } from '../../../theme/variants'
import { useAuthStore } from '../../../stores/auth'
import { Terminal } from 'xterm'
import { FitAddon } from 'xterm-addon-fit'
import 'xterm/css/xterm.css'
import { useTheme, alpha } from '@mui/material/styles'
import { useTranslation } from 'react-i18next'

// ──────────────────────────────────────────
// 日志面板（SSE 流式）
// ──────────────────────────────────────────
interface LogLine {
  id: number
  text: string
  type: 'log' | 'error' | 'info'
}

function LogsPanel({ workspaceId }: { workspaceId: number }) {
  const { t } = useTranslation('workspace')
  const theme = useTheme()
  const [logs, setLogs] = useState<LogLine[]>([])
  const logIdRef = useRef(0)
  const logEndRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const cleanup = streamSandboxLogs(
      workspaceId,
      (data, type) => {
        setLogs(prev => [...prev, { id: logIdRef.current++, text: data, type }])
      },
      () => {
        setLogs(prev => [
          ...prev,
          { id: logIdRef.current++, text: t('detail.sandbox.logs.disconnected'), type: 'error' },
        ])
      }
    )
    return () => cleanup?.()
  }, [workspaceId, t])

  useEffect(() => {
    logEndRef.current?.scrollIntoView({ behavior: 'auto' })
  }, [logs])

  const lineColor = (type: 'log' | 'error' | 'info') => {
    if (type === 'error') return theme.palette.error.main
    if (type === 'info') return theme.palette.warning.main
    return theme.palette.text.primary
  }

  const headerBg = alpha(theme.palette.background.paper, theme.palette.mode === 'dark' ? 0.85 : 0.95)
  const contentBg = theme.palette.mode === 'dark' ? '#1E1E1E' : '#f5f5f5'

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', height: '100%', minHeight: 0 }}>
      <Box
        sx={{
          px: 2,
          py: 0.75,
          display: 'flex',
          alignItems: 'center',
          gap: 1,
          borderBottom: `1px solid ${theme.palette.divider}`,
          flexShrink: 0,
          bgcolor: headerBg,
        }}
      >
        <LogsIcon sx={{ fontSize: 16, color: 'text.secondary' }} />
        <Typography variant="caption" sx={{ color: 'text.secondary', fontFamily: 'monospace' }}>
          {t('detail.sandbox.logs.title')}
        </Typography>
        <Typography variant="caption" sx={{ color: 'text.disabled', fontFamily: 'monospace' }}>
          {t('detail.sandbox.logs.lines', { count: logs.length })}
        </Typography>
        <Box sx={{ flexGrow: 1 }} />
        <Tooltip title={t('detail.sandbox.logs.clearTooltip')}>
          <IconButton size="small" onClick={() => setLogs([])} sx={{ color: 'text.secondary', p: 0.5 }}>
            <ClearIcon sx={{ fontSize: 14 }} />
          </IconButton>
        </Tooltip>
      </Box>

      <Box
        sx={{
          flex: 1,
          minHeight: 0,
          overflowY: 'auto',
          px: 2,
          py: 1,
          fontFamily: '"SFMono-Regular", Consolas, "Liberation Mono", Menlo, monospace',
          fontSize: '0.78rem',
          lineHeight: 1.5,
          bgcolor: contentBg,
          whiteSpace: 'pre-wrap',
          wordBreak: 'break-all',
          ...SCROLLBAR_VARIANTS.thin.styles,
        }}
      >
        {logs.length === 0 ? (
          <Typography
            sx={{ color: 'text.disabled', fontFamily: 'monospace', fontSize: '0.78rem' }}
          >
            {t('detail.sandbox.logs.waiting')}
          </Typography>
        ) : (
          logs.map(line => (
            <Box key={line.id} sx={{ color: lineColor(line.type) }}>
              {line.text}
            </Box>
          ))
        )}
        <div ref={logEndRef} />
      </Box>
    </Box>
  )
}

// ──────────────────────────────────────────
// 终端面板（WebSocket + xterm.js）
// ──────────────────────────────────────────
function TerminalPanel({ workspaceId, isActive }: { workspaceId: number; isActive: boolean }) {
  const { t } = useTranslation('workspace')
  const theme = useTheme()
  const termContainerRef = useRef<HTMLDivElement>(null)
  const termInstance = useRef<Terminal | null>(null)
  const wsRef = useRef<WebSocket | null>(null)
  const [connStatus, setConnStatus] = useState<'disconnected' | 'connecting' | 'connected'>(
    'disconnected'
  )

  const termBg = theme.palette.mode === 'dark' ? '#1E1E1E' : '#f5f5f5'
  const termFg = theme.palette.mode === 'dark' ? 'rgba(255,255,255,0.87)' : '#1c1c1c'
  const termCursor = theme.palette.primary.main
  const termSelectionBg = alpha(theme.palette.primary.main, 0.3)

  const connect = useCallback(() => {
    if (!termContainerRef.current) return
    setConnStatus('connecting')

    if (wsRef.current) {
      wsRef.current.close()
      wsRef.current = null
    }
    if (termInstance.current) {
      termInstance.current.dispose()
      termInstance.current = null
    }

    const term = new Terminal({
      theme: {
        background: termBg,
        foreground: termFg,
        cursor: termCursor,
        selectionBackground: termSelectionBg,
      },
      fontFamily: '"SFMono-Regular", Consolas, "Liberation Mono", Menlo, monospace',
      fontSize: 13,
      lineHeight: 1.4,
      cursorBlink: true,
      allowProposedApi: true,
    })
    const fitAddon = new FitAddon()
    term.loadAddon(fitAddon)
    term.open(termContainerRef.current)

    requestAnimationFrame(() => {
      try {
        fitAddon.fit()
      } catch {
        /* ignore */
      }
    })

    termInstance.current = term

    const token = useAuthStore.getState().token
    const wsUrl = `${getSandboxTerminalWsUrl(workspaceId)}${token ? `?token=${encodeURIComponent(token)}` : ''}`
    const ws = new WebSocket(wsUrl)
    wsRef.current = ws

    ws.onopen = () => {
      setConnStatus('connected')
      try {
        fitAddon.fit()
        const { rows, cols } = term
        ws.send(JSON.stringify({ type: 'resize', rows, cols }))
      } catch {
        /* ignore */
      }
    }

    ws.onmessage = event => {
      try {
        const msg = JSON.parse(event.data as string) as { type: string; data: string }
        if (msg.type === 'output') term.write(msg.data)
      } catch {
        term.write(event.data as string)
      }
    }

    ws.onclose = () => {
      setConnStatus('disconnected')
      term.write(`\r\n\x1b[33m${t('detail.sandbox.terminal.wsDisconnected')}\x1b[0m\r\n`)
    }

    ws.onerror = () => {
      setConnStatus('disconnected')
      term.write(`\r\n\x1b[31m${t('detail.sandbox.terminal.wsError')}\x1b[0m\r\n`)
    }

    term.onData(data => {
      if (ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({ type: 'input', data }))
      }
    })

    const observer = new ResizeObserver(() => {
      try {
        fitAddon.fit()
        const { rows, cols } = term
        if (ws.readyState === WebSocket.OPEN) {
          ws.send(JSON.stringify({ type: 'resize', rows, cols }))
        }
      } catch {
        /* ignore */
      }
    })

    if (termContainerRef.current) {
      observer.observe(termContainerRef.current)
    }

    ;(term as unknown as { _observer: ResizeObserver })._observer = observer
  }, [workspaceId, t, termBg, termFg, termCursor, termSelectionBg])

  useEffect(() => {
    return () => {
      wsRef.current?.close()
      if (termInstance.current) {
        const obs = (termInstance.current as unknown as { _observer?: ResizeObserver })._observer
        obs?.disconnect()
        termInstance.current.dispose()
      }
    }
  }, [])

  const connStatusColor =
    connStatus === 'connected'
      ? theme.palette.success.main
      : connStatus === 'connecting'
        ? theme.palette.warning.main
        : theme.palette.text.disabled
  const connStatusLabel =
    connStatus === 'connected' ? t('detail.sandbox.terminal.connected') : connStatus === 'connecting' ? t('detail.sandbox.terminal.connecting') : t('detail.sandbox.terminal.disconnected')

  const headerBg = alpha(theme.palette.background.paper, theme.palette.mode === 'dark' ? 0.85 : 0.95)

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', height: '100%', minHeight: 0 }}>
      <Box
        sx={{
          px: 2,
          py: 0.75,
          display: 'flex',
          alignItems: 'center',
          gap: 1.5,
          borderBottom: `1px solid ${theme.palette.divider}`,
          flexShrink: 0,
          bgcolor: headerBg,
        }}
      >
        <TerminalIcon sx={{ fontSize: 16, color: 'text.secondary' }} />
        <Typography variant="caption" sx={{ color: 'text.secondary', fontFamily: 'monospace' }}>
          {t('detail.sandbox.terminal.title')}
        </Typography>
        <Box
          sx={{ width: 7, height: 7, borderRadius: '50%', bgcolor: connStatusColor, flexShrink: 0 }}
        />
        <Typography variant="caption" sx={{ color: connStatusColor, fontFamily: 'monospace' }}>
          {connStatusLabel}
        </Typography>
        <Box sx={{ flexGrow: 1 }} />
        {!isActive ? (
          <Typography variant="caption" sx={{ color: 'text.disabled' }}>
            {t('detail.sandbox.terminal.notRunning')}
          </Typography>
        ) : (
          <Button
            size="small"
            variant="text"
            startIcon={<RefreshIcon sx={{ fontSize: 14 }} />}
            onClick={connect}
            disabled={connStatus === 'connecting'}
            sx={{ fontSize: '0.7rem', color: 'text.secondary', minWidth: 0, px: 1, py: 0.25 }}
          >
            {connStatus === 'disconnected' ? t('detail.sandbox.terminal.connect') : t('detail.sandbox.terminal.reconnect')}
          </Button>
        )}
      </Box>

      <Box
        sx={{
          flex: 1,
          minHeight: 0,
          bgcolor: termBg,
          overflow: 'hidden',
          position: 'relative',
          '& .xterm': { height: '100%', padding: '8px' },
          '& .xterm-viewport': { overflowY: 'auto !important' },
        }}
      >
        {!isActive ? (
          <Box
            sx={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100%' }}
          >
            <Typography
              sx={{ color: 'text.disabled', fontFamily: 'monospace', fontSize: '0.8rem' }}
            >
              {t('detail.sandbox.terminal.startFirst')}
            </Typography>
          </Box>
        ) : (
          <div ref={termContainerRef} style={{ width: '100%', height: '100%' }} />
        )}
      </Box>
    </Box>
  )
}

// ──────────────────────────────────────────
// Tab 1: 沙盒容器（控制 + 日志 + 终端）
// ──────────────────────────────────────────
export default function SandboxTab({
  workspace,
  sandboxStatus,
  onSandboxMutate,
  onNavigateToOverview,
}: {
  workspace: WorkspaceDetail
  sandboxStatus: SandboxStatus | null
  onSandboxMutate: () => void
  onNavigateToOverview?: () => void
}) {
  const theme = useTheme()
  const queryClient = useQueryClient()
  const notification = useNotification()
  const { t } = useTranslation('workspace')
  const [isTransitioning, setIsTransitioning] = useState(false)
  const [rebuildOpen, setRebuildOpen] = useState(false)

  useEffect(() => {
    if (!isTransitioning) return
    const status = sandboxStatus?.status
    if (status === 'active' || status === 'stopped') {
      setIsTransitioning(false)
    }
  }, [sandboxStatus?.status, isTransitioning])

  const currentStatus = sandboxStatus?.status ?? workspace.status
  const isActive = currentStatus === 'active'
  const isStopped = currentStatus === 'stopped' || currentStatus === 'failed'

  const startMutation = useMutation({
    mutationFn: () => workspaceApi.sandboxStart(workspace.id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['sandbox-status', workspace.id] })
      queryClient.invalidateQueries({ queryKey: ['workspace', workspace.id] })
      notification.success(t('detail.sandbox.notifications.startSuccess'))
    },
    onError: (err: Error) => {
      const msg = err.message
      notification.error(t('detail.sandbox.notifications.startFailed', { message: msg }))
      if ((msg.includes('镜像') || msg.includes('image')) && onNavigateToOverview) {
        onNavigateToOverview()
      }
    },
  })

  const stopMutation = useMutation({
    mutationFn: () => workspaceApi.sandboxStop(workspace.id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['sandbox-status', workspace.id] })
      queryClient.invalidateQueries({ queryKey: ['workspace', workspace.id] })
      notification.success(t('detail.sandbox.notifications.stopSuccess'))
    },
    onError: (err: Error) => notification.error(t('detail.sandbox.notifications.stopFailed', { message: err.message })),
  })

  const restartMutation = useMutation({
    mutationFn: () => workspaceApi.sandboxRestart(workspace.id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['sandbox-status', workspace.id] })
      notification.success(t('detail.sandbox.notifications.restartSuccess'))
    },
    onError: (err: Error) => notification.error(t('detail.sandbox.notifications.restartFailed', { message: err.message })),
  })

  const rebuildMutation = useMutation({
    mutationFn: () => workspaceApi.sandboxRebuild(workspace.id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['sandbox-status', workspace.id] })
      queryClient.invalidateQueries({ queryKey: ['workspace', workspace.id] })
      notification.success(t('detail.sandbox.notifications.rebuildSuccess'))
      setRebuildOpen(false)
      setIsTransitioning(false)
    },
    onError: (err: Error) => {
      const msg = err.message
      setRebuildOpen(false)
      notification.error(t('detail.sandbox.notifications.rebuildFailed', { message: msg }))
      if ((msg.includes('镜像') || msg.includes('image')) && onNavigateToOverview) {
        onNavigateToOverview()
      }
    },
  })

  const resetSessionMutation = useMutation({
    mutationFn: () => workspaceApi.resetSession(workspace.id),
    onSuccess: () => notification.success(t('detail.sandbox.notifications.resetSessionSuccess')),
    onError: (err: Error) => notification.error(t('detail.sandbox.notifications.resetSessionFailed', { message: err.message })),
  })

  const anyMutating =
    startMutation.isPending ||
    stopMutation.isPending ||
    restartMutation.isPending ||
    rebuildMutation.isPending ||
    resetSessionMutation.isPending

  const statusRows = [
    { label: t('detail.sandbox.statusRows.containerName'), value: sandboxStatus?.container_name ?? workspace.container_name ?? '—' },
    { label: t('detail.sandbox.statusRows.hostPort'), value: sandboxStatus?.host_port ?? workspace.host_port ?? '—' },
    { label: t('detail.sandbox.statusRows.sessionId'), value: sandboxStatus?.session_id ?? '—' },
  ]

  return (
    <Box sx={{ height: '100%', display: 'flex', flexDirection: 'column', gap: 1.5 }}>
      {/* ── 沙盒控制卡片（顶部，固定高度） ── */}
      <Card sx={{ ...CARD_VARIANTS.default.styles, flexShrink: 0 }}>
        <CardContent sx={{ pb: '12px !important' }}>
          {/* 标题行：状态 + 过渡提示 + 控制按钮 */}
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5, flexWrap: 'wrap', mb: 1.5 }}>
            <Typography variant="subtitle2" sx={{ fontWeight: 600 }}>
              {t('detail.sandbox.title')}
            </Typography>
            {isTransitioning && (
              <Typography variant="caption" color="text.secondary">
                {t('detail.sandbox.transitioning')}
              </Typography>
            )}
            <Box sx={{ flexGrow: 1 }} />
            <Stack direction="row" spacing={1} flexWrap="wrap">
              <Button
                size="small"
                variant="contained"
                color="success"
                startIcon={
                  startMutation.isPending ? (
                    <CircularProgress size={14} color="inherit" />
                  ) : (
                    <PlayArrowIcon />
                  )
                }
                disabled={!isStopped || anyMutating}
                onClick={() => {
                  onSandboxMutate()
                  setIsTransitioning(true)
                  startMutation.mutate()
                }}
              >
                {t('detail.sandbox.buttons.start')}
              </Button>
              <Button
                size="small"
                variant="outlined"
                color="warning"
                startIcon={
                  stopMutation.isPending ? (
                    <CircularProgress size={14} color="inherit" />
                  ) : (
                    <StopIcon />
                  )
                }
                disabled={!isActive || anyMutating}
                onClick={() => {
                  onSandboxMutate()
                  setIsTransitioning(true)
                  stopMutation.mutate()
                }}
              >
                {t('detail.sandbox.buttons.stop')}
              </Button>
              <Button
                size="small"
                variant="outlined"
                startIcon={
                  restartMutation.isPending ? (
                    <CircularProgress size={14} color="inherit" />
                  ) : (
                    <RestartAltIcon />
                  )
                }
                disabled={!isActive || anyMutating}
                onClick={() => {
                  onSandboxMutate()
                  setIsTransitioning(true)
                  restartMutation.mutate()
                }}
              >
                {t('detail.sandbox.buttons.restart')}
              </Button>
              <Button
                size="small"
                variant="outlined"
                startIcon={
                  resetSessionMutation.isPending ? <CircularProgress size={14} /> : <RefreshIcon />
                }
                disabled={!isActive || anyMutating}
                onClick={() => {
                  onSandboxMutate()
                  resetSessionMutation.mutate()
                }}
              >
                {t('detail.sandbox.buttons.resetSession')}
              </Button>
              <Button
                size="small"
                variant="outlined"
                color="error"
                startIcon={<BuildIcon />}
                disabled={anyMutating}
                onClick={() => setRebuildOpen(true)}
              >
                {t('detail.sandbox.buttons.rebuild')}
              </Button>
            </Stack>
          </Box>

          <Divider sx={{ mb: 1.5 }} />

          {/* 运行信息行 */}
          <Stack direction="row" spacing={3} flexWrap="wrap">
            {statusRows.map(row => (
              <Box key={row.label} sx={{ display: 'flex', gap: 0.75, alignItems: 'center' }}>
                <Typography variant="caption" color="text.secondary" sx={{ flexShrink: 0 }}>
                  {row.label}
                </Typography>
                <Typography
                  variant="caption"
                  sx={{ fontFamily: 'monospace', wordBreak: 'break-all' }}
                >
                  {String(row.value)}
                </Typography>
              </Box>
            ))}
          </Stack>

          {/* 错误提示 */}
          {workspace.last_error && (
            <Alert severity="error" variant="outlined" sx={{ mt: 1.5 }}>
              <strong>{t('detail.sandbox.logError')}</strong>
              {workspace.last_error}
            </Alert>
          )}
        </CardContent>
      </Card>

      {/* ── 控制台（日志 + 终端，占满剩余高度） ── */}
      <Box
        sx={{
          flex: 1,
          minHeight: 0,
          display: 'flex',
          flexDirection: 'column',
          bgcolor: theme.palette.mode === 'dark' ? '#1E1E1E' : '#f5f5f5',
          borderRadius: 1,
          overflow: 'hidden',
          border: `1px solid ${theme.palette.divider}`,
        }}
      >
        {/* 日志区（上 55%）*/}
        <Box sx={{ flex: '0 0 55%', minHeight: 0, display: 'flex', flexDirection: 'column' }}>
          <LogsPanel workspaceId={workspace.id} />
        </Box>

        <Box sx={{ height: '2px', bgcolor: 'divider', flexShrink: 0 }} />

        {/* 终端区（下 45%）*/}
        <Box sx={{ flex: '0 0 45%', minHeight: 0, display: 'flex', flexDirection: 'column' }}>
          <TerminalPanel workspaceId={workspace.id} isActive={isActive} />
        </Box>
      </Box>

      {/* 重建确认对话框 */}
      <Dialog
        open={rebuildOpen}
        onClose={() => !rebuildMutation.isPending && setRebuildOpen(false)}
      >
        <DialogTitle>{t('detail.sandbox.rebuildDialog.title')}</DialogTitle>
        <DialogContent>
          <DialogContentText>
            {t('detail.sandbox.rebuildDialog.content')}
          </DialogContentText>
        </DialogContent>
        <DialogActions sx={{ px: 3, pb: 2 }}>
          <Button onClick={() => setRebuildOpen(false)} disabled={rebuildMutation.isPending}>
            {t('detail.sandbox.rebuildDialog.cancel')}
          </Button>
          <Button
            variant="contained"
            color="error"
            onClick={() => {
              onSandboxMutate()
              setIsTransitioning(true)
              rebuildMutation.mutate()
            }}
            disabled={rebuildMutation.isPending}
          >
            {rebuildMutation.isPending ? <CircularProgress size={20} /> : t('detail.sandbox.rebuildDialog.rebuild')}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  )
}
