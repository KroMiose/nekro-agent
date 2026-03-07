import { useState, useEffect, useRef, useCallback } from 'react'
import {
  Box,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  ListSubheader,
  Typography,
  Card,
  Stack,
  CircularProgress,
  TextField,
  IconButton,
  Chip,
  Tooltip,
} from '@mui/material'
import {
  Send as SendIcon,
  DeleteOutline as ClearIcon,
} from '@mui/icons-material'
import { useQuery, useMutation } from '@tanstack/react-query'
import { useTranslation } from 'react-i18next'
import { chatChannelApi } from '../../services/api/chat-channel'
import { commandsApi } from '../../services/api/commands'
import { CARD_VARIANTS } from '../../theme/variants'

interface OutputEntry {
  command_name: string
  status: string
  message: string
  timestamp: number
}

const MAX_ENTRIES = 200

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

export default function CommandOutputPage() {
  const { t } = useTranslation('chat-channel')
  const [selectedChatKey, setSelectedChatKey] = useState<string>('')
  const [selectedCommand, setSelectedCommand] = useState<string>('')
  const [argsInput, setArgsInput] = useState('')
  const [entries, setEntries] = useState<OutputEntry[]>([])
  const [autoScroll, setAutoScroll] = useState(true)
  const bottomRef = useRef<HTMLDivElement>(null)
  const containerRef = useRef<HTMLDivElement>(null)

  const { data: channelList, isLoading } = useQuery({
    queryKey: ['chat-channels-for-commands'],
    queryFn: () => chatChannelApi.getList({ page: 1, page_size: 200 }),
  })

  // 获取命令列表
  const { data: commands = [] } = useQuery({
    queryKey: ['commands-for-output', selectedChatKey],
    queryFn: () => commandsApi.listCommands(selectedChatKey || undefined),
    enabled: !!selectedChatKey,
  })

  // 自动选中第一个频道
  useEffect(() => {
    if (!selectedChatKey && channelList?.items?.length) {
      setSelectedChatKey(channelList.items[0].chat_key)
    }
  }, [channelList, selectedChatKey])

  // 切换频道时清空输出和命令选择
  useEffect(() => {
    setEntries([])
    setSelectedCommand('')
    setArgsInput('')
  }, [selectedChatKey])

  // 检测是否在底部附近，控制自动滚动
  const handleScroll = useCallback(() => {
    const el = containerRef.current
    if (!el) return
    const atBottom = el.scrollHeight - el.scrollTop - el.clientHeight < 40
    setAutoScroll(atBottom)
  }, [])

  // 判断当前选中命令是否接受额外参数
  const selectedCmdHasArgs = (() => {
    if (!selectedCommand) return false
    const cmd = commands.find((c) => c.name === selectedCommand)
    if (!cmd?.params_schema) return false
    const props = cmd.params_schema.properties as Record<string, unknown> | undefined
    return !!props && Object.keys(props).length > 0
  })()

  // 自动滚动到底部
  useEffect(() => {
    if (autoScroll) {
      bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
    }
  }, [entries, autoScroll])

  const { mutate: executeCommand, isPending } = useMutation({
    mutationFn: ({ name, args }: { name: string; args: string }) =>
      commandsApi.webuiExecute(name, selectedChatKey, args),
    onSuccess: (data, variables) => {
      const now = Date.now() / 1000
      const newEntries: OutputEntry[] = data.responses.map((r, i) => ({
        command_name: variables.name,
        status: r.status,
        message: r.message,
        timestamp: now + i * 0.001,
      }))
      setEntries((prev) => {
        const next = [...prev, ...newEntries]
        return next.length > MAX_ENTRIES ? next.slice(-MAX_ENTRIES) : next
      })
    },
  })

  const handleSubmit = () => {
    if (!selectedCommand || !selectedChatKey) return
    executeCommand({ name: selectedCommand, args: argsInput.trim() })
    setArgsInput('')
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSubmit()
    }
  }

  const handleClear = () => {
    setEntries([])
  }

  return (
    <Box sx={{ height: '100%', display: 'flex', flexDirection: 'column', gap: 2, p: 2 }}>
      {/* 顶部：频道选择 */}
      <Card sx={{ ...CARD_VARIANTS.default.styles, flexShrink: 0 }}>
        <Stack direction="row" alignItems="center" spacing={2} sx={{ p: 2 }}>
          <FormControl size="small" fullWidth>
            <InputLabel>{t('commandSidebar.selectChannel')}</InputLabel>
            <Select
              value={selectedChatKey}
              label={t('commandSidebar.selectChannel')}
              onChange={(e) => setSelectedChatKey(e.target.value)}
            >
              {isLoading ? (
                <MenuItem disabled>
                  <CircularProgress size={16} sx={{ mr: 1 }} /> Loading...
                </MenuItem>
              ) : (
                channelList?.items?.map((ch) => (
                  <MenuItem key={ch.chat_key} value={ch.chat_key}>
                    <Typography variant="body2" component="span" noWrap>
                      {ch.channel_name || ch.chat_key}
                    </Typography>
                    <Typography
                      variant="caption"
                      component="span"
                      color="text.secondary"
                      sx={{ ml: 1, fontFamily: 'monospace' }}
                    >
                      {ch.chat_key}
                    </Typography>
                  </MenuItem>
                ))
              )}
            </Select>
          </FormControl>
          <Tooltip title={t('commandSidebar.clear')}>
            <span>
              <IconButton size="small" onClick={handleClear} disabled={entries.length === 0}>
                <ClearIcon fontSize="small" />
              </IconButton>
            </span>
          </Tooltip>
        </Stack>
      </Card>

      {/* 中间：命令输出日志 */}
      <Card sx={{ ...CARD_VARIANTS.default.styles, flex: 1, overflow: 'hidden', display: 'flex', flexDirection: 'column' }}>
        {selectedChatKey ? (
          <Box
            ref={containerRef}
            onScroll={handleScroll}
            sx={{
              flex: 1,
              overflow: 'auto',
              px: 1.5,
              py: 1,
              fontFamily: 'monospace',
              fontSize: '0.75rem',
              lineHeight: 1.6,
            }}
          >
            {entries.length === 0 ? (
              <Box sx={{ textAlign: 'center', py: 3 }}>
                <Typography variant="body2" color="text.secondary">
                  {t('commandSidebar.noOutput')}
                </Typography>
                <Typography variant="caption" color="text.disabled" sx={{ mt: 0.5, display: 'block' }}>
                  {t('commandSidebar.outputHint')}
                </Typography>
              </Box>
            ) : (
              entries.map((ev, idx) => (
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
                      whiteSpace: 'pre-wrap',
                    }}
                  >
                    {ev.message}
                  </Typography>
                </Box>
              ))
            )}
            <div ref={bottomRef} />
          </Box>
        ) : (
          <Box className="flex items-center justify-center h-full">
            <Typography variant="body2" color="text.secondary">
              {t('commandSidebar.selectChannelHint')}
            </Typography>
          </Box>
        )}
      </Card>

      {/* 底部：命令选择 + 参数输入 */}
      <Card sx={{ ...CARD_VARIANTS.default.styles, flexShrink: 0 }}>
        <Stack direction="row" spacing={1} alignItems="center" sx={{ p: 2 }}>
          <FormControl size="small" sx={{ minWidth: 200 }}>
            <InputLabel>{t('commandSidebar.selectCommand')}</InputLabel>
            <Select
              value={selectedCommand}
              label={t('commandSidebar.selectCommand')}
              onChange={(e) => setSelectedCommand(e.target.value)}
              disabled={!selectedChatKey || isPending}
              renderValue={(val) => `/${val}`}
            >
              {(() => {
                const enabled = commands.filter((cmd) => cmd.enabled)
                const builtIn = enabled.filter((cmd) => cmd.source === 'built_in')
                const plugin = enabled.filter((cmd) => cmd.source !== 'built_in')
                const items: React.ReactNode[] = []
                if (builtIn.length > 0) {
                  items.push(<ListSubheader key="__builtin">{t('commandSidebar.builtInCommands', '内置命令')}</ListSubheader>)
                  builtIn.forEach((cmd) => items.push(
                    <MenuItem key={cmd.name} value={cmd.name}>
                      <Stack direction="row" spacing={1} alignItems="center">
                        <Typography variant="body2" component="span" fontFamily="monospace">
                          /{cmd.name}
                        </Typography>
                        <Typography variant="caption" component="span" color="text.secondary">
                          {cmd.description}
                        </Typography>
                      </Stack>
                    </MenuItem>
                  ))
                }
                if (plugin.length > 0) {
                  items.push(<ListSubheader key="__plugin">{t('commandSidebar.pluginCommands', '插件命令')}</ListSubheader>)
                  plugin.forEach((cmd) => items.push(
                    <MenuItem key={cmd.name} value={cmd.name}>
                      <Stack direction="row" spacing={1} alignItems="center">
                        <Typography variant="body2" component="span" fontFamily="monospace">
                          /{cmd.name}
                        </Typography>
                        <Typography variant="caption" component="span" color="text.secondary">
                          {cmd.description}
                        </Typography>
                      </Stack>
                    </MenuItem>
                  ))
                }
                return items
              })()}
            </Select>
          </FormControl>
          <TextField
            size="small"
            fullWidth
            placeholder={selectedCmdHasArgs ? t('commandSidebar.argsPlaceholder', '输入参数...') : t('commandSidebar.noArgsNeeded', '该命令无需参数')}
            value={argsInput}
            onChange={(e) => setArgsInput(e.target.value)}
            onKeyDown={handleKeyDown}
            disabled={!selectedCommand || isPending || !selectedCmdHasArgs}
          />
          <IconButton
            onClick={handleSubmit}
            disabled={!selectedCommand || !selectedChatKey || isPending}
            color="primary"
          >
            {isPending ? <CircularProgress size={20} /> : <SendIcon />}
          </IconButton>
        </Stack>
      </Card>
    </Box>
  )
}
