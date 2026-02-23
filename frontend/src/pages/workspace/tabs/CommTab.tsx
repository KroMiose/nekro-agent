import { useState, useEffect, useCallback, useRef, useMemo } from 'react'
import {
  Box,
  Button,
  Typography,
  CircularProgress,
  IconButton,
  Tooltip,
  TextField,
  alpha,
} from '@mui/material'
import {
  Build as BuildIcon,
  Forum as ForumIcon,
  Send as SendIcon,
  CheckCircle as CheckCircleIcon,
  ErrorOutline as ErrorOutlineIcon,
} from '@mui/icons-material'
import { useQuery } from '@tanstack/react-query'
import {
  WorkspaceDetail,
  commApi,
  streamCommLog,
  CommLogEntry,
} from '../../../services/api/workspace'
import { chatChannelApi } from '../../../services/api/chat-channel'
import { useNotification } from '../../../hooks/useNotification'
import { SCROLLBAR_VARIANTS } from '../../../theme/variants'
import MarkdownRenderer from '../../../components/common/MarkdownRenderer'
import { useTheme } from '@mui/material/styles'
import { useTranslation } from 'react-i18next'

// ──────────────────────────────────────────
// 通讯气泡内紧凑 Markdown 样式（模块级，避免每次渲染重建）
const COMM_BUBBLE_MD_SX = {
  fontSize: '0.82rem',
  '& p': { fontSize: '0.82rem', lineHeight: 1.65, marginBottom: '5px', '&:last-child': { marginBottom: 0 } },
  '& h1, & h2': { fontSize: '0.96rem', marginTop: '8px', marginBottom: '4px', paddingBottom: '2px' },
  '& h3, & h4, & h5, & h6': { fontSize: '0.88rem', marginTop: '6px', marginBottom: '3px' },
  '& ul, & ol': { fontSize: '0.82rem', paddingLeft: '18px', marginBottom: '5px', marginTop: '2px' },
  '& li': { marginBottom: '2px', lineHeight: 1.55 },
  '& code': { fontSize: '0.76rem', padding: '1px 4px' },
  '& pre': { fontSize: '0.76rem', padding: '8px 12px', marginBottom: '6px', marginTop: '4px' },
  '& blockquote': { marginBottom: '5px', padding: '3px 10px' },
  '& table': { fontSize: '0.78rem', marginBottom: '5px' },
  '& hr': { margin: '6px 0' },
  '& img': { maxWidth: '100%' },
} as const

// OS 检测（模块级，只运行一次）
const isMac = typeof navigator !== 'undefined' &&
  (/Mac/.test(navigator.platform) || /Macintosh/.test(navigator.userAgent))

export default function CommTab({ workspace, prefill }: { workspace: WorkspaceDetail; prefill?: string }) {
  const theme = useTheme()
  const notification = useNotification()
  const { t } = useTranslation('workspace')
  const [messages, setMessages] = useState<CommLogEntry[]>([])
  const [hasMore, setHasMore] = useState(false)
  const [loadingMore, setLoadingMore] = useState(false)
  const [input, setInput] = useState(prefill ?? '')
  const [sending, setSending] = useState(false)
  const [expandedIds, setExpandedIds] = useState<Set<number>>(new Set())

  // CC 工作状态推断：从消息流最后一条消息判断 CC 是否还在处理中
  // USER_TO_CC / NA_TO_CC / TOOL_CALL / TOOL_RESULT 出现在最后 → CC 还在工作
  // CC_TO_NA / SYSTEM 出现在最后 → CC 已完成
  const ccRunning = useMemo(() => {
    if (messages.length === 0) return false
    const last = messages[messages.length - 1]
    if (last.direction === 'CC_TO_NA' || last.direction === 'SYSTEM') return false
    // 10 分钟内的未完成消息才视为"正在工作"，防止历史异常消息误触
    const msgTime = new Date(last.create_time).getTime()
    return Date.now() - msgTime < 10 * 60 * 1000
  }, [messages])
  const endRef = useRef<HTMLDivElement>(null)
  const scrollRef = useRef<HTMLDivElement>(null)
  const autoScrollRef = useRef(true)
  const isInitializedRef = useRef(false)

  // prefill 变化时更新输入框
  useEffect(() => {
    if (prefill) setInput(prefill)
  }, [prefill])

  // 加载频道列表用于 chat_key 显示转换
  const { data: channelList } = useQuery({
    queryKey: ['chat-channels-comm'],
    queryFn: () => chatChannelApi.getList({ page: 1, page_size: 200 }),
    staleTime: 60000,
  })
  const allChannels = channelList?.items ?? []

  // 初始加载历史记录（最近20条）
  useEffect(() => {
    isInitializedRef.current = false
    commApi.getHistory(workspace.id, 20).then(r => {
      setMessages(r.items)
      setHasMore(r.total > r.items.length)
    }).catch(() => {})
  }, [workspace.id])

  // 加载更多（向上翻页）
  const loadMore = useCallback(async () => {
    if (loadingMore || !hasMore || messages.length === 0) return
    const oldestId = Math.min(...messages.map(m => m.id))
    setLoadingMore(true)
    try {
      const r = await commApi.getHistory(workspace.id, 20, oldestId)
      if (r.items.length > 0) {
        const scrollEl = scrollRef.current
        const prevScrollHeight = scrollEl?.scrollHeight ?? 0
        setMessages(prev => [...r.items, ...prev])
        setHasMore(r.items.length >= 20)
        requestAnimationFrame(() => {
          if (scrollEl) {
            scrollEl.scrollTop = scrollEl.scrollHeight - prevScrollHeight
          }
        })
      } else {
        setHasMore(false)
      }
    } catch { /* ignore */ }
    setLoadingMore(false)
  }, [workspace.id, messages, hasMore, loadingMore])

  // SSE 实时追加（id 去重）
  useEffect(() => {
    const cancel = streamCommLog(
      workspace.id,
      (entry) => {
        setMessages(prev =>
          prev.some(m => m.id === entry.id) ? prev : [...prev, entry]
        )
      },
      (err) => { console.error('comm stream error', err) },
    )
    return cancel
  }, [workspace.id])

  // 新消息时如果用户在底部则自动滚动
  useEffect(() => {
    if (messages.length === 0) return
    const el = scrollRef.current
    if (!isInitializedRef.current) {
      // 初次加载：瞬间跳到底部，避免 smooth 滚动触发 onScroll→loadMore
      if (el) el.scrollTop = el.scrollHeight
      isInitializedRef.current = true
    } else if (autoScrollRef.current) {
      endRef.current?.scrollIntoView({ behavior: 'smooth' })
    }
  }, [messages])

  const handleSend = async () => {
    if (!input.trim() || sending) return
    setSending(true)
    try {
      await commApi.sendToCC(workspace.id, input.trim())
      setInput('')
    } catch (e) {
      notification.error(t('detail.comm.notifications.sendFailed', { message: (e as Error).message }))
    } finally {
      setSending(false)
    }
  }

  const toggleExpand = (id: number) => {
    setExpandedIds(prev => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })
  }

  // 将 chat_key 渲染为频道名称（带下划线），悬浮显示原始 key
  const renderChatKey = (chatKey: string) => {
    if (!chatKey || chatKey === '__user__') return null
    const ch = allChannels.find(c => c.chat_key === chatKey)
    const displayName = ch?.channel_name ?? chatKey
    return (
      <Tooltip title={chatKey} placement="top" arrow>
        <Typography
          component="span"
          variant="caption"
          sx={{
            fontSize: '0.68rem',
            color: 'text.secondary',
            textDecoration: 'underline',
            textDecorationStyle: 'dotted',
            cursor: 'help',
            fontWeight: ch?.channel_name ? 500 : 400,
          }}
        >
          {displayName}
        </Typography>
      </Tooltip>
    )
  }

  const renderMessage = (msg: CommLogEntry) => {
    const isRight = msg.direction === 'NA_TO_CC' || msg.direction === 'USER_TO_CC'
    const isSystem = msg.direction === 'SYSTEM'
    const MAX_LEN = 2000
    const isLong = msg.content.length > MAX_LEN
    const expanded = expandedIds.has(msg.id)
    const displayContent = isLong && !expanded ? msg.content.slice(0, MAX_LEN) + '…' : msg.content

    const isLight = theme.palette.mode === 'light'
    const dirColor: Record<string, string> = {
      NA_TO_CC: theme.palette.primary.main,
      CC_TO_NA: theme.palette.success.main,
      USER_TO_CC: theme.palette.warning.main,
      SYSTEM: theme.palette.text.disabled as string,
    }
    const color = dirColor[msg.direction] ?? (theme.palette.text.secondary as string)

    const dirLabel: Record<string, string> = {
      NA_TO_CC: 'NA → CC',
      CC_TO_NA: 'CC → NA',
      USER_TO_CC: t('detail.comm.msgTypes.USER_TO_CC'),
      SYSTEM: t('detail.comm.msgTypes.SYSTEM'),
    }
    const label = dirLabel[msg.direction] ?? msg.direction
    const timeStr = new Date(msg.create_time).toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit', second: '2-digit' })

    // ── Tool call ──────────────────────────────────────────────
    if (msg.direction === 'TOOL_CALL') {
      let toolName = '?'
      let toolInput: Record<string, unknown> = {}
      try {
        const parsed = JSON.parse(msg.content)
        toolName = parsed.name ?? '?'
        toolInput = parsed.input ?? {}
      } catch { /* ignore */ }

      const tcColor = theme.palette.secondary.main
      const primaryParamKeys = ['command', 'file_path', 'pattern', 'url', 'query', 'prompt', 'notebook_path', 'path']
      let primaryKey = ''
      let primaryVal = ''
      for (const k of primaryParamKeys) {
        if (typeof toolInput[k] === 'string') { primaryKey = k; primaryVal = toolInput[k] as string; break }
      }
      if (!primaryKey && Object.keys(toolInput).length > 0) {
        const firstKey = Object.keys(toolInput)[0]
        if (firstKey !== 'description') {
          primaryKey = firstKey
          primaryVal = String(toolInput[firstKey])
        }
      }
      const description = typeof toolInput['description'] === 'string' && toolInput['description']
        ? (toolInput['description'] as string)
        : ''

      return (
        <Box key={msg.id} sx={{ display: 'flex', justifyContent: 'flex-start', mb: 0.5 }}>
          <Box sx={{
            maxWidth: '90%',
            bgcolor: alpha(tcColor, isLight ? 0.1 : 0.05),
            border: `1px solid ${alpha(tcColor, 0.18)}`,
            borderLeft: `3px solid ${alpha(tcColor, 0.55)}`,
            borderRadius: 1.5,
            px: 1.5,
            py: 0.75,
          }}>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.75, mb: (description || primaryVal) ? 0.4 : 0 }}>
              <BuildIcon sx={{ fontSize: 13, color: tcColor }} />
              <Typography variant="caption" sx={{ fontWeight: 700, color: tcColor, fontSize: '0.72rem' }}>{toolName}</Typography>
              <Typography variant="caption" sx={{ color: 'text.disabled', fontSize: '0.65rem', ml: 'auto', flexShrink: 0 }}>{timeStr}</Typography>
            </Box>
            {description && (
              <Typography variant="caption" sx={{ display: 'block', color: 'text.secondary', fontSize: '0.72rem', fontStyle: 'italic', mb: primaryVal ? 0.3 : 0, lineHeight: 1.4 }}>
                {description}
              </Typography>
            )}
            {primaryVal && (
              <Typography variant="caption" sx={{ display: 'block', fontFamily: 'monospace', color: 'text.secondary', fontSize: '0.7rem', whiteSpace: 'pre-wrap', wordBreak: 'break-all', lineHeight: 1.4 }}>
                <Box component="span" sx={{ color: alpha(tcColor, 0.7) }}>{primaryKey}: </Box>
                {primaryVal.slice(0, 300)}{primaryVal.length > 300 ? '…' : ''}
              </Typography>
            )}
            {expanded && Object.keys(toolInput).length > 0 && (
              <Box component="pre" sx={{ fontSize: '0.68rem', mt: 0.5, mb: 0, p: 0.75, bgcolor: alpha(tcColor, isLight ? 0.08 : 0.04), borderRadius: 1, overflowX: 'auto', fontFamily: 'monospace', whiteSpace: 'pre-wrap', wordBreak: 'break-word' }}>
                {JSON.stringify(toolInput, null, 2)}
              </Box>
            )}
            {Object.keys(toolInput).length > 0 && (
              <Button size="small" variant="text" onClick={() => toggleExpand(msg.id)} sx={{ mt: 0.25, fontSize: '0.68rem', p: 0, minWidth: 0, color: alpha(tcColor, 0.7) }}>
                {expanded ? t('detail.comm.collapseArgs') : t('detail.comm.expandArgs')}
              </Button>
            )}
          </Box>
        </Box>
      )
    }

    // ── Tool result ────────────────────────────────────────────
    if (msg.direction === 'TOOL_RESULT') {
      let resultContent = ''
      let isError = false
      try {
        const parsed = JSON.parse(msg.content)
        resultContent = parsed.content ?? ''
        isError = Boolean(parsed.is_error)
      } catch { /* ignore */ }

      const MAX_RESULT = 800
      const trExpanded = expandedIds.has(msg.id)
      const trLong = resultContent.length > MAX_RESULT
      const displayResult = trLong && !trExpanded ? resultContent.slice(0, MAX_RESULT) + '…' : resultContent
      const trColor = isError ? theme.palette.error.main : theme.palette.success.main

      return (
        <Box key={msg.id} sx={{ display: 'flex', justifyContent: 'flex-start', mb: 1 }}>
          <Box sx={{
            maxWidth: '90%',
            bgcolor: alpha(trColor, isLight ? 0.08 : 0.04),
            border: `1px solid ${alpha(trColor, 0.18)}`,
            borderLeft: `3px solid ${alpha(trColor, 0.45)}`,
            borderRadius: 1.5,
            px: 1.5,
            py: 0.75,
          }}>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.75, mb: displayResult ? 0.4 : 0 }}>
              {isError
                ? <ErrorOutlineIcon sx={{ fontSize: 13, color: 'error.main' }} />
                : <CheckCircleIcon sx={{ fontSize: 13, color: 'success.main' }} />}
              <Typography variant="caption" sx={{ color: isError ? 'error.main' : 'text.disabled', fontSize: '0.7rem' }}>
                {isError ? t('detail.comm.execFailed') : t('detail.comm.execDone')}
              </Typography>
              <Typography variant="caption" sx={{ color: 'text.disabled', fontSize: '0.65rem', ml: 'auto', flexShrink: 0 }}>{timeStr}</Typography>
            </Box>
            {displayResult && (
              <MarkdownRenderer sx={COMM_BUBBLE_MD_SX} enableHtml={false}>
                {displayResult}
              </MarkdownRenderer>
            )}
            {trLong && (
              <Button size="small" variant="text" onClick={() => toggleExpand(msg.id)} sx={{ mt: 0.25, fontSize: '0.68rem', p: 0, minWidth: 0, color: 'text.disabled' }}>
                {trExpanded ? t('detail.comm.collapse') : t('detail.comm.expand', { chars: resultContent.length.toLocaleString() })}
              </Button>
            )}
          </Box>
        </Box>
      )
    }

    if (isSystem) {
      return (
        <Box key={msg.id} sx={{ display: 'flex', justifyContent: 'center', my: 0.5 }}>
          <Typography variant="caption" sx={{ color: 'text.disabled', fontStyle: 'italic', fontSize: '0.7rem' }}>
            {msg.content} · {timeStr}
          </Typography>
        </Box>
      )
    }

    return (
      <Box key={msg.id} sx={{ display: 'flex', justifyContent: isRight ? 'flex-end' : 'flex-start', mb: 1.5 }}>
        <Box
          sx={{
            maxWidth: '82%',
            bgcolor: alpha(color, isLight ? 0.12 : 0.07),
            border: `1px solid ${alpha(color, 0.22)}`,
            borderRadius: 2,
            p: 1.5,
          }}
        >
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 0.75 }}>
            <Typography variant="caption" sx={{ fontWeight: 700, color, fontSize: '0.72rem' }}>
              {label}
            </Typography>
            {msg.source_chat_key && msg.source_chat_key !== '__user__' && (
              renderChatKey(msg.source_chat_key)
            )}
            <Typography variant="caption" sx={{ color: 'text.disabled', fontSize: '0.65rem', ml: 'auto', flexShrink: 0 }}>
              {timeStr}
            </Typography>
          </Box>
          <MarkdownRenderer sx={COMM_BUBBLE_MD_SX} enableHtml={false}>
            {displayContent}
          </MarkdownRenderer>
          {isLong && (
            <Button
              size="small"
              variant="text"
              onClick={() => toggleExpand(msg.id)}
              sx={{ mt: 0.5, fontSize: '0.72rem', p: 0, minWidth: 0, color }}
            >
              {expanded ? t('detail.comm.collapse') : t('detail.comm.expand', { chars: msg.content.length.toLocaleString() })}
            </Button>
          )}
        </Box>
      </Box>
    )
  }

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
      {/* 消息列表 */}
      <Box
        ref={scrollRef}
        onScroll={() => {
          const el = scrollRef.current
          if (!el) return
          // 距顶部 < 80px 时触发加载更多
          if (el.scrollTop < 80) loadMore()
          // 检测用户是否在底部
          autoScrollRef.current = el.scrollHeight - el.scrollTop - el.clientHeight < 120
        }}
        sx={{ flex: 1, minHeight: 0, overflowY: 'auto', px: 0.5, py: 1, ...SCROLLBAR_VARIANTS.thin.styles }}
      >
        {/* 加载更多指示器 */}
        {hasMore && (
          <Box sx={{ display: 'flex', justifyContent: 'center', py: 1 }}>
            {loadingMore
              ? <CircularProgress size={18} thickness={4} />
              : <Typography variant="caption" color="text.disabled" sx={{ fontSize: '0.7rem' }}>{t('detail.comm.loadMoreHint')}</Typography>
            }
          </Box>
        )}
        {messages.length === 0 ? (
          <Box sx={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', height: '100%', gap: 1.5 }}>
            <ForumIcon sx={{ fontSize: 48, opacity: 0.15 }} />
            <Typography variant="body2" color="text.disabled">{t('detail.comm.noRecords')}</Typography>
            <Typography variant="caption" color="text.disabled">{t('detail.comm.noRecordsHint')}</Typography>
          </Box>
        ) : (
          messages.map(renderMessage)
        )}
        <div ref={endRef} />
      </Box>

      {/* 手动发送区 */}
      <Box
        sx={{
          flexShrink: 0,
          borderTop: `1px solid ${theme.palette.divider}`,
          pt: 0.5,
          pb: 0.5,
          px: 0.5,
        }}
      >
        <Typography variant="caption" sx={{ color: 'warning.main', fontSize: '0.68rem', mb: 0.5, display: 'block' }}>
          {t('detail.comm.sendWarning')}
        </Typography>
        {/* CC 工作状态指示条 */}
        {ccRunning && (
          <Box sx={{
            display: 'flex',
            alignItems: 'center',
            gap: 0.75,
            mb: 0.5,
            py: 0.5,
            px: 1,
            bgcolor: alpha(theme.palette.info.main, 0.08),
            border: `1px solid ${alpha(theme.palette.info.main, 0.2)}`,
            borderRadius: 1,
          }}>
            <CircularProgress size={11} thickness={5} sx={{ color: 'info.main', flexShrink: 0 }} />
            <Typography variant="caption" sx={{ color: 'info.main', fontSize: '0.72rem' }}>
              {t('detail.comm.ccRunning')}
            </Typography>
          </Box>
        )}
        <Box sx={{ display: 'flex', gap: 1, alignItems: 'flex-end' }}>
          <TextField
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={e => {
              if (e.key === 'Enter' && !e.shiftKey && !e.nativeEvent.isComposing) {
                e.preventDefault()
                handleSend()
              }
            }}
            placeholder={isMac ? t('detail.comm.inputPlaceholderMac') : t('detail.comm.inputPlaceholderWin')}
            multiline
            maxRows={5}
            fullWidth
            size="small"
            disabled={sending || ccRunning}
          />
          <Tooltip title={ccRunning ? t('detail.comm.ccRunning') : t('detail.comm.sendTooltip')}>
            <span>
              <IconButton
                color="primary"
                onClick={handleSend}
                disabled={sending || ccRunning || !input.trim()}
                size="medium"
              >
                {sending ? <CircularProgress size={20} /> : <SendIcon />}
              </IconButton>
            </span>
          </Tooltip>
        </Box>
      </Box>
    </Box>
  )
}
