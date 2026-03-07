import React, { useEffect, useRef, useState, useCallback } from 'react'
import {
  Box,
  Typography,
  Chip,
  IconButton,
  Stack,
  Tooltip,
} from '@mui/material'
import {
  DeleteOutline as ClearIcon,
  Circle as CircleIcon,
} from '@mui/icons-material'
import { commandsApi, type CommandOutputEvent } from '../../../../services/api/commands'
import { useTranslation } from 'react-i18next'

interface CommandOutputLogProps {
  chatKey: string
}

const MAX_EVENTS = 200

const STATUS_COLOR_MAP: Record<string, 'success' | 'error' | 'warning' | 'info' | 'default'> = {
  success: 'success',
  error: 'error',
  processing: 'info',
  unauthorized: 'warning',
  waiting: 'warning',
  not_found: 'default',
  invalid_args: 'error',
  disabled: 'default',
}

function formatTime(ts: number): string {
  const d = new Date(ts * 1000)
  return d.toLocaleTimeString('en-GB', { hour12: false })
}

export default function CommandOutputLog({ chatKey }: CommandOutputLogProps) {
  const [events, setEvents] = useState<CommandOutputEvent[]>([])
  const [connected, setConnected] = useState(false)
  const bottomRef = useRef<HTMLDivElement>(null)
  const containerRef = useRef<HTMLDivElement>(null)
  const [autoScroll, setAutoScroll] = useState(true)
  const { t } = useTranslation('chat-channel')

  // 检测是否在底部附近，控制自动滚动
  const handleScroll = useCallback(() => {
    const el = containerRef.current
    if (!el) return
    const atBottom = el.scrollHeight - el.scrollTop - el.clientHeight < 40
    setAutoScroll(atBottom)
  }, [])

  // 自动滚动到底部
  useEffect(() => {
    if (autoScroll) {
      bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
    }
  }, [events, autoScroll])

  // SSE 订阅
  useEffect(() => {
    setEvents([])
    setConnected(false)

    // 使用一个小延迟确保连接被建立后标记为 connected
    const connectTimer = setTimeout(() => setConnected(true), 500)

    const cleanup = commandsApi.streamCommandOutput(
      chatKey,
      (event) => {
        setConnected(true)
        setEvents((prev) => {
          const next = [...prev, event]
          return next.length > MAX_EVENTS ? next.slice(-MAX_EVENTS) : next
        })
      },
      () => {
        setConnected(false)
      },
    )

    return () => {
      clearTimeout(connectTimer)
      cleanup()
    }
  }, [chatKey])

  const handleClear = () => {
    setEvents([])
  }

  return (
    <Box className="flex flex-col h-full">
      {/* 顶部工具栏 */}
      <Stack
        direction="row"
        alignItems="center"
        justifyContent="space-between"
        sx={{ px: 1.5, py: 0.5, flexShrink: 0 }}
      >
        <Stack direction="row" alignItems="center" spacing={0.5}>
          <CircleIcon
            sx={{
              fontSize: 8,
              color: connected ? 'success.main' : 'text.disabled',
            }}
          />
          <Typography variant="caption" color="text.secondary">
            {connected
              ? t('commandSidebar.connected')
              : t('commandSidebar.disconnected')}
          </Typography>
        </Stack>
        <Tooltip title={t('commandSidebar.clear')}>
          <IconButton size="small" onClick={handleClear} disabled={events.length === 0}>
            <ClearIcon fontSize="small" />
          </IconButton>
        </Tooltip>
      </Stack>

      {/* 日志内容 */}
      <Box
        ref={containerRef}
        onScroll={handleScroll}
        sx={{
          flex: 1,
          overflow: 'auto',
          px: 1.5,
          pb: 1,
          fontFamily: 'monospace',
          fontSize: '0.75rem',
          lineHeight: 1.6,
        }}
      >
        {events.length === 0 ? (
          <Box sx={{ textAlign: 'center', py: 3 }}>
            <Typography variant="body2" color="text.secondary">
              {t('commandSidebar.noOutput')}
            </Typography>
            <Typography variant="caption" color="text.disabled" sx={{ mt: 0.5, display: 'block' }}>
              {t('commandSidebar.outputHint')}
            </Typography>
          </Box>
        ) : (
          events.map((ev, idx) => (
            <Box key={idx} sx={{ py: 0.25, display: 'flex', alignItems: 'flex-start', gap: 0.5 }}>
              <Typography
                component="span"
                sx={{ fontSize: 'inherit', color: 'text.disabled', flexShrink: 0 }}
              >
                {formatTime(ev.timestamp)}
              </Typography>
              <Chip
                label={ev.command_name}
                size="small"
                color={STATUS_COLOR_MAP[ev.status] || 'default'}
                variant="outlined"
                sx={{
                  height: 18,
                  fontSize: '0.65rem',
                  flexShrink: 0,
                  '& .MuiChip-label': { px: 0.5 },
                }}
              />
              <Typography
                component="span"
                sx={{
                  fontSize: 'inherit',
                  color: ev.status === 'error' ? 'error.main' : 'text.primary',
                  wordBreak: 'break-word',
                }}
              >
                {ev.message}
              </Typography>
            </Box>
          ))
        )}
        <div ref={bottomRef} />
      </Box>
    </Box>
  )
}
