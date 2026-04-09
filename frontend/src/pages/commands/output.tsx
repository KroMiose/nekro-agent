import { useState, useEffect, useRef, useCallback, useMemo } from 'react'
import {
  Box,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Autocomplete,
  Typography,
  Card,
  Stack,
  CircularProgress,
  TextField,
  Chip,
  Tooltip,
  InputAdornment,
} from '@mui/material'
import {
  Send as SendIcon,
  DeleteOutline as ClearIcon,
} from '@mui/icons-material'
import { useQuery, useMutation } from '@tanstack/react-query'
import { useTranslation } from 'react-i18next'
import CommandOutputSegments from '../../components/common/CommandOutputSegments'
import { chatChannelApi } from '../../services/api/chat-channel'
import { commandsApi } from '../../services/api/commands'
import type { CommandOutputSegment } from '../../services/api/commands'
import { CARD_VARIANTS } from '../../theme/variants'
import IconActionButton from '../../components/common/IconActionButton'

interface OutputEntry {
  command_name: string
  status: string
  message: string
  output_segments?: CommandOutputSegment[] | null
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
  const [inputValue, setInputValue] = useState('')
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

  const enabledCommands = useMemo(() => commands.filter((cmd) => cmd.enabled), [commands])

  // 自动选中第一个频道
  useEffect(() => {
    if (!selectedChatKey && channelList?.items?.length) {
      setSelectedChatKey(channelList.items[0].chat_key)
    }
  }, [channelList, selectedChatKey])

  // 切换频道时清空输出和输入
  useEffect(() => {
    setEntries([])
    setInputValue('')
  }, [selectedChatKey])

  // 检测是否在底部附近，控制自动滚动
  const handleScroll = useCallback(() => {
    const el = containerRef.current
    if (!el) return
    const atBottom = el.scrollHeight - el.scrollTop - el.clientHeight < 40
    setAutoScroll(atBottom)
  }, [])

  // 从输入中解析命令名和参数
  const parseInput = useCallback(
    (text: string): { name: string; args: string } | null => {
      const trimmed = text.trim()
      if (!trimmed) return null
      const spaceIdx = trimmed.indexOf(' ')
      const cmdName = spaceIdx === -1 ? trimmed : trimmed.slice(0, spaceIdx)
      const args = spaceIdx === -1 ? '' : trimmed.slice(spaceIdx + 1).trim()
      const matched = enabledCommands.find(
        (c) => c.name === cmdName || c.aliases.includes(cmdName),
      )
      if (!matched) return null
      return { name: matched.name, args }
    },
    [enabledCommands],
  )

  const handleSubmit = () => {
    const parsed = parseInput(inputValue)
    if (!parsed || !selectedChatKey) return
    executeCommand({ name: parsed.name, args: parsed.args })
    setInputValue('')
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSubmit()
    }
  }

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
        output_segments: r.output_segments,
        timestamp: now + i * 0.001,
      }))
      setEntries((prev) => {
        const next = [...prev, ...newEntries]
        return next.length > MAX_ENTRIES ? next.slice(-MAX_ENTRIES) : next
      })
    },
  })

  const handleClear = () => {
    setEntries([])
  }

  return (
    <Box sx={{ height: '100%', display: 'flex', flexDirection: 'column', gap: 2, p: 2, boxSizing: 'border-box' }}>
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
              <IconActionButton size="small" onClick={handleClear} disabled={entries.length === 0}>
                <ClearIcon fontSize="small" />
              </IconActionButton>
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
                  <Box sx={{ minWidth: 0, flex: 1 }}>
                    {ev.message ? (
                      <Typography
                        component="div"
                        sx={{
                          fontSize: 'inherit',
                          color: ev.status === 'error' ? 'error.main' : 'text.primary',
                          wordBreak: 'break-word',
                          whiteSpace: 'pre-wrap',
                        }}
                      >
                        {ev.message}
                      </Typography>
                    ) : null}
                    <CommandOutputSegments
                      segments={ev.output_segments}
                      textColor={ev.status === 'error' ? 'error.main' : 'text.primary'}
                    />
                  </Box>
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

      {/* 底部：命令输入框 */}
      <Card sx={{ ...CARD_VARIANTS.default.styles, flexShrink: 0 }}>
        <Stack direction="row" spacing={1} alignItems="center" sx={{ p: 2 }}>
          <Autocomplete
            fullWidth
            freeSolo
            options={enabledCommands}
            inputValue={inputValue}
            onInputChange={(_, val, reason) => {
              if (reason !== 'reset') setInputValue(val)
            }}
            onChange={(_, val) => {
              if (val && typeof val !== 'string') {
                setInputValue(`${val.name} `)
              }
            }}
            getOptionLabel={(opt) => (typeof opt === 'string' ? opt : opt.name)}
            groupBy={(opt) =>
              typeof opt === 'string'
                ? ''
                : opt.source === 'built_in'
                  ? t('commandSidebar.builtInCommands', '内置命令')
                  : t('commandSidebar.pluginCommands', '插件命令')
            }
            filterOptions={(options, { inputValue: iv }) => {
              const q = iv.split(/\s/)[0].toLowerCase()
              if (!q) return options
              return options.filter(
                (cmd) =>
                  cmd.name.toLowerCase().includes(q) ||
                  cmd.description.toLowerCase().includes(q) ||
                  cmd.aliases.some((a) => a.toLowerCase().includes(q)),
              )
            }}
            renderOption={({ key, ...props }, opt) =>
              typeof opt === 'string' ? null : (
                <Box component="li" key={key} {...props}>
                  <Stack direction="row" spacing={1} alignItems="center">
                    <Typography variant="body2" component="span" fontFamily="monospace">
                      {opt.name}
                    </Typography>
                    <Typography variant="caption" component="span" color="text.secondary">
                      {opt.description}
                    </Typography>
                  </Stack>
                </Box>
              )
            }
            renderInput={(params) => (
              <TextField
                {...params}
                placeholder={t('commandSidebar.inputPlaceholder', '输入命令，如 help')}
                onKeyDown={handleKeyDown}
                slotProps={{
                  input: {
                    ...params.InputProps,
                    endAdornment: (
                      <InputAdornment position="end">
                        {params.InputProps.endAdornment}
                        <IconActionButton
                          tone="primary"
                          onClick={handleSubmit}
                          disabled={!parseInput(inputValue) || !selectedChatKey || isPending}
                          size="small"
                        >
                          {isPending ? <CircularProgress size={20} /> : <SendIcon />}
                        </IconActionButton>
                      </InputAdornment>
                    ),
                  },
                }}
              />
            )}
            disabled={!selectedChatKey || isPending}
            isOptionEqualToValue={(opt, val) =>
              typeof opt === 'string' || typeof val === 'string' ? false : opt.name === val.name
            }
          />
        </Stack>
      </Card>
    </Box>
  )
}
