import { type ReactNode, useCallback, useDeferredValue, useEffect, useMemo, useRef, useState } from 'react'
import {
  Autocomplete,
  Alert,
  Box,
  Card,
  Chip,
  CircularProgress,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  Divider,
  Stack,
  TextField,
  Tooltip,
  Typography,
  useMediaQuery,
  useTheme,
} from '@mui/material'
import {
  ArrowOutward as ArrowOutwardIcon,
  Send as SendIcon,
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
import type { ChannelDirectoryEntry } from '../../hooks/useChannelDirectory'

type ManageScope = 'system' | 'channel'
type ManageTargetOption =
  | { type: 'system'; value: 'system'; label: string }
  | { type: 'channel'; value: string; channel: ChannelDirectoryEntry }
type ParamSchemaItem = {
  name: string
  typeLabel: string
  description: string | null
  required: boolean
  defaultValue: string | null
  enumValues: string[]
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
  command: Pick<CommandState, 'source' | 'source_display_name'>,
  t: TFunction<'settings'>,
) {
  return command.source === 'built_in'
    ? t('commands.sources.builtIn', '内置')
    : t('commands.sources.pluginWithName', '插件 · {{name}}', {
        name: command.source_display_name || command.source,
      })
}

function getSourceDetailLabel(
  command: Pick<CommandState, 'source' | 'source_display_name'>,
  t: TFunction<'settings'>,
) {
  if (command.source === 'built_in') {
    return t('commands.sources.builtIn', '内置')
  }

  if (!command.source_display_name || command.source_display_name === command.source) {
    return command.source
  }

  return t('commands.sources.pluginWithNameAndKey', '插件 · {{name}} ({{key}})', {
    name: command.source_display_name,
    key: command.source,
  })
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

function getEffectiveStateDescription(
  cmd: CommandState,
  scope: ManageScope,
  t: TFunction<'settings'>,
) {
  if (scope === 'system') {
    return cmd.enabled
      ? t('commands.stateDescription.systemEnabled', '该命令当前在系统范围内可用。')
      : t('commands.stateDescription.systemDisabled', '该命令当前在系统范围内已停用。')
  }

  if (cmd.has_channel_override) {
    return cmd.enabled
      ? t(
          'commands.stateDescription.channelEnabled',
          '该频道已单独启用此命令，不受系统默认状态影响。',
        )
      : t(
          'commands.stateDescription.channelDisabled',
          '该频道已单独停用此命令，不受系统默认状态影响。',
        )
  }

  return cmd.enabled
    ? t(
        'commands.stateDescription.inheritedEnabled',
        '该频道没有单独设置，当前沿用系统默认启用状态。',
      )
    : t(
        'commands.stateDescription.inheritedDisabled',
        '该频道没有单独设置，当前沿用系统默认停用状态。',
      )
}

function getPermissionOverrideDescription(
  cmd: CommandState,
  scope: ManageScope,
  t: TFunction<'settings'>,
) {
  if (scope === 'system') {
    return cmd.has_permission_override
      ? t(
          'commands.permissionEditor.systemOverrideHint',
          '当前系统权限已覆盖命令注册时的默认权限。',
        )
      : t(
          'commands.permissionEditor.systemDefaultHint',
          '当前系统权限沿用命令注册时的默认权限。',
        )
  }

  return cmd.has_permission_override
    ? t(
        'commands.permissionEditor.channelOverrideHint',
        '当前频道已单独覆盖权限，不受系统权限影响。',
      )
    : t(
        'commands.permissionEditor.channelInheritedHint',
        '当前频道未单独设置权限，沿用系统生效权限。',
      )
}

function isManageScope(value: string | null): value is ManageScope {
  return value === 'system' || value === 'channel'
}

function getManageTargetValue(scope: ManageScope, chatKey: string) {
  return scope === 'system' ? 'system' : chatKey ? `channel:${chatKey}` : 'system'
}

function renderChannelIdentity(channelName: string | null | undefined, chatKey: string) {
  return (
    <Stack direction="row" spacing={1} alignItems="center" sx={{ minWidth: 0, width: '100%' }}>
      <Typography
        variant="body2"
        noWrap
        sx={{
          minWidth: 0,
          flex: 1,
          overflow: 'hidden',
          textOverflow: 'ellipsis',
        }}
      >
        {channelName || chatKey}
      </Typography>
      <Typography
        variant="caption"
        color="text.secondary"
        noWrap
        sx={{ fontFamily: 'monospace', flexShrink: 0 }}
      >
        {chatKey}
      </Typography>
    </Stack>
  )
}

function normalizeSchemaType(property: Record<string, unknown>): string {
  const directType = property.type
  if (typeof directType === 'string' && directType) {
    return directType
  }

  const anyOf = Array.isArray(property.anyOf) ? property.anyOf : []
  const oneOf = Array.isArray(property.oneOf) ? property.oneOf : []
  const variants = [...anyOf, ...oneOf]
    .map(item => (typeof item === 'object' && item !== null ? item.type : null))
    .filter((value): value is string => typeof value === 'string' && value.length > 0)

  return variants.length > 0 ? variants.join(' | ') : 'unknown'
}

function normalizeParamSchema(schema?: Record<string, unknown>): ParamSchemaItem[] {
  if (!schema || schema.type !== 'object') {
    return []
  }

  const properties =
    schema.properties && typeof schema.properties === 'object' && !Array.isArray(schema.properties)
      ? schema.properties
      : null
  if (!properties) {
    return []
  }

  const required = new Set(
    Array.isArray(schema.required) ? schema.required.filter((item): item is string => typeof item === 'string') : [],
  )

  return Object.entries(properties)
    .filter((entry): entry is [string, Record<string, unknown>] => {
      const value = entry[1]
      return typeof value === 'object' && value !== null
    })
    .map(([name, value]) => ({
      name,
      typeLabel: normalizeSchemaType(value),
      description: typeof value.description === 'string' ? value.description : null,
      required: required.has(name),
      defaultValue:
        value.default === undefined ? null : typeof value.default === 'string' ? value.default : JSON.stringify(value.default),
      enumValues: Array.isArray(value.enum)
        ? value.enum.map((item: unknown) => (typeof item === 'string' ? item : JSON.stringify(item)))
        : [],
    }))
}

export default function CommandCenterPage() {
  const theme = useTheme()
  const isMobile = useMediaQuery(theme.breakpoints.down('lg'))
  const isPhone = useMediaQuery(theme.breakpoints.down('sm'))
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
  const [detailDialogOpen, setDetailDialogOpen] = useState(false)
  const executePanelRef = useRef<HTMLDivElement | null>(null)
  const invalidateCommandQueries = useCallback(() => {
    queryClient.invalidateQueries({ queryKey: ['command-center', 'commands'] })
    queryClient.invalidateQueries({ queryKey: ['command-center', 'execute-commands'] })
  }, [queryClient])

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
      permissionSet.add(cmd.default_permission)
    })

    return {
      categories: Array.from(categorySet.entries()).sort((a, b) => a[1].localeCompare(b[1])),
      sources: Array.from(sourceSet).sort(),
      permissions: Array.from(permissionSet).sort((a, b) =>
        t(`commands.permissions.${a}`, a).localeCompare(t(`commands.permissions.${b}`, b), i18n.language),
      ),
    }
  }, [commands, i18n.language, t])

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
    if (!isPhone) {
      setDetailDialogOpen(false)
    }
  }, [isPhone])

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
      invalidateCommandQueries()
      notification.success(t('commands.messages.toggleSuccess', '已更新命令状态'))
    },
    onError: () => {
      notification.error(t('commands.messages.toggleFailed', '更新失败'))
    },
  })

  const resetMutation = useMutation({
    mutationFn: (name: string) => commandsApi.resetCommandState(name, managementQueryChatKey),
    onSuccess: () => {
      invalidateCommandQueries()
      notification.success(t('commands.messages.resetSuccess', '已重置命令状态'))
    },
    onError: () => {
      notification.error(t('commands.messages.resetFailed', '重置失败'))
    },
  })

  const setPermissionMutation = useMutation({
    mutationFn: ({ name, permission }: { name: string; permission: string }) =>
      commandsApi.setCommandPermission(name, permission, managementQueryChatKey),
    onSuccess: () => {
      invalidateCommandQueries()
      notification.success(t('commands.messages.permissionUpdateSuccess', '已更新命令权限'))
    },
    onError: () => {
      notification.error(t('commands.messages.permissionUpdateFailed', '权限更新失败'))
    },
  })

  const resetPermissionMutation = useMutation({
    mutationFn: (name: string) => commandsApi.resetCommandPermission(name, managementQueryChatKey),
    onSuccess: () => {
      invalidateCommandQueries()
      notification.success(t('commands.messages.permissionResetSuccess', '已重置命令权限'))
    },
    onError: () => {
      notification.error(t('commands.messages.permissionResetFailed', '权限重置失败'))
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
        label:
          source === 'built_in'
            ? t('commands.sources.builtIn', '内置')
            : (() => {
                const matched = commands.find(cmd => cmd.source === source)
                return matched ? getSourceDetailLabel(matched, t) : source
              })(),
      })),
    ],
    [commands, sources, t],
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
  const permissionEditorOptions = useMemo(
    () => permissions.map(permission => ({
      value: permission,
      label: t(`commands.permissions.${permission}`, permission),
    })),
    [permissions, t],
  )

  const manageTargetValue = getManageTargetValue(scope, managementChatKey)
  const manageTargetOptions = useMemo<ManageTargetOption[]>(
    () => [
      { type: 'system', value: 'system', label: t('commands.scope.system', '系统默认') },
      ...channels.map(channel => ({
        type: 'channel' as const,
        value: `channel:${channel.chat_key}`,
        channel,
      })),
    ],
    [channels, t],
  )
  const selectedManageTarget = useMemo(
    () => manageTargetOptions.find(option => option.value === manageTargetValue) ?? manageTargetOptions[0] ?? null,
    [manageTargetOptions, manageTargetValue],
  )
  const selectedExecuteChannel = useMemo(
    () => channels.find(channel => channel.chat_key === executeChatKey) ?? null,
    [channels, executeChatKey],
  )
  const selectedCommandParams = useMemo(
    () => normalizeParamSchema(selectedCommand?.params_schema),
    [selectedCommand?.params_schema],
  )

  const handleExecute = () => {
    if (!parsedExecution) {
      return
    }
    executeMutation.mutate(parsedExecution)
  }

  const handleCommandSelect = (commandName: string) => {
    updateParams({ command: commandName })
  }

  const handleCommandDetailOpen = (commandName: string) => {
    updateParams({ command: commandName })
    if (isPhone) {
      setDetailDialogOpen(true)
    }
  }

  return (
    <Box
      sx={{
        height: '100%',
        display: 'flex',
        flexDirection: 'column',
        overflow: { xs: 'auto', lg: 'hidden' },
        p: { xs: 1.5, md: 2 },
        gap: { xs: 1.5, md: 2 },
        minWidth: 0,
      }}
    >
      <Box
        sx={{
          flex: { xs: '0 0 auto', lg: 1 },
          minHeight: { xs: 'auto', lg: 0 },
          display: 'grid',
          gridTemplateColumns: isMobile ? '1fr' : 'minmax(320px, 420px) minmax(0, 1fr)',
          gap: { xs: 1.5, md: 2 },
          minWidth: 0,
        }}
      >
        <Card
          sx={{
            ...CARD_VARIANTS.default.styles,
            minHeight: { xs: 'auto', lg: 0 },
            maxHeight: { xs: '72vh', lg: 'none' },
            display: 'flex',
            flexDirection: 'column',
            minWidth: 0,
          }}
        >
          <Box sx={{ px: { xs: 1.5, md: 2 }, pt: { xs: 1.5, md: 2 }, pb: 1.5 }}>
            <Stack spacing={1.5}>
              <Stack
                direction={{ xs: 'column', sm: 'row' }}
                spacing={1}
                alignItems={{ xs: 'stretch', sm: 'center' }}
                justifyContent="space-between"
                sx={{ minWidth: 0 }}
              >
                <Stack direction="row" spacing={1} alignItems="center" sx={{ minWidth: 0 }}>
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
                      flexShrink: 0,
                    }}
                  >
                    <TuneIcon sx={{ fontSize: 18 }} />
                  </Box>
                  <Typography variant="subtitle1" sx={{ fontWeight: 700 }}>
                    {t('commands.center.catalogTitle', '命令目录')}
                  </Typography>
                </Stack>
                <Typography
                  variant="caption"
                  color="text.secondary"
                  sx={{ flexShrink: 0, textAlign: { xs: 'left', sm: 'right' } }}
                >
                  {t('commands.total', '共 {{count}} 个命令', { count: filteredCommands.length })}
                </Typography>
              </Stack>

              <Autocomplete
                fullWidth
                size="small"
                options={manageTargetOptions}
                value={selectedManageTarget}
                loading={channelsLoading}
                onChange={(_, option) => {
                  if (!option || option.type === 'system') {
                    updateParams({ scope: 'system', chat_key: null })
                    return
                  }
                  const nextChatKey = option.channel.chat_key
                  updateParams({
                    scope: 'channel',
                    chat_key: nextChatKey,
                    execute_chat_key: executeChatKey || nextChatKey,
                  })
                }}
                isOptionEqualToValue={(option, value) => option.value === value.value}
                getOptionLabel={option =>
                  option.type === 'system'
                    ? option.label
                    : `${option.channel.channel_name || option.channel.chat_key} ${option.channel.chat_key}`
                }
                filterOptions={(options, state) => {
                  const keyword = state.inputValue.trim().toLowerCase()
                  if (!keyword) return options
                  return options.filter(option => {
                    if (option.type === 'system') {
                      return option.label.toLowerCase().includes(keyword)
                    }
                    return (
                      (option.channel.channel_name || '').toLowerCase().includes(keyword) ||
                      option.channel.chat_key.toLowerCase().includes(keyword)
                    )
                  })
                }}
                renderOption={(props, option) => (
                  <Box component="li" {...props}>
                    {option.type === 'system'
                      ? (
                        <Typography variant="body2">{option.label}</Typography>
                      )
                      : renderChannelIdentity(option.channel.channel_name, option.channel.chat_key)}
                  </Box>
                )}
                renderInput={params => (
                  <TextField
                    {...params}
                    label={t('commands.scope.label', '管理范围')}
                    placeholder={t('commands.scope.searchPlaceholder', '搜索频道')}
                  />
                )}
              />
            </Stack>
          </Box>
          <Box sx={{ px: { xs: 1.5, md: 2 }, pb: { xs: 1.5, md: 2 } }}>
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
            </Stack>
          </Box>
          <Divider />
          <Box sx={{ flex: 1, minHeight: 0, overflow: 'auto', px: { xs: 1, md: 1.25 }, py: { xs: 1, md: 1.25 } }}>
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
                    onClick={() => handleCommandSelect(cmd.name)}
                    onOpenDetail={() => handleCommandDetailOpen(cmd.name)}
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
              display: { xs: 'none', sm: 'flex' },
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
            </Stack>

            {selectedCommand ? (
              <>
                <Stack
                  direction={{ xs: 'column', md: 'row' }}
                  spacing={2}
                  alignItems={{ xs: 'flex-start', md: 'center' }}
                  justifyContent="space-between"
                >
                  <Box sx={{ minWidth: 0 }}>
                    <Typography
                      variant="h6"
                      sx={{ fontWeight: 700, fontFamily: 'monospace', mb: 0.75, wordBreak: 'break-word' }}
                    >
                      {selectedCommand.name}
                    </Typography>
                    <Typography variant="body1" sx={{ fontWeight: 600 }}>
                      {getCommandDescription(selectedCommand, i18n.language)}
                    </Typography>
                  </Box>

                  <Stack direction="row" spacing={1} useFlexGap flexWrap="wrap">
                    <Tooltip
                      arrow
                      placement="top"
                      title={getEffectiveStateDescription(selectedCommand, scope, t)}
                    >
                      <Chip
                        size="small"
                        color={getEffectiveStateColor(selectedCommand, scope)}
                        label={getEffectiveStateLabel(selectedCommand, scope, t)}
                      />
                    </Tooltip>
                    {scope === 'channel' && selectedCommand.has_channel_override && (
                      <Tooltip
                        arrow
                        placement="top"
                        title={t(
                          'commands.stateDescription.channelOverride',
                          '当前频道使用了单独设置，与系统默认状态不同。',
                        )}
                      >
                      <Chip
                        size="small"
                        variant="outlined"
                        color="warning"
                        label={t('commands.state.channelOverride', '频道覆盖')}
                      />
                      </Tooltip>
                    )}
                  </Stack>
                </Stack>

                <Box
                  sx={{
                    display: 'grid',
                    gridTemplateColumns: { xs: '1fr', xl: 'minmax(0, 1.4fr) minmax(280px, 0.8fr)' },
                    gap: 2.5,
                    alignItems: 'start',
                  }}
                >
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
                      value=""
                      content={
                        <CommandParamsView
                          items={selectedCommandParams}
                          emptyText={t('commands.detail.noParams', '此命令没有额外参数说明')}
                          t={t}
                        />
                      }
                    />
                  </Stack>

                  <Box
                    sx={{
                      display: 'grid',
                      gridTemplateColumns: { xs: '1fr', sm: 'repeat(2, minmax(0, 1fr))', xl: '1fr' },
                      gap: 1.5,
                      pt: { xl: 0.25 },
                    }}
                  >
                    <DetailRow
                      label={t('commands.detail.category', '分类')}
                      value={getCommandCategory(selectedCommand, i18n.language)}
                    />
                    <DetailRow
                      label={t('commands.detail.source', '来源')}
                      value={getSourceDetailLabel(selectedCommand, t)}
                    />
                    <DetailRow
                      label={t('commands.detail.permission', '生效权限')}
                      value=""
                      content={
                        <Stack spacing={0.75}>
                          <Stack
                            direction={{ xs: 'column', sm: 'row' }}
                            spacing={1}
                            alignItems={{ xs: 'stretch', sm: 'center' }}
                          >
                            <Box sx={{ flex: 1, minWidth: { xs: '100%', sm: 220 } }}>
                              <FilterSelect
                                label=""
                                value={selectedCommand.permission}
                                options={permissionEditorOptions}
                                onChange={value => {
                                  if (
                                    !selectedCommand ||
                                    !value ||
                                    value === selectedCommand.permission
                                  ) {
                                    return
                                  }
                                  setPermissionMutation.mutate({
                                    name: selectedCommand.name,
                                    permission: value,
                                  })
                                }}
                                disabled={setPermissionMutation.isPending || resetPermissionMutation.isPending}
                              />
                            </Box>
                            <ActionButton
                              tone="secondary"
                              onClick={() => resetPermissionMutation.mutate(selectedCommand.name)}
                              disabled={!selectedCommand.has_permission_override || resetPermissionMutation.isPending}
                            >
                              {scope === 'system'
                                ? t('commands.actions.resetPermissionDefault', '恢复默认权限')
                                : t('commands.actions.resetPermissionInherited', '恢复继承权限')}
                            </ActionButton>
                          </Stack>
                          <Typography variant="caption" color="text.secondary">
                            {getPermissionOverrideDescription(selectedCommand, scope, t)}
                          </Typography>
                        </Stack>
                      }
                    />
                  </Box>
                </Box>

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
              <Stack spacing={2}>
                <Typography variant="subtitle1" sx={{ fontWeight: 700 }}>
                  {t('commands.center.executeTitle', '执行')}
                </Typography>

                <Box
                  sx={{
                    border: '1px solid',
                    borderColor: 'divider',
                    borderRadius: 2,
                    px: 1.5,
                    py: 1.5,
                    backgroundColor: alpha(theme.palette.background.paper, 0.12),
                  }}
                >
                  <Stack spacing={1.25}>
                    <Typography variant="caption" color="text.secondary">
                      {t('commands.execute.panelHint', '选择目标频道并输入命令，结果会显示在下方输出区。')}
                    </Typography>

                    <Box
                      sx={{
                        display: 'grid',
                        gridTemplateColumns: { xs: '1fr', xl: '320px minmax(0, 1fr) 112px' },
                        gap: 1.25,
                        alignItems: 'stretch',
                      }}
                    >
                      <Autocomplete
                        fullWidth
                        size="small"
                        options={channels}
                        value={selectedExecuteChannel}
                        loading={channelsLoading}
                        onChange={(_, option) =>
                          updateParams({ execute_chat_key: option?.chat_key || null })
                        }
                        isOptionEqualToValue={(option, value) => option.chat_key === value.chat_key}
                        getOptionLabel={option => `${option.channel_name || option.chat_key} ${option.chat_key}`}
                        filterOptions={(options, state) => {
                          const keyword = state.inputValue.trim().toLowerCase()
                          if (!keyword) return options
                          return options.filter(option =>
                            (option.channel_name || '').toLowerCase().includes(keyword) ||
                            option.chat_key.toLowerCase().includes(keyword)
                          )
                        }}
                        renderOption={(props, option) => (
                          <Box component="li" {...props}>
                            {renderChannelIdentity(option.channel_name, option.chat_key)}
                          </Box>
                        )}
                        renderInput={params => (
                          <TextField
                            {...params}
                            label={t('commands.execute.channel', '执行目标频道')}
                            placeholder={t('commands.execute.searchPlaceholder', '搜索频道')}
                          />
                        )}
                      />

                      <TextField
                        fullWidth
                        size="small"
                        label={t('commands.execute.command', '执行命令')}
                        value={commandLine}
                        placeholder={t('commands.execute.placeholder', '输入命令，如 help 或 help 参数')}
                        onChange={event => setCommandLine(event.target.value)}
                        onKeyDown={event => {
                          if (event.key === 'Enter' && !event.shiftKey) {
                            event.preventDefault()
                            handleExecute()
                          }
                        }}
                      />
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
                        sx={{ minWidth: 0, height: '100%' }}
                      >
                        {t('commands.execute.run', '执行')}
                      </ActionButton>
                    </Box>

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
              </Stack>
            </Box>

            <Box
              sx={{
                flex: 1,
                minHeight: 260,
                overflow: 'hidden',
                mx: 2,
                mb: 2,
                border: '1px solid',
                borderColor: 'divider',
                borderRadius: 2,
                backgroundColor: alpha(theme.palette.background.paper, 0.08),
              }}
            >
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

      <Dialog
        open={isPhone && detailDialogOpen && Boolean(selectedCommand)}
        onClose={() => setDetailDialogOpen(false)}
        maxWidth="sm"
        fullWidth
        PaperProps={{
          sx: {
            m: 2,
            width: 'calc(100% - 32px)',
            maxHeight: 'calc(100% - 32px)',
            borderRadius: 2,
          },
        }}
      >
        <DialogTitle sx={{ px: 2, py: 1.5 }}>
          <Typography variant="subtitle1" sx={{ fontWeight: 700 }}>
            {t('commands.center.detailTitle', '命令详情')}
          </Typography>
        </DialogTitle>
        <DialogContent sx={{ px: 2, pb: 2 }}>
          {selectedCommand ? (
            <Stack spacing={2}>
              <Box sx={{ minWidth: 0 }}>
                <Typography
                  variant="h6"
                  sx={{ fontWeight: 700, fontFamily: 'monospace', mb: 0.75, wordBreak: 'break-word' }}
                >
                  {selectedCommand.name}
                </Typography>
                <Typography variant="body1" sx={{ fontWeight: 600, wordBreak: 'break-word' }}>
                  {getCommandDescription(selectedCommand, i18n.language)}
                </Typography>
              </Box>

              <Stack direction="row" spacing={1} useFlexGap flexWrap="wrap">
                <Chip
                  size="small"
                  color={getEffectiveStateColor(selectedCommand, scope)}
                  label={getEffectiveStateLabel(selectedCommand, scope, t)}
                />
                {scope === 'channel' && selectedCommand.has_channel_override && (
                  <Chip
                    size="small"
                    variant="outlined"
                    color="warning"
                    label={t('commands.state.channelOverride', '频道覆盖')}
                  />
                )}
              </Stack>

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
                label={t('commands.detail.category', '分类')}
                value={getCommandCategory(selectedCommand, i18n.language)}
              />
              <DetailRow
                label={t('commands.detail.source', '来源')}
                value={getSourceDetailLabel(selectedCommand, t)}
              />
              <DetailRow
                label={t('commands.detail.params', '参数')}
                value=""
                content={
                  <CommandParamsView
                    items={selectedCommandParams}
                    emptyText={t('commands.detail.noParams', '此命令没有额外参数说明')}
                    t={t}
                  />
                }
              />
              <DetailRow
                label={t('commands.detail.permission', '生效权限')}
                value=""
                content={
                  <Stack spacing={0.75}>
                    <FilterSelect
                      label=""
                      value={selectedCommand.permission}
                      options={permissionEditorOptions}
                      onChange={value => {
                        if (!value || value === selectedCommand.permission) {
                          return
                        }
                        setPermissionMutation.mutate({
                          name: selectedCommand.name,
                          permission: value,
                        })
                      }}
                      disabled={setPermissionMutation.isPending || resetPermissionMutation.isPending}
                    />
                    <ActionButton
                      tone="secondary"
                      onClick={() => resetPermissionMutation.mutate(selectedCommand.name)}
                      disabled={!selectedCommand.has_permission_override || resetPermissionMutation.isPending}
                      sx={{ width: '100%' }}
                    >
                      {scope === 'system'
                        ? t('commands.actions.resetPermissionDefault', '恢复默认权限')
                        : t('commands.actions.resetPermissionInherited', '恢复继承权限')}
                    </ActionButton>
                    <Typography variant="caption" color="text.secondary">
                      {getPermissionOverrideDescription(selectedCommand, scope, t)}
                    </Typography>
                  </Stack>
                }
              />

              <Stack spacing={1.25}>
                <ActionButton
                  tone={selectedCommand.enabled ? 'secondary' : 'primary'}
                  onClick={() =>
                    toggleMutation.mutate({
                      name: selectedCommand.name,
                      enabled: !selectedCommand.enabled,
                    })
                  }
                  disabled={toggleMutation.isPending}
                  sx={{ width: '100%' }}
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
                    sx={{ width: '100%' }}
                  >
                    {t('commands.actions.reset', '重置为默认')}
                  </ActionButton>
                )}
              </Stack>
            </Stack>
          ) : null}
        </DialogContent>
        <DialogActions sx={{ px: 2, pb: 2, pt: 0 }}>
          <ActionButton
            tone="secondary"
            onClick={() => setDetailDialogOpen(false)}
            sx={{ width: '100%' }}
          >
            {t('commands.actions.back', '返回')}
          </ActionButton>
        </DialogActions>
      </Dialog>
    </Box>
  )
}

function CommandListItem({
  cmd,
  lang,
  selected,
  scope,
  onClick,
  onOpenDetail,
  t,
}: {
  cmd: CommandState
  lang: string
  selected: boolean
  scope: ManageScope
  onClick: () => void
  onOpenDetail: () => void
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
          <Typography variant="body2" sx={{ fontWeight: 700, fontFamily: 'monospace', minWidth: 0, wordBreak: 'break-all' }}>
            {cmd.name}
          </Typography>
          <Tooltip title={t('commands.actions.viewDetail', '查看详情')}>
            <Box
              component="button"
              type="button"
              onClick={event => {
                event.stopPropagation()
                onOpenDetail()
              }}
              onKeyDown={event => {
                event.stopPropagation()
              }}
              sx={{
                width: 30,
                height: 30,
                p: 0,
                border: '1px solid',
                borderColor: selected ? 'primary.main' : 'divider',
                borderRadius: 1,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                color: selected ? 'primary.main' : 'text.secondary',
                backgroundColor: selected ? alpha(theme.palette.primary.main, 0.08) : 'background.paper',
                cursor: 'pointer',
                flexShrink: 0,
                transition: 'all 0.2s ease',
                '&:hover': {
                  borderColor: 'primary.main',
                  color: 'primary.main',
                  backgroundColor: alpha(theme.palette.primary.main, 0.12),
                },
              }}
            >
              <ArrowOutwardIcon fontSize="inherit" sx={{ fontSize: 16 }} />
            </Box>
          </Tooltip>
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
            label={getSourceLabel(cmd, t)}
          />
        </Stack>
      </Stack>
    </Box>
  )
}

function DetailRow({
  label,
  value,
  content,
  monospace = false,
  multiline = false,
}: {
  label: string
  value: string
  content?: ReactNode
  monospace?: boolean
  multiline?: boolean
}) {
  return (
    <Box>
      <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mb: 0.5 }}>
        {label}
      </Typography>
      {content ?? (
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
      )}
    </Box>
  )
}

function CommandParamsView({
  items,
  emptyText,
  t,
}: {
  items: ParamSchemaItem[]
  emptyText: string
  t: TFunction<'settings'>
}) {
  if (items.length === 0) {
    return (
      <Typography variant="body2" color="text.secondary">
        {emptyText}
      </Typography>
    )
  }

  return (
    <Stack spacing={1}>
      {items.map(item => (
        <Box
          key={item.name}
          sx={{
            border: '1px solid',
            borderColor: 'divider',
            borderRadius: 1.5,
            px: 1.25,
            py: 1,
            backgroundColor: 'action.hover',
          }}
        >
          <Stack spacing={0.75}>
            <Stack direction="row" spacing={0.75} alignItems="center" useFlexGap flexWrap="wrap">
              <Typography variant="body2" sx={{ fontWeight: 700, fontFamily: 'monospace' }}>
                {item.name}
              </Typography>
              <Chip size="small" variant="outlined" label={item.typeLabel} />
              {item.required && (
                <Chip
                  size="small"
                  color="warning"
                  variant="outlined"
                  label={t('commands.detail.required', '必填')}
                />
              )}
            </Stack>

            {item.description ? (
              <Typography variant="body2" color="text.secondary">
                {item.description}
              </Typography>
            ) : null}

            {(item.defaultValue || item.enumValues.length > 0) && (
              <Stack
                direction={{ xs: 'column', sm: 'row' }}
                spacing={1.5}
                useFlexGap
                flexWrap="wrap"
              >
                {item.defaultValue ? (
                  <Typography variant="caption" color="text.secondary">
                    {t('commands.detail.defaultValue', '默认值')}: {item.defaultValue}
                  </Typography>
                ) : null}
                {item.enumValues.length > 0 ? (
                  <Typography variant="caption" color="text.secondary">
                    {t('commands.detail.allowedValues', '可选值')}: {item.enumValues.join(', ')}
                  </Typography>
                ) : null}
              </Stack>
            )}
          </Stack>
        </Box>
      ))}
    </Stack>
  )
}
