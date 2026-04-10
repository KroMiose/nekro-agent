import { useCallback, useDeferredValue, useEffect, useMemo, useRef, useState } from 'react'
import {
  Alert,
  Box,
  Card,
  Chip,
  CircularProgress,
  Divider,
  FormControl,
  InputAdornment,
  InputLabel,
  MenuItem,
  Select,
  Stack,
  TextField,
  Typography,
  useMediaQuery,
  useTheme,
} from '@mui/material'
import {
  ArrowOutward as ArrowOutwardIcon,
  Send as SendIcon,
  Terminal as TerminalIcon,
  Tune as TuneIcon,
} from '@mui/icons-material'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useSearchParams } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { alpha } from '@mui/material/styles'
import type { TFunction } from 'i18next'
import SearchField from '../../components/common/SearchField'
import FilterSelect from '../../components/common/FilterSelect'
import ActionButton from '../../components/common/ActionButton'
import CommandOutputLog from '../chat-channel/components/sidebar/CommandOutputLog'
import { commandsApi, type CommandState } from '../../services/api/commands'
import { getLocalizedText } from '../../services/api/types'
import { CARD_VARIANTS } from '../../theme/variants'
import { useNotification } from '../../hooks/useNotification'
import { useChannelDirectoryContext } from '../../contexts/ChannelDirectoryContext'

type ManageScope = 'system' | 'channel'

const PERMISSION_COLORS: Record<string, 'error' | 'warning' | 'success' | 'default' | 'info'> = {
  super_user: 'error',
  advanced: 'warning',
  user: 'info',
  public: 'success',
}

function getCommandDescription(cmd: CommandState, lang: string) {
  return getLocalizedText(cmd.i18n_description, cmd.description, lang)
}

function getCommandUsage(cmd: CommandState, lang: string) {
  return getLocalizedText(cmd.i18n_usage, cmd.usage, lang)
}

function getCommandCategory(cmd: CommandState, lang: string) {
  return getLocalizedText(cmd.i18n_category, cmd.category, lang)
}

function getSourceLabel(
  source: string,
  t: TFunction<'settings'>,
) {
  return source === 'built_in'
    ? t('commands.sources.builtIn', '内置')
    : t('commands.sources.plugin', '插件')
}

function getEffectiveStateLabel(
  cmd: CommandState,
  scope: ManageScope,
  t: TFunction<'settings'>,
) {
  if (scope === 'system') {
    return cmd.enabled
      ? t('commands.state.systemEnabled', '系统启用')
      : t('commands.state.systemDisabled', '系统禁用')
  }

  if (cmd.has_channel_override) {
    return cmd.enabled
      ? t('commands.state.channelEnabled', '频道覆盖启用')
      : t('commands.state.channelDisabled', '频道覆盖禁用')
  }

  return cmd.enabled
    ? t('commands.state.inheritedEnabled', '继承系统启用')
    : t('commands.state.inheritedDisabled', '继承系统禁用')
}

function getEffectiveStateColor(
  cmd: CommandState,
  scope: ManageScope,
): 'success' | 'warning' | 'default' {
  if (scope === 'system') {
    return cmd.enabled ? 'success' : 'default'
  }
  if (cmd.has_channel_override) {
    return cmd.enabled ? 'success' : 'warning'
  }
  return cmd.enabled ? 'success' : 'default'
}

function isManageScope(value: string | null): value is ManageScope {
  return value === 'system' || value === 'channel'
}

export default function CommandCenterPage() {
  const theme = useTheme()
  const isMobile = useMediaQuery(theme.breakpoints.down('lg'))
  const notification = useNotification()
  const queryClient = useQueryClient()
  const { t, i18n } = useTranslation('settings')
  const { channels, isLoading: channelsLoading } = useChannelDirectoryContext()
  const [searchParams, setSearchParams] = useSearchParams()
  const urlSearch = searchParams.get('search') ?? ''
  const requestedScope = searchParams.get('scope')
  const scope: ManageScope = isManageScope(requestedScope) ? requestedScope : 'system'
  const managementChatKey = searchParams.get('chat_key') ?? ''
  const executeChatKey = searchParams.get('execute_chat_key') ?? ''
  const categoryFilter = searchParams.get('category') ?? ''
  const sourceFilter = searchParams.get('source') ?? ''
  const permissionFilter = searchParams.get('permission') ?? ''
  const selectedCommandName = searchParams.get('command') ?? ''
  const focus = searchParams.get('focus') ?? ''
  const [searchInput, setSearchInput] = useState(urlSearch)
  const deferredSearchInput = useDeferredValue(searchInput)
  const [commandLine, setCommandLine] = useState('')
  const executePanelRef = useRef<HTMLDivElement | null>(null)

  const updateParams = useCallback(
    (updates: Record<string, string | null>, replace = true) => {
      const nextParams = new URLSearchParams(searchParams)

      Object.entries(updates).forEach(([key, value]) => {
        if (!value) {
          nextParams.delete(key)
        } else {
          nextParams.set(key, value)
        }
      })

      setSearchParams(nextParams, { replace })
    },
    [searchParams, setSearchParams],
  )

  useEffect(() => {
    setSearchInput(urlSearch)
  }, [urlSearch])

  useEffect(() => {
    const normalizedSearch = deferredSearchInput.trim()
    if (normalizedSearch === urlSearch.trim()) {
      return
    }
    updateParams({ search: normalizedSearch || null })
  }, [deferredSearchInput, updateParams, urlSearch])

  useEffect(() => {
    if (scope !== 'channel' || channels.length === 0 || managementChatKey) {
      return
    }
    updateParams({
      chat_key: channels[0].chat_key,
      execute_chat_key: executeChatKey || channels[0].chat_key,
    })
  }, [channels, executeChatKey, managementChatKey, scope, updateParams])

  useEffect(() => {
    if (scope !== 'channel' || !managementChatKey || executeChatKey) {
      return
    }
    updateParams({ execute_chat_key: managementChatKey })
  }, [executeChatKey, managementChatKey, scope, updateParams])

  const managementQueryChatKey = scope === 'channel' ? managementChatKey || undefined : undefined

  const { data: commands = [], isLoading: commandsLoading } = useQuery({
    queryKey: ['command-center', 'commands', managementQueryChatKey ?? 'system'],
    queryFn: () => commandsApi.listCommands(managementQueryChatKey),
  })

  const { data: executableCommands = [] } = useQuery({
    queryKey: ['command-center', 'execute-commands', executeChatKey],
    queryFn: () => commandsApi.listCommands(executeChatKey),
    enabled: Boolean(executeChatKey),
  })

  const executableCommandNames = useMemo(() => {
    return new Set(executableCommands.filter(cmd => cmd.enabled).map(cmd => cmd.name))
  }, [executableCommands])

  const { categories, sources, permissions } = useMemo(() => {
    const categorySet = new Map<string, string>()
    const sourceSet = new Set<string>()
    const permissionSet = new Set<string>()

    commands.forEach(cmd => {
      categorySet.set(cmd.category, getCommandCategory(cmd, i18n.language))
      sourceSet.add(cmd.source)
      permissionSet.add(cmd.permission)
    })

    return {
      categories: Array.from(categorySet.entries()).sort((a, b) => a[1].localeCompare(b[1])),
      sources: Array.from(sourceSet).sort(),
      permissions: Array.from(permissionSet).sort(),
    }
  }, [commands, i18n.language])

  const filteredCommands = useMemo(() => {
    const keyword = deferredSearchInput.trim().toLowerCase()

    return commands.filter(cmd => {
      const description = getCommandDescription(cmd, i18n.language)
      const matchSearch =
        !keyword ||
        cmd.name.toLowerCase().includes(keyword) ||
        description.toLowerCase().includes(keyword) ||
        cmd.aliases.some(alias => alias.toLowerCase().includes(keyword))
      const matchCategory = !categoryFilter || cmd.category === categoryFilter
      const matchSource = !sourceFilter || cmd.source === sourceFilter
      const matchPermission = !permissionFilter || cmd.permission === permissionFilter
      return matchSearch && matchCategory && matchSource && matchPermission
    })
  }, [categoryFilter, commands, deferredSearchInput, i18n.language, permissionFilter, sourceFilter])

  useEffect(() => {
    if (filteredCommands.length === 0) {
      if (selectedCommandName) {
        updateParams({ command: null })
      }
      return
    }

    const exists = filteredCommands.some(cmd => cmd.name === selectedCommandName)
    if (!exists) {
      updateParams({ command: filteredCommands[0].name })
    }
  }, [filteredCommands, selectedCommandName, updateParams])

  const selectedCommand = useMemo(
    () => filteredCommands.find(cmd => cmd.name === selectedCommandName) ?? null,
    [filteredCommands, selectedCommandName],
  )

  useEffect(() => {
    setCommandLine(selectedCommandName || '')
  }, [selectedCommandName])

  useEffect(() => {
    if (focus !== 'execute' || !executePanelRef.current) {
      return
    }
    executePanelRef.current.scrollIntoView({ behavior: 'smooth', block: 'start' })
  }, [focus])

  const toggleMutation = useMutation({
    mutationFn: ({ name, enabled }: { name: string; enabled: boolean }) =>
      commandsApi.setCommandState(name, enabled, managementQueryChatKey),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['command-center', 'commands'] })
      queryClient.invalidateQueries({ queryKey: ['command-center', 'execute-commands'] })
      notification.success(t('commands.messages.toggleSuccess', '已更新命令状态'))
    },
    onError: () => {
      notification.error(t('commands.messages.toggleFailed', '更新失败'))
    },
  })

  const resetMutation = useMutation({
    mutationFn: (name: string) => commandsApi.resetCommandState(name, managementQueryChatKey),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['command-center', 'commands'] })
      queryClient.invalidateQueries({ queryKey: ['command-center', 'execute-commands'] })
      notification.success(t('commands.messages.resetSuccess', '已重置命令状态'))
    },
    onError: () => {
      notification.error(t('commands.messages.resetFailed', '重置失败'))
    },
  })

  const executeMutation = useMutation({
    mutationFn: ({ commandName, rawArgs }: { commandName: string; rawArgs: string }) =>
      commandsApi.webuiExecute(commandName, executeChatKey, rawArgs),
    onSuccess: () => {
      notification.info(t('commands.messages.executeSent', '命令已发送，等待输出'))
    },
    onError: () => {
      notification.error(t('commands.messages.executeFailed', '命令执行失败'))
    },
  })

  const parsedExecution = useMemo(() => {
    const trimmed = commandLine.trim()
    if (!trimmed || !executeChatKey) {
      return null
    }

    const spaceIndex = trimmed.indexOf(' ')
    const commandName = spaceIndex === -1 ? trimmed : trimmed.slice(0, spaceIndex)
    const rawArgs = spaceIndex === -1 ? '' : trimmed.slice(spaceIndex + 1).trim()

    if (!executableCommandNames.has(commandName)) {
      return null
    }

    return { commandName, rawArgs }
  }, [commandLine, executableCommandNames, executeChatKey])

  const categoryOptions = useMemo(
    () => [
      { value: '', label: t('commands.filters.all', '全部') },
      ...categories.map(([value, label]) => ({ value, label })),
    ],
    [categories, t],
  )

  const sourceOptions = useMemo(
    () => [
      { value: '', label: t('commands.filters.all', '全部') },
      ...sources.map(source => ({
        value: source,
        label: getSourceLabel(source, t),
      })),
    ],
    [sources, t],
  )

  const permissionOptions = useMemo(
    () => [
      { value: '', label: t('commands.filters.all', '全部') },
      ...permissions.map(permission => ({
        value: permission,
        label: t(`commands.permissions.${permission}`, permission),
      })),
    ],
    [permissions, t],
  )

  const selectedExecuteChannel = channels.find(channel => channel.chat_key === executeChatKey) ?? null

  const handleExecute = () => {
    if (!parsedExecution) {
      return
    }
    executeMutation.mutate(parsedExecution)
  }

  return (
    <Box
      sx={{
        height: '100%',
        display: 'flex',
        flexDirection: 'column',
        overflow: 'hidden',
        p: 2,
        gap: 2,
      }}
    >
      <Box
        sx={{
          flex: 1,
          minHeight: 0,
          display: 'grid',
          gridTemplateColumns: isMobile ? '1fr' : 'minmax(320px, 420px) minmax(0, 1fr)',
          gap: 2,
        }}
      >
        <Card
          sx={{
            ...CARD_VARIANTS.default.styles,
            minHeight: 0,
            display: 'flex',
          flexDirection: 'column',
        }}
      >
          <Box sx={{ px: 2, pt: 2, pb: 1.5 }}>
            <Stack
              direction={{ xs: 'column', md: 'row' }}
              spacing={1.5}
              alignItems={{ xs: 'stretch', md: 'center' }}
              justifyContent="space-between"
            >
              <Stack spacing={0.5} sx={{ minWidth: 0, flex: 1 }}>
                <Stack direction="row" spacing={1} alignItems="center">
                  <Box
                    sx={{
                      width: 30,
                      height: 30,
                      borderRadius: 1.25,
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      color: 'primary.main',
                      backgroundColor: alpha(theme.palette.primary.main, 0.1),
                    }}
                  >
                    <TuneIcon sx={{ fontSize: 18 }} />
                  </Box>
                  <Typography variant="subtitle1" sx={{ fontWeight: 700 }}>
                    {t('commands.center.catalogTitle', '命令目录')}
                  </Typography>
                </Stack>
              </Stack>

              <Stack
                direction={{ xs: 'column', sm: 'row' }}
                spacing={1}
                alignItems={{ xs: 'stretch', sm: 'center' }}
              >
                <FormControl size="small" sx={{ minWidth: 170 }}>
                  <InputLabel>{t('commands.scope.label', '管理作用域')}</InputLabel>
                  <Select
                    value={scope}
                    label={t('commands.scope.label', '管理作用域')}
                    onChange={event => {
                      const nextScope = event.target.value as ManageScope
                      if (nextScope === 'system') {
                        updateParams({ scope: 'system', chat_key: null })
                        return
                      }
                      updateParams({
                        scope: 'channel',
                        chat_key: managementChatKey || channels[0]?.chat_key || null,
                      })
                    }}
                  >
                    <MenuItem value="system">{t('commands.scope.system', '系统默认')}</MenuItem>
                    <MenuItem value="channel">{t('commands.scope.channel', '指定频道')}</MenuItem>
                  </Select>
                </FormControl>

                {scope === 'channel' && (
                  <FormControl size="small" sx={{ minWidth: 240 }}>
                    <InputLabel>{t('commands.scope.channelSelector', '管理频道')}</InputLabel>
                    <Select
                      value={managementChatKey}
                      label={t('commands.scope.channelSelector', '管理频道')}
                      onChange={event => {
                        const nextChatKey = String(event.target.value)
                        updateParams({ chat_key: nextChatKey })
                        if (!executeChatKey) {
                          updateParams({ execute_chat_key: nextChatKey })
                        }
                      }}
                    >
                      {channelsLoading ? (
                        <MenuItem value="" disabled>
                          <CircularProgress size={16} sx={{ mr: 1 }} />
                          {t('commands.common.loadingChannels', '加载频道中...')}
                        </MenuItem>
                      ) : (
                        channels.map(channel => (
                          <MenuItem key={channel.chat_key} value={channel.chat_key}>
                            {channel.channel_name || channel.chat_key}
                          </MenuItem>
                        ))
                      )}
                    </Select>
                  </FormControl>
                )}
              </Stack>
            </Stack>
          </Box>
          <Box sx={{ px: 2, pb: 2 }}>
            <Stack spacing={1.25}>
              <SearchField
                size="small"
                value={searchInput}
                onChange={setSearchInput}
                onClear={() => setSearchInput('')}
                placeholder={t('commands.search', '搜索命令...')}
              />
              <Stack direction={{ xs: 'column', sm: 'row' }} spacing={1}>
                <FilterSelect
                  label={t('commands.filters.category', '分类')}
                  value={categoryFilter}
                  options={categoryOptions}
                  onChange={value => updateParams({ category: value || null })}
                />
                <FilterSelect
                  label={t('commands.filters.source', '来源')}
                  value={sourceFilter}
                  options={sourceOptions}
                  onChange={value => updateParams({ source: value || null })}
                />
              </Stack>
              <FilterSelect
                label={t('commands.filters.permission', '权限')}
                value={permissionFilter}
                options={permissionOptions}
                onChange={value => updateParams({ permission: value || null })}
              />
              <Typography variant="caption" color="text.secondary">
                {t('commands.total', '共 {{count}} 个命令', { count: filteredCommands.length })}
              </Typography>
            </Stack>
          </Box>
          <Divider />
          <Box sx={{ flex: 1, minHeight: 0, overflow: 'auto', px: 1.25, py: 1.25 }}>
            {commandsLoading ? (
              <Stack alignItems="center" justifyContent="center" sx={{ py: 6 }}>
                <CircularProgress size={28} />
                <Typography variant="body2" color="text.secondary" sx={{ mt: 1.5 }}>
                  {t('commands.loading', '加载中...')}
                </Typography>
              </Stack>
            ) : filteredCommands.length === 0 ? (
              <Stack alignItems="center" justifyContent="center" sx={{ py: 6 }}>
                <Typography variant="body2" color="text.secondary">
                  {t('commands.empty', '暂无命令')}
                </Typography>
              </Stack>
            ) : (
              <Stack spacing={1}>
                {filteredCommands.map(cmd => (
                  <CommandListItem
                    key={cmd.name}
                    cmd={cmd}
                    lang={i18n.language}
                    selected={cmd.name === selectedCommandName}
                    scope={scope}
                    onClick={() => updateParams({ command: cmd.name })}
                    t={t}
                  />
                ))}
              </Stack>
            )}
          </Box>
        </Card>

        <Box sx={{ minHeight: 0, display: 'flex', flexDirection: 'column', gap: 2 }}>
          <Card
            sx={{
              ...CARD_VARIANTS.default.styles,
              p: 2,
              display: 'flex',
              flexDirection: 'column',
              gap: 2,
            }}
          >
            <Stack
              direction={{ xs: 'column', md: 'row' }}
              spacing={1}
              alignItems={{ xs: 'flex-start', md: 'center' }}
              justifyContent="space-between"
            >
              <Box>
                <Typography variant="subtitle1" sx={{ fontWeight: 700 }}>
                  {t('commands.center.detailTitle', '命令详情')}
                </Typography>
              </Box>
              {selectedCommand && (
                <Chip
                  size="small"
                  color={getEffectiveStateColor(selectedCommand, scope)}
                  label={getEffectiveStateLabel(selectedCommand, scope, t)}
                />
              )}
            </Stack>

            {selectedCommand ? (
              <>
                <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
                  <Chip label={selectedCommand.name} color="primary" variant="outlined" />
                  <Chip
                    label={getSourceLabel(selectedCommand.source, t)}
                    variant="outlined"
                    size="small"
                  />
                  <Chip
                    label={t(`commands.permissions.${selectedCommand.permission}`, selectedCommand.permission)}
                    color={PERMISSION_COLORS[selectedCommand.permission] || 'default'}
                    variant="outlined"
                    size="small"
                  />
                  <Chip
                    label={getCommandCategory(selectedCommand, i18n.language)}
                    variant="outlined"
                    size="small"
                  />
                  {scope === 'channel' && selectedCommand.has_channel_override && (
                    <Chip
                      label={t('commands.state.channelOverride', '频道覆盖')}
                      color="warning"
                      size="small"
                    />
                  )}
                </Stack>

                <Box>
                  <Typography variant="body1" sx={{ fontWeight: 600 }}>
                    {getCommandDescription(selectedCommand, i18n.language)}
                  </Typography>
                </Box>

                <Stack spacing={1.5}>
                  <DetailRow
                    label={t('commands.detail.usage', '用法')}
                    value={getCommandUsage(selectedCommand, i18n.language) || '-'}
                    monospace
                  />
                  <DetailRow
                    label={t('commands.detail.aliases', '别名')}
                    value={selectedCommand.aliases.length > 0 ? selectedCommand.aliases.join(', ') : '-'}
                    monospace
                  />
                  <DetailRow
                    label={t('commands.detail.params', '参数')}
                    value={
                      selectedCommand.params_schema
                        ? JSON.stringify(selectedCommand.params_schema, null, 2)
                        : t('commands.detail.noParams', '此命令没有额外参数说明')
                    }
                    monospace
                    multiline
                  />
                </Stack>

                <Stack direction={{ xs: 'column', sm: 'row' }} spacing={1.25}>
                  <ActionButton
                    tone={selectedCommand.enabled ? 'secondary' : 'primary'}
                    onClick={() =>
                      toggleMutation.mutate({
                        name: selectedCommand.name,
                        enabled: !selectedCommand.enabled,
                      })
                    }
                    disabled={toggleMutation.isPending}
                  >
                    {selectedCommand.enabled
                      ? t('commands.actions.disable', '禁用命令')
                      : t('commands.actions.enable', '启用命令')}
                  </ActionButton>
                  {scope === 'channel' && (
                    <ActionButton
                      tone="ghost"
                      onClick={() => resetMutation.mutate(selectedCommand.name)}
                      disabled={!selectedCommand.has_channel_override || resetMutation.isPending}
                    >
                      {t('commands.actions.reset', '重置为默认')}
                    </ActionButton>
                  )}
                </Stack>
              </>
            ) : (
              <Alert severity="info" variant="outlined">
                {t('commands.center.selectHint', '从左侧选择一条命令后，这里会显示相关信息。')}
              </Alert>
            )}
          </Card>

          <Card
            ref={executePanelRef}
            sx={{
              ...CARD_VARIANTS.default.styles,
              flex: 1,
              minHeight: 0,
              display: 'flex',
              flexDirection: 'column',
            }}
          >
            <Box sx={{ p: 2 }}>
              <Stack spacing={1.5}>
                <Stack
                  direction={{ xs: 'column', md: 'row' }}
                  spacing={1}
                  alignItems={{ xs: 'stretch', md: 'center' }}
                  justifyContent="space-between"
                >
                  <Box>
                    <Typography variant="subtitle1" sx={{ fontWeight: 700 }}>
                      {t('commands.center.executeTitle', '执行')}
                    </Typography>
                  </Box>
                  {selectedExecuteChannel && (
                    <Chip
                      icon={<TerminalIcon />}
                      variant="outlined"
                      label={selectedExecuteChannel.channel_name || selectedExecuteChannel.chat_key}
                    />
                  )}
                </Stack>

                <Stack direction={{ xs: 'column', lg: 'row' }} spacing={1.25}>
                  <FormControl size="small" sx={{ minWidth: { xs: '100%', lg: 280 } }}>
                    <InputLabel>{t('commands.execute.channel', '执行频道')}</InputLabel>
                    <Select
                      value={executeChatKey}
                      label={t('commands.execute.channel', '执行频道')}
                      onChange={event => updateParams({ execute_chat_key: String(event.target.value) })}
                    >
                      {channelsLoading ? (
                        <MenuItem value="" disabled>
                          <CircularProgress size={16} sx={{ mr: 1 }} />
                          {t('commands.common.loadingChannels', '加载频道中...')}
                        </MenuItem>
                      ) : (
                        channels.map(channel => (
                          <MenuItem key={channel.chat_key} value={channel.chat_key}>
                            {channel.channel_name || channel.chat_key}
                          </MenuItem>
                        ))
                      )}
                    </Select>
                  </FormControl>

                  <TextField
                    fullWidth
                    size="small"
                    value={commandLine}
                    placeholder={t('commands.execute.placeholder', '输入命令，如 help 或 help 参数')}
                    onChange={event => setCommandLine(event.target.value)}
                    onKeyDown={event => {
                      if (event.key === 'Enter' && !event.shiftKey) {
                        event.preventDefault()
                        handleExecute()
                      }
                    }}
                    slotProps={{
                      input: {
                        endAdornment: (
                          <InputAdornment position="end">
                            <ActionButton
                              tone="primary"
                              onClick={handleExecute}
                              disabled={!parsedExecution || executeMutation.isPending}
                              startIcon={
                                executeMutation.isPending ? (
                                  <CircularProgress size={14} color="inherit" />
                                ) : (
                                  <SendIcon fontSize="small" />
                                )
                              }
                            >
                              {t('commands.execute.run', '执行')}
                            </ActionButton>
                          </InputAdornment>
                        ),
                      },
                    }}
                  />
                </Stack>

                {!executeChatKey ? (
                  <Alert severity="info" variant="outlined">
                    {t('commands.execute.selectChannelHint', '请先选择执行频道，再发送命令。')}
                  </Alert>
                ) : parsedExecution ? null : (
                  <Alert severity="warning" variant="outlined">
                    {t(
                      'commands.execute.invalidCommand',
                      '当前输入的命令未在所选频道启用，或命令名不存在。',
                    )}
                  </Alert>
                )}
              </Stack>
            </Box>

            <Divider />

            <Box sx={{ flex: 1, minHeight: 260, overflow: 'hidden' }}>
              {executeChatKey ? (
                <CommandOutputLog chatKey={executeChatKey} />
              ) : (
                <Stack alignItems="center" justifyContent="center" sx={{ height: '100%', px: 3 }}>
                  <Typography variant="body2" color="text.secondary" align="center">
                    {t('commands.execute.logHint', '选择频道后，这里会显示该频道的实时命令输出。')}
                  </Typography>
                </Stack>
              )}
            </Box>
          </Card>
        </Box>
      </Box>
    </Box>
  )
}

function CommandListItem({
  cmd,
  lang,
  selected,
  scope,
  onClick,
  t,
}: {
  cmd: CommandState
  lang: string
  selected: boolean
  scope: ManageScope
  onClick: () => void
  t: TFunction<'settings'>
}) {
  const theme = useTheme()

  return (
    <Box
      role="button"
      tabIndex={0}
      onClick={onClick}
      onKeyDown={event => {
        if (event.key === 'Enter' || event.key === ' ') {
          event.preventDefault()
          onClick()
        }
      }}
      sx={{
        borderRadius: 2,
        border: '1px solid',
        borderColor: selected ? 'primary.main' : 'divider',
        backgroundColor: selected ? alpha(theme.palette.primary.main, 0.08) : 'transparent',
        px: 1.25,
        py: 1.1,
        cursor: 'pointer',
        transition: 'all 0.2s ease',
        '&:hover': {
          borderColor: selected ? 'primary.main' : 'text.secondary',
          backgroundColor: selected ? alpha(theme.palette.primary.main, 0.12) : 'action.hover',
        },
      }}
    >
      <Stack spacing={1}>
        <Stack direction="row" spacing={1} alignItems="center" justifyContent="space-between">
          <Typography variant="body2" sx={{ fontWeight: 700, fontFamily: 'monospace' }}>
            {cmd.name}
          </Typography>
          <ArrowOutwardIcon
            fontSize="inherit"
            sx={{ color: selected ? 'primary.main' : 'text.disabled', fontSize: 16 }}
          />
        </Stack>
        <Typography variant="body2" color="text.secondary">
          {getCommandDescription(cmd, lang)}
        </Typography>
        <Stack direction="row" spacing={0.75} flexWrap="wrap" useFlexGap>
          <Chip
            size="small"
            variant="outlined"
            label={getEffectiveStateLabel(cmd, scope, t)}
            color={getEffectiveStateColor(cmd, scope)}
          />
          <Chip
            size="small"
            variant="outlined"
            label={getCommandCategory(cmd, lang)}
          />
          <Chip
            size="small"
            variant="outlined"
            label={getSourceLabel(cmd.source, t)}
          />
        </Stack>
      </Stack>
    </Box>
  )
}

function DetailRow({
  label,
  value,
  monospace = false,
  multiline = false,
}: {
  label: string
  value: string
  monospace?: boolean
  multiline?: boolean
}) {
  return (
    <Box>
      <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mb: 0.5 }}>
        {label}
      </Typography>
      <Typography
        variant="body2"
        sx={{
          fontFamily: monospace ? 'monospace' : 'inherit',
          whiteSpace: multiline ? 'pre-wrap' : 'normal',
          wordBreak: 'break-word',
        }}
      >
        {value}
      </Typography>
    </Box>
  )
}
