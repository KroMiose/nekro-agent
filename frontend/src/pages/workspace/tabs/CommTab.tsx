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
  Collapse,
} from '@mui/material'
import {
  Build as BuildIcon,
  Forum as ForumIcon,
  Send as SendIcon,
  CheckCircle as CheckCircleIcon,
  ErrorOutline as ErrorOutlineIcon,
  StopCircle as StopCircleIcon,
  HourglassBottom as HourglassIcon,
  ExpandMore as ExpandMoreIcon,
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

// ── 工具调用聚合类型 ──────────────────────────────────────────────────
interface ToolCallGroup {
  toolUseId: string
  callMsg: CommLogEntry
  resultMsg: CommLogEntry | null
  toolName: string
  toolInput: Record<string, unknown>
  description: string
  primaryKey: string
  primaryVal: string
  resultContent: string
  isError: boolean
}

// 从 TOOL_CALL 消息中提取显示信息
const PRIMARY_PARAM_KEYS = ['command', 'file_path', 'pattern', 'url', 'query', 'prompt', 'notebook_path', 'path']

function parseToolCall(msg: CommLogEntry): Omit<ToolCallGroup, 'resultMsg' | 'resultContent' | 'isError'> {
  let toolName = '?'
  let toolInput: Record<string, unknown> = {}
  let toolUseId = ''
  try {
    const parsed = JSON.parse(msg.content)
    toolName = parsed.name ?? '?'
    toolInput = parsed.input ?? {}
    toolUseId = parsed.tool_use_id ?? ''
  } catch { /* ignore */ }

  let primaryKey = ''
  let primaryVal = ''
  for (const k of PRIMARY_PARAM_KEYS) {
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

  return { toolUseId, callMsg: msg, toolName, toolInput, description, primaryKey, primaryVal }
}

function parseToolResult(msg: CommLogEntry): { toolUseId: string; content: string; isError: boolean } {
  let toolUseId = ''
  let content = ''
  let isError = false
  try {
    const parsed = JSON.parse(msg.content)
    toolUseId = parsed.tool_use_id ?? ''
    content = parsed.content ?? ''
    isError = Boolean(parsed.is_error)
  } catch { /* ignore */ }
  return { toolUseId, content, isError }
}

// ── 聚合消息类型 ──────────────────────────────────────────────────────
type DisplayItem =
  | { type: 'message'; msg: CommLogEntry }
  | { type: 'tool'; group: ToolCallGroup }

export default function CommTab({ workspace, prefill, ccRunning }: { workspace: WorkspaceDetail; prefill?: string; ccRunning: boolean }) {
  const theme = useTheme()
  const notification = useNotification()
  const { t } = useTranslation('workspace')
  const [messages, setMessages] = useState<CommLogEntry[]>([])
  const [hasMore, setHasMore] = useState(false)
  const [loadingMore, setLoadingMore] = useState(false)
  const [input, setInput] = useState(prefill ?? '')
  const [sending, setSending] = useState(false)
  const [expandedIds, setExpandedIds] = useState<Set<string>>(new Set())

  const [cancelling, setCancelling] = useState(false)

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

  // 初始加载历史记录（最近50条）
  useEffect(() => {
    isInitializedRef.current = false
    commApi.getHistory(workspace.id, 50).then(r => {
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

  // SSE 实时追加（id 去重；CC_STATUS 状态事件由 detail.tsx 处理，此处过滤不显示）
  // 重连时拉取最近历史消息，补偿断线期间丢失的事件
  useEffect(() => {
    const cancel = streamCommLog(
      workspace.id,
      (entry) => {
        if (entry.direction === 'CC_STATUS') return
        setMessages(prev =>
          prev.some(m => m.id === entry.id) ? prev : [...prev, entry]
        )
      },
      (err) => { console.error('comm stream error', err) },
      () => {
        // SSE 重连：拉取最近 20 条历史消息，利用 id 去重自动合并
        commApi.getHistory(workspace.id, 20).then(r => {
          if (r.items.length > 0) {
            setMessages(prev => {
              const existingIds = new Set(prev.map(m => m.id))
              const newItems = r.items.filter(item => !existingIds.has(item.id))
              if (newItems.length === 0) return prev
              return [...prev, ...newItems].sort((a, b) => a.id - b.id)
            })
          }
        }).catch(() => {})
      },
    )
    return cancel
  }, [workspace.id])

  // ── 将原始消息聚合为 DisplayItem[] ──────────────────────────────────
  const displayItems = useMemo<DisplayItem[]>(() => {
    const items: DisplayItem[] = []
    // tool_use_id → ToolCallGroup 索引
    const toolMap = new Map<string, ToolCallGroup>()
    // 已被合并的 TOOL_RESULT msg.id 集合（避免重复渲染）
    const mergedResultIds = new Set<number>()

    // 第一遍：收集所有 TOOL_CALL 并建立索引
    for (const msg of messages) {
      if (msg.direction === 'TOOL_CALL') {
        const parsed = parseToolCall(msg)
        if (parsed.toolUseId) {
          toolMap.set(parsed.toolUseId, {
            ...parsed,
            resultMsg: null,
            resultContent: '',
            isError: false,
          })
        }
      }
    }

    // 第二遍：匹配 TOOL_RESULT
    for (const msg of messages) {
      if (msg.direction === 'TOOL_RESULT') {
        const parsed = parseToolResult(msg)
        if (parsed.toolUseId && toolMap.has(parsed.toolUseId)) {
          const group = toolMap.get(parsed.toolUseId)!
          group.resultMsg = msg
          group.resultContent = parsed.content
          group.isError = parsed.isError
          mergedResultIds.add(msg.id)
        }
      }
    }

    // 第三遍：构建显示列表
    for (const msg of messages) {
      if (msg.direction === 'TOOL_CALL') {
        let toolUseId = ''
        try { toolUseId = JSON.parse(msg.content).tool_use_id ?? '' } catch { /* ignore */ }
        const group = toolUseId ? toolMap.get(toolUseId) : undefined
        if (group) {
          items.push({ type: 'tool', group })
        } else {
          items.push({ type: 'message', msg })
        }
      } else if (msg.direction === 'TOOL_RESULT' && mergedResultIds.has(msg.id)) {
        // 已合并到 TOOL_CALL 卡片中，跳过
        continue
      } else {
        items.push({ type: 'message', msg })
      }
    }

    return items
  }, [messages])

  // 新消息时如果用户在底部则自动滚动
  useEffect(() => {
    if (messages.length === 0) return
    const el = scrollRef.current
    if (!isInitializedRef.current) {
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

  const handleForceCancel = async () => {
    if (cancelling) return
    setCancelling(true)
    try {
      await commApi.forceCancel(workspace.id)
      notification.success(t('detail.comm.notifications.cancelSuccess'))
    } catch (e) {
      notification.error(t('detail.comm.notifications.cancelFailed', { message: (e as Error).message }))
    } finally {
      setCancelling(false)
    }
  }

  const toggleExpand = (key: string) => {
    setExpandedIds(prev => {
      const next = new Set(prev)
      if (next.has(key)) next.delete(key)
      else next.add(key)
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

  const isLight = theme.palette.mode === 'light'
  const tcColor = theme.palette.secondary.main

  // ── 合并后的工具调用卡片 ───────────────────────────────────────────
  const renderToolCard = (group: ToolCallGroup) => {
    const { callMsg, resultMsg, toolName, toolInput, description, primaryKey, primaryVal, resultContent, isError } = group
    const expandKey = `tool-${group.toolUseId}`
    const expanded = expandedIds.has(expandKey)
    const isDone = resultMsg !== null
    const timeStr = new Date(callMsg.create_time).toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit', second: '2-digit' })

    // 计算耗时
    let durationStr = ''
    if (resultMsg) {
      const callTime = new Date(callMsg.create_time).getTime()
      const resultTime = new Date(resultMsg.create_time).getTime()
      const seconds = (resultTime - callTime) / 1000
      durationStr = seconds < 1 ? '<1s' : `${seconds.toFixed(1)}s`
    }

    // 状态颜色
    const statusColor = !isDone
      ? theme.palette.warning.main
      : isError
        ? theme.palette.error.main
        : theme.palette.success.main

    const borderColor = !isDone ? alpha(tcColor, 0.35) : alpha(statusColor, 0.45)

    return (
      <Box key={`tool-${callMsg.id}`} sx={{ mb: 0.4 }}>
        {/* 摘要行 — 固定宽度范围，始终可见 */}
        <Box
          onClick={() => toggleExpand(expandKey)}
          sx={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: 0.75,
            minWidth: 180,
            maxWidth: '80%',
            px: 1.25,
            py: 0.4,
            cursor: 'pointer',
            userSelect: 'none',
            bgcolor: alpha(tcColor, isLight ? 0.08 : 0.12),
            border: `1px solid ${alpha(tcColor, isLight ? 0.18 : 0.25)}`,
            borderLeft: `3px solid ${borderColor}`,
            borderRadius: 1.5,
            '&:hover': { bgcolor: alpha(tcColor, isLight ? 0.13 : 0.18) },
            transition: 'background-color 0.15s',
          }}
        >
          {/* 状态图标 */}
          {!isDone ? (
            <HourglassIcon sx={{ fontSize: 13, color: 'warning.main', animation: 'spin 1.5s linear infinite', '@keyframes spin': { '100%': { transform: 'rotate(360deg)' } } }} />
          ) : isError ? (
            <ErrorOutlineIcon sx={{ fontSize: 13, color: 'error.main' }} />
          ) : (
            <CheckCircleIcon sx={{ fontSize: 13, color: 'success.main' }} />
          )}

          {/* 工具名 */}
          <Typography variant="caption" sx={{ fontWeight: 700, color: tcColor, fontSize: '0.72rem', flexShrink: 0 }}>
            {toolName}
          </Typography>

          {/* 描述摘要 */}
          {(description || primaryVal) && (
            <Typography
              variant="caption"
              sx={{
                flex: 1,
                minWidth: 0,
                color: 'text.secondary',
                fontSize: '0.68rem',
                fontStyle: description ? 'italic' : 'normal',
                fontFamily: description ? 'inherit' : 'monospace',
                overflow: 'hidden',
                textOverflow: 'ellipsis',
                whiteSpace: 'nowrap',
              }}
            >
              {description || `${primaryKey}: ${primaryVal}`}
            </Typography>
          )}

          {/* 耗时 / 执行中 */}
          <Typography variant="caption" sx={{ color: statusColor, fontSize: '0.64rem', flexShrink: 0, fontWeight: 500 }}>
            {!isDone ? t('detail.comm.toolRunning') : durationStr}
          </Typography>

          {/* 时间戳 */}
          <Typography variant="caption" sx={{ color: 'text.disabled', fontSize: '0.62rem', flexShrink: 0 }}>
            {timeStr}
          </Typography>

          {/* 展开箭头 */}
          <ExpandMoreIcon sx={{
            fontSize: 14,
            color: 'text.disabled',
            transition: 'transform 0.2s',
            transform: expanded ? 'rotate(180deg)' : 'rotate(0deg)',
            flexShrink: 0,
          }} />
        </Box>

        {/* 展开详情 — 独立区块 */}
        <Collapse in={expanded} timeout={200}>
          <Box sx={{
            mt: 0.25,
            ml: 1.5,
            maxWidth: '88%',
            bgcolor: alpha(tcColor, isLight ? 0.06 : 0.08),
            border: `1px solid ${alpha(tcColor, isLight ? 0.15 : 0.20)}`,
            borderRadius: 1,
            px: 1.25,
            py: 0.75,
          }}>
            {/* 输入参数 */}
            {primaryVal && (
              <Typography variant="caption" sx={{
                display: 'block', fontFamily: 'monospace', color: 'text.secondary',
                fontSize: '0.7rem', whiteSpace: 'pre-wrap', wordBreak: 'break-all',
                lineHeight: 1.4,
              }}>
                <Box component="span" sx={{ color: alpha(tcColor, 0.7) }}>{primaryKey}: </Box>
                {primaryVal.slice(0, 500)}{primaryVal.length > 500 ? '…' : ''}
              </Typography>
            )}

            {/* 完整参数 JSON（二级展开） */}
            {Object.keys(toolInput).length > 1 && (
              <>
                <Button
                  size="small" variant="text"
                  onClick={(e) => { e.stopPropagation(); toggleExpand(`args-${group.toolUseId}`) }}
                  sx={{ mt: 0.25, fontSize: '0.66rem', p: 0, minWidth: 0, color: alpha(tcColor, 0.6) }}
                >
                  {expandedIds.has(`args-${group.toolUseId}`) ? t('detail.comm.collapseArgs') : t('detail.comm.expandArgs')}
                </Button>
                <Collapse in={expandedIds.has(`args-${group.toolUseId}`)} timeout={150}>
                  <Box component="pre" sx={{
                    fontSize: '0.66rem', mt: 0.5, mb: 0, p: 0.75,
                    bgcolor: alpha(tcColor, isLight ? 0.10 : 0.12),
                    borderRadius: 1, overflowX: 'auto', fontFamily: 'monospace',
                    whiteSpace: 'pre-wrap', wordBreak: 'break-word',
                  }}>
                    {JSON.stringify(toolInput, null, 2)}
                  </Box>
                </Collapse>
              </>
            )}

            {/* 执行结果 */}
            {isDone && (
              <Box sx={{ mt: primaryVal || Object.keys(toolInput).length > 1 ? 0.75 : 0 }}>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5, mb: 0.4 }}>
                  {isError
                    ? <ErrorOutlineIcon sx={{ fontSize: 11, color: 'error.main' }} />
                    : <CheckCircleIcon sx={{ fontSize: 11, color: 'success.main' }} />}
                  <Typography variant="caption" sx={{ color: isError ? 'error.main' : 'success.main', fontSize: '0.66rem', fontWeight: 500 }}>
                    {isError ? t('detail.comm.execFailed') : t('detail.comm.execDone')}
                  </Typography>
                </Box>
                {resultContent && (
                  <>
                    <Box sx={{
                      bgcolor: alpha(isError ? theme.palette.error.main : theme.palette.success.main, isLight ? 0.08 : 0.12),
                      borderRadius: 1,
                      p: 0.75,
                      maxHeight: expandedIds.has(`result-${group.toolUseId}`) ? 'none' : '120px',
                      overflow: 'hidden',
                      position: 'relative',
                    }}>
                      <MarkdownRenderer sx={{ ...COMM_BUBBLE_MD_SX, fontSize: '0.76rem', '& p': { ...COMM_BUBBLE_MD_SX['& p'], fontSize: '0.76rem' } }} enableHtml={false}>
                        {expandedIds.has(`result-${group.toolUseId}`)
                          ? resultContent
                          : resultContent.slice(0, 600) + (resultContent.length > 600 ? '…' : '')}
                      </MarkdownRenderer>
                      {!expandedIds.has(`result-${group.toolUseId}`) && resultContent.length > 200 && (
                        <Box sx={{
                          position: 'absolute', bottom: 0, left: 0, right: 0, height: 32,
                          background: isLight
                            ? `linear-gradient(transparent, ${alpha(theme.palette.background.paper, 0.95)})`
                            : `linear-gradient(transparent, ${alpha(theme.palette.background.paper, 0.9)})`,
                        }} />
                      )}
                    </Box>
                    {resultContent.length > 200 && (
                      <Button
                        size="small" variant="text"
                        onClick={(e) => { e.stopPropagation(); toggleExpand(`result-${group.toolUseId}`) }}
                        sx={{ mt: 0.25, fontSize: '0.66rem', p: 0, minWidth: 0, color: 'text.disabled' }}
                      >
                        {expandedIds.has(`result-${group.toolUseId}`)
                          ? t('detail.comm.collapse')
                          : t('detail.comm.expand', { chars: resultContent.length.toLocaleString() })}
                      </Button>
                    )}
                  </>
                )}
              </Box>
            )}
          </Box>
        </Collapse>
      </Box>
    )
  }

  // ── 普通消息渲染 ────────────────────────────────────────────────────
  const renderMessage = (msg: CommLogEntry) => {
    const isRight = msg.direction === 'NA_TO_CC' || msg.direction === 'USER_TO_CC'
    const isSystem = msg.direction === 'SYSTEM'
    const MAX_LEN = 2000
    const isLong = msg.content.length > MAX_LEN
    const expanded = expandedIds.has(`msg-${msg.id}`)
    const displayContent = isLong && !expanded ? msg.content.slice(0, MAX_LEN) + '…' : msg.content

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

    // 未匹配到 TOOL_CALL group 的独立 TOOL_CALL（不应发生，但作为 fallback）
    if (msg.direction === 'TOOL_CALL') {
      let toolName = '?'
      try { toolName = JSON.parse(msg.content).name ?? '?' } catch { /* ignore */ }
      return (
        <Box key={msg.id} sx={{ display: 'flex', justifyContent: 'flex-start', mb: 0.4 }}>
          <Box sx={{
            maxWidth: '90%',
            bgcolor: alpha(tcColor, isLight ? 0.08 : 0.12),
            border: `1px solid ${alpha(tcColor, isLight ? 0.18 : 0.25)}`,
            borderLeft: `3px solid ${alpha(tcColor, 0.35)}`,
            borderRadius: 1.5, px: 1.25, py: 0.5,
          }}>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.75 }}>
              <BuildIcon sx={{ fontSize: 13, color: tcColor }} />
              <Typography variant="caption" sx={{ fontWeight: 700, color: tcColor, fontSize: '0.72rem' }}>{toolName}</Typography>
              <Typography variant="caption" sx={{ color: 'text.disabled', fontSize: '0.65rem', ml: 'auto' }}>{timeStr}</Typography>
            </Box>
          </Box>
        </Box>
      )
    }

    // 未合并的独立 TOOL_RESULT fallback
    if (msg.direction === 'TOOL_RESULT') {
      let resultContent = ''
      let isError = false
      try {
        const parsed = JSON.parse(msg.content)
        resultContent = parsed.content ?? ''
        isError = Boolean(parsed.is_error)
      } catch { /* ignore */ }
      const trColor = isError ? theme.palette.error.main : theme.palette.success.main
      return (
        <Box key={msg.id} sx={{ display: 'flex', justifyContent: 'flex-start', mb: 0.4 }}>
          <Box sx={{
            maxWidth: '90%',
            bgcolor: alpha(trColor, isLight ? 0.08 : 0.12),
            border: `1px solid ${alpha(trColor, isLight ? 0.18 : 0.25)}`,
            borderLeft: `3px solid ${alpha(trColor, 0.35)}`,
            borderRadius: 1.5, px: 1.25, py: 0.5,
          }}>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
              {isError ? <ErrorOutlineIcon sx={{ fontSize: 13, color: 'error.main' }} /> : <CheckCircleIcon sx={{ fontSize: 13, color: 'success.main' }} />}
              <Typography variant="caption" sx={{ color: isError ? 'error.main' : 'text.disabled', fontSize: '0.7rem' }}>
                {isError ? t('detail.comm.execFailed') : t('detail.comm.execDone')}
              </Typography>
              <Typography variant="caption" sx={{ color: 'text.disabled', fontSize: '0.65rem', ml: 'auto' }}>{timeStr}</Typography>
            </Box>
            {resultContent && (
              <Typography variant="caption" sx={{ display: 'block', fontSize: '0.7rem', color: 'text.secondary', mt: 0.3, fontFamily: 'monospace' }}>
                {resultContent.slice(0, 200)}{resultContent.length > 200 ? '…' : ''}
              </Typography>
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
            background: isRight
              ? (isLight ? 'rgba(0, 0, 0, 0.04)' : 'rgba(255, 255, 255, 0.09)')
              : (isLight ? `rgba(56, 139, 253, 0.08)` : `rgba(56, 139, 253, 0.18)`),
            borderRadius: isRight ? '12px 2px 12px 12px' : '2px 12px 12px 12px',
            px: 1.5,
            py: 0.8,
            transition: 'background 0.15s',
            '&:hover': {
              background: isRight
                ? (isLight ? 'rgba(0, 0, 0, 0.06)' : 'rgba(255, 255, 255, 0.13)')
                : (isLight ? `rgba(56, 139, 253, 0.13)` : `rgba(56, 139, 253, 0.25)`),
            },
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
              onClick={() => toggleExpand(`msg-${msg.id}`)}
              sx={{ mt: 0.5, fontSize: '0.72rem', p: 0, minWidth: 0, color }}
            >
              {expanded ? t('detail.comm.collapse') : t('detail.comm.expand', { chars: msg.content.length.toLocaleString() })}
            </Button>
          )}
        </Box>
      </Box>
    )
  }

  // ── 渲染 DisplayItem ─────────────────────────────────────────────
  const renderDisplayItem = (item: DisplayItem, _idx: number) => {
    if (item.type === 'tool') return renderToolCard(item.group)
    return renderMessage(item.msg)
  }

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
      {/* 消息列表 */}
      <Box
        ref={scrollRef}
        onScroll={() => {
          const el = scrollRef.current
          if (!el) return
          if (el.scrollTop < 80) loadMore()
          autoScrollRef.current = el.scrollHeight - el.scrollTop - el.clientHeight < 120
        }}
        sx={{ flex: 1, minHeight: 0, overflowY: 'auto', px: 2, py: 1, ...SCROLLBAR_VARIANTS.thin.styles }}
      >
        {/* 顶部加载区：有更多时显示可点击按钮；加载中显示进度圈；无更多且有消息时提示已加载全部 */}
        {messages.length > 0 && (
          <Box sx={{ display: 'flex', justifyContent: 'center', py: 0.75 }}>
            {loadingMore ? (
              <CircularProgress size={18} thickness={4} />
            ) : hasMore ? (
              <Button
                size="small"
                variant="text"
                onClick={loadMore}
                sx={{ fontSize: '0.72rem', color: 'text.secondary', py: 0.25 }}
              >
                {t('detail.comm.loadMore')}
              </Button>
            ) : (
              <Typography variant="caption" color="text.disabled" sx={{ fontSize: '0.68rem' }}>
                {t('detail.comm.noMoreMessages')}
              </Typography>
            )}
          </Box>
        )}
        {displayItems.length === 0 ? (
          <Box sx={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', height: '100%', gap: 1.5 }}>
            <ForumIcon sx={{ fontSize: 48, opacity: 0.15 }} />
            <Typography variant="body2" color="text.disabled">{t('detail.comm.noRecords')}</Typography>
            <Typography variant="caption" color="text.disabled">{t('detail.comm.noRecordsHint')}</Typography>
          </Box>
        ) : (
          displayItems.map(renderDisplayItem)
        )}
        <div ref={endRef} />
      </Box>

      {/* 发送区 */}
      <Box
        sx={{
          flexShrink: 0,
          borderTop: `1px solid ${theme.palette.divider}`,
          pt: 0.5,
          pb: 0.5,
          px: 0.5,
        }}
      >
        {/* CC 工作中：统一状态条（替代原先的警告+指示条双层设计） */}
        {ccRunning && (
          <Box sx={{
            display: 'flex',
            alignItems: 'center',
            gap: 0.75,
            mb: 0.5,
            py: 0.4,
            px: 1,
            bgcolor: alpha(theme.palette.success.main, 0.08),
            border: `1px solid ${alpha(theme.palette.success.main, 0.2)}`,
            borderRadius: 1,
          }}>
            <CircularProgress size={11} thickness={5} sx={{ color: 'success.main', flexShrink: 0 }} />
            <Typography variant="caption" sx={{ color: 'success.main', fontSize: '0.72rem', fontWeight: 500 }}>
              {t('detail.comm.ccRunning')}
            </Typography>
            <Tooltip title={t('detail.comm.forceCancel')}>
              <span style={{ marginLeft: 'auto' }}>
                <IconButton
                  size="small"
                  onClick={handleForceCancel}
                  disabled={cancelling}
                  sx={{ color: 'error.main', p: 0.25 }}
                >
                  {cancelling
                    ? <CircularProgress size={14} sx={{ color: 'error.main' }} />
                    : <StopCircleIcon sx={{ fontSize: 16 }} />}
                </IconButton>
              </span>
            </Tooltip>
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
            placeholder={
              ccRunning
                ? t('detail.comm.ccRunning')
                : (isMac ? t('detail.comm.inputPlaceholderMac') : t('detail.comm.inputPlaceholderWin'))
            }
            multiline
            maxRows={5}
            fullWidth
            size="small"
            disabled={sending || ccRunning}
            sx={{
              '& .MuiOutlinedInput-root': {
                fontSize: '0.85rem',
              },
            }}
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
