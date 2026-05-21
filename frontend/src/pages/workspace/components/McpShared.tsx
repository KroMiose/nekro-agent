import { useState, useEffect, useMemo } from 'react'
import {
  Box,
  Chip,
  TextField,
  CircularProgress,
  Stack,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  List,
  ListItem,
  ListItemButton,
  ListItemText,
  InputAdornment,
  Typography,
  Paper,
  Card,
  Divider,
  Switch,
  Tooltip,
  Alert,
  Menu,
  MenuItem,
  ListItemIcon,
} from '@mui/material'
import {
  Delete as DeleteIcon,
  Add as AddIcon,
  Search as SearchIcon,
  Edit as EditIcon,
  Code as CodeIcon,
  ViewModule as ViewModuleIcon,
  FormatListBulleted as ListViewIcon,
  FileUpload as ImportIcon,
  SyncOutlined as SyncIcon,
  ArrowDropDown as ArrowDropDownIcon,
  PlayArrow as PlayArrowIcon,
  CheckCircle as CheckCircleIcon,
  ErrorOutline as ErrorOutlineIcon,
} from '@mui/icons-material'
import { useQuery } from '@tanstack/react-query'
import { useTheme } from '@mui/material/styles'
import { Editor } from '@monaco-editor/react'
import {
  mcpApi,
  type McpServerConfig,
  type McpRegistryItem,
  type McpServerType,
  type McpValidationResult,
} from '../../../services/api/workspace'
import { stripJsoncComments, typeColor, typeIcon, emptyServer } from './mcpUtils'
import { CARD_VARIANTS, UNIFIED_TABLE_STYLES } from '../../../theme/variants'
import ActionButton from '../../../components/common/ActionButton'
import IconActionButton from '../../../components/common/IconActionButton'

// ── KeyValueEditor ──

export function KeyValueEditor({
  value,
  onChange,
  keyLabel,
  valueLabel,
}: {
  value: Record<string, string>
  onChange: (v: Record<string, string>) => void
  keyLabel: string
  valueLabel: string
}) {
  const entries = Object.entries(value)
  const handleChange = (oldKey: string, field: 'key' | 'value', newVal: string) => {
    const result: Record<string, string> = {}
    for (const [k, v] of entries) {
      if (k === oldKey) {
        result[field === 'key' ? newVal : k] = field === 'value' ? newVal : v
      } else {
        result[k] = v
      }
    }
    onChange(result)
  }
  const handleAdd = () => onChange({ ...value, '': '' })
  const handleRemove = (key: string) => {
    const result = { ...value }
    delete result[key]
    onChange(result)
  }

  return (
    <Box>
      {entries.map(([k, v], i) => (
        <Box key={i} sx={{ display: 'flex', flexDirection: { xs: 'column', sm: 'row' }, gap: 1, mb: 0.75, alignItems: { xs: 'stretch', sm: 'center' } }}>
          <TextField size="small" label={keyLabel} value={k} onChange={e => handleChange(k, 'key', e.target.value)} sx={{ flex: 1 }} />
          <TextField size="small" label={valueLabel} value={v} onChange={e => handleChange(k, 'value', e.target.value)} sx={{ flex: 2 }} />
          <IconActionButton size="small" onClick={() => handleRemove(k)}><DeleteIcon fontSize="small" /></IconActionButton>
        </Box>
      ))}
      <ActionButton size="small" startIcon={<AddIcon />} onClick={handleAdd}>{keyLabel}</ActionButton>
    </Box>
  )
}

// ── ServerFormDialog ──

export function ServerFormDialog({
  open, onClose, onSubmit, onValidate, initial, title, submitLabel, t,
}: {
  open: boolean; onClose: () => void; onSubmit: (server: McpServerConfig) => void
  onValidate?: (server: McpServerConfig) => Promise<McpValidationResult>
  initial: McpServerConfig; title: string; submitLabel: string; t: (key: string) => string
}) {
  const [form, setForm] = useState<McpServerConfig>(initial)
  const [validating, setValidating] = useState(false)
  const [validationResult, setValidationResult] = useState<McpValidationResult | null>(null)
  // 验证成功时的"结构指纹"快照，提交时与当前表单对比，相同则把验证状态一并写入
  const [validatedSnapshot, setValidatedSnapshot] = useState<string | null>(null)
  useEffect(() => {
    if (open) {
      setForm(initial)
      setValidationResult(null)
      setValidatedSnapshot(null)
    }
  }, [open, initial])

  const ALLOWED_STDIO_CMDS = new Set(['npx', 'uvx'])

  // 给表单做结构指纹（不含 enabled），用于判断"验证后是否被改动过"
  const fingerprint = (s: McpServerConfig) => JSON.stringify({
    name: s.name,
    type: s.type,
    command: s.command ?? '',
    args: s.args ?? [],
    env: s.env ?? {},
    url: s.url ?? '',
    headers: s.headers ?? {},
  })

  const handleSubmit = () => {
    if (!form.name.trim()) return
    if (form.type === 'stdio' && !ALLOWED_STDIO_CMDS.has((form.command ?? '').trim())) return
    const cleaned: McpServerConfig = {
      ...form,
      args: form.args ?? [],
      env: form.env ?? {},
      headers: form.headers ?? {},
    }
    // 验证后未改动 → 携带 validated 状态
    if (
      validationResult?.ok
      && validatedSnapshot
      && validatedSnapshot === fingerprint(cleaned)
    ) {
      cleaned.validation = {
        status: 'validated',
        validated_at: new Date().toISOString(),
        server_name: validationResult.server_info?.name ?? null,
        server_version: validationResult.server_info?.version ?? null,
        tools_count: (validationResult.tools ?? []).length,
        latency_ms: validationResult.latency_ms,
      }
    }
    onSubmit(cleaned)
  }

  const stdioCommandInvalid = form.type === 'stdio' && (form.command ?? '').trim() !== '' && !ALLOWED_STDIO_CMDS.has((form.command ?? '').trim())

  const canValidate = !!onValidate && !!form.name.trim() && !stdioCommandInvalid && (
    form.type === 'stdio'
      ? !!form.command?.trim()
      : !!form.url?.trim()
  )

  const handleValidate = async () => {
    if (!onValidate || validating) return
    setValidating(true)
    setValidationResult(null)
    setValidatedSnapshot(null)
    try {
      const cleaned: McpServerConfig = {
        ...form,
        args: form.args ?? [],
        env: form.env ?? {},
        headers: form.headers ?? {},
      }
      const result = await onValidate(cleaned)
      setValidationResult(result)
      if (result.ok) {
        setValidatedSnapshot(fingerprint(cleaned))
      }
    } catch (e) {
      setValidationResult({
        ok: false,
        latency_ms: 0,
        error: (e as Error).message,
        error_kind: 'transport_error',
      })
    } finally {
      setValidating(false)
    }
  }

  // 表单一旦发生结构变化（不含 enabled），就清掉验证结果与快照，让用户重新点验证
  useEffect(() => {
    if (!validatedSnapshot) return
    if (validatedSnapshot !== fingerprint(form)) {
      setValidationResult(null)
      setValidatedSnapshot(null)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [form])

  return (
    <Dialog open={open} onClose={onClose} maxWidth="sm" fullWidth>
      <DialogTitle>{title}</DialogTitle>
      <DialogContent sx={{ pt: '12px !important' }}>
        <Stack spacing={2}>
          <TextField label={t('detail.mcp.form.name')} value={form.name} onChange={e => setForm(f => ({ ...f, name: e.target.value }))} size="small" fullWidth required />
          <Box sx={{ display: 'flex', gap: 1 }}>
            {(['stdio', 'sse', 'http'] as McpServerType[]).map(tp => (
              <Chip key={tp} label={tp.toUpperCase()} color={form.type === tp ? typeColor(tp) as 'info' | 'warning' | 'success' : 'default'} variant={form.type === tp ? 'filled' : 'outlined'} onClick={() => setForm(f => ({ ...f, type: tp }))} icon={typeIcon(tp)} size="small" />
            ))}
          </Box>
          {form.type === 'stdio' ? (
            <>
              <TextField label={t('detail.mcp.form.command')} value={form.command ?? ''} onChange={e => setForm(f => ({ ...f, command: e.target.value }))} size="small" fullWidth placeholder="npx / uvx" error={stdioCommandInvalid} helperText={stdioCommandInvalid ? t('detail.mcp.form.stdioCommandError') : undefined} />
              <TextField label={t('detail.mcp.form.args')} value={(form.args ?? []).join(' ')} onChange={e => setForm(f => ({ ...f, args: e.target.value.split(' ').filter(Boolean) }))} size="small" fullWidth placeholder="-y @modelcontextprotocol/server-github" helperText={t('detail.mcp.form.argsHint')} />
              <Typography variant="caption" color="text.secondary">{t('detail.mcp.form.envLabel')}</Typography>
              <KeyValueEditor value={form.env ?? {}} onChange={env => setForm(f => ({ ...f, env }))} keyLabel="Key" valueLabel="Value" />
              <Alert severity="info" sx={{ py: 0.5 }}>{t('detail.mcp.form.stdioHint')}</Alert>
            </>
          ) : (
            <>
              <TextField label={t('detail.mcp.form.url')} value={form.url ?? ''} onChange={e => setForm(f => ({ ...f, url: e.target.value }))} size="small" fullWidth placeholder="https://your-mcp-server.example.com/mcp" />
              <Typography variant="caption" color="text.secondary">{t('detail.mcp.form.headersLabel')}</Typography>
              <KeyValueEditor value={form.headers ?? {}} onChange={headers => setForm(f => ({ ...f, headers }))} keyLabel="Header" valueLabel="Value" />
            </>
          )}
          {validationResult && <ValidationResultPanel result={validationResult} t={t} />}
        </Stack>
      </DialogContent>
      <DialogActions sx={{ justifyContent: 'space-between', px: 3 }}>
        <Box>
          {onValidate && (
            <ActionButton
              size="small"
              variant="outlined"
              startIcon={validating ? <CircularProgress size={14} /> : <PlayArrowIcon />}
              onClick={handleValidate}
              disabled={!canValidate || validating}
            >
              {t('mcpServices.validate.button')}
            </ActionButton>
          )}
        </Box>
        <Box sx={{ display: 'flex', gap: 1 }}>
          <ActionButton onClick={onClose}>{t('detail.mcp.form.cancel')}</ActionButton>
          <ActionButton variant="contained" onClick={handleSubmit} disabled={!form.name.trim() || stdioCommandInvalid}>{submitLabel}</ActionButton>
        </Box>
      </DialogActions>
    </Dialog>
  )
}

// ── ValidationResultPanel — 内联展示 MCP 握手结果 ──

function ValidationResultPanel({
  result, t,
}: {
  result: McpValidationResult; t: (key: string) => string
}) {
  if (result.ok) {
    const tools = result.tools ?? []
    return (
      <Alert
        severity="success"
        icon={<CheckCircleIcon fontSize="small" />}
        sx={{ py: 0.5 }}
      >
        <Typography variant="body2" sx={{ fontWeight: 600 }}>
          {t('mcpServices.validate.success', {
            name: result.server_info?.name ?? '-',
            version: result.server_info?.version ?? '-',
          })}
        </Typography>
        <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mt: 0.25 }}>
          {t('mcpServices.validate.toolsAndLatency', {
            count: tools.length,
            latency: Math.round(result.latency_ms),
          })}
        </Typography>
        {tools.length > 0 && (
          <Typography variant="caption" sx={{ display: 'block', fontFamily: 'monospace', mt: 0.5, wordBreak: 'break-all' }}>
            {tools.slice(0, 8).join(', ')}{tools.length > 8 ? '…' : ''}
          </Typography>
        )}
      </Alert>
    )
  }
  const kind = result.error_kind ?? 'transport_error'
  return (
    <Alert severity="error" icon={<ErrorOutlineIcon fontSize="small" />} sx={{ py: 0.5 }}>
      <Typography variant="body2" sx={{ fontWeight: 600 }}>
        {t(`mcpServices.validate.errorKind.${kind}`)}
      </Typography>
      {result.error && (
        <Typography variant="caption" sx={{ display: 'block', mt: 0.25, fontFamily: 'monospace', wordBreak: 'break-all' }}>
          {result.error}
        </Typography>
      )}
    </Alert>
  )
}

// ── RegistryDialog ──

export function RegistryDialog({
  open, onClose, onSelect, t,
}: {
  open: boolean; onClose: () => void; onSelect: (item: McpRegistryItem) => void; t: (key: string) => string
}) {
  const { data: registry, isLoading } = useQuery({ queryKey: ['mcp-registry'], queryFn: () => mcpApi.getRegistry(), enabled: open })
  const [search, setSearch] = useState('')
  const filtered = useMemo(() => (registry ?? []).filter(item => item.name.toLowerCase().includes(search.toLowerCase()) || item.description.toLowerCase().includes(search.toLowerCase()) || item.tags?.some(tag => tag.toLowerCase().includes(search.toLowerCase()))), [registry, search])

  return (
    <Dialog open={open} onClose={onClose} maxWidth="sm" fullWidth>
      <DialogTitle>{t('detail.mcp.registry.title')}</DialogTitle>
      <DialogContent sx={{ pt: '12px !important' }}>
        <TextField size="small" fullWidth placeholder={t('detail.mcp.registry.search')} value={search} onChange={e => setSearch(e.target.value)} sx={{ mb: 1 }} InputProps={{ startAdornment: <InputAdornment position="start"><SearchIcon fontSize="small" /></InputAdornment> }} />
        {isLoading ? (
          <Box sx={{ display: 'flex', justifyContent: 'center', py: 3 }}><CircularProgress size={28} /></Box>
        ) : (
          <List disablePadding>
            {filtered.map(item => (
              <ListItem key={item.id} disablePadding>
                <ListItemButton onClick={() => onSelect(item)} sx={{ borderRadius: 1 }}>
                  <ListItemText
                    primary={<Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}><Typography variant="body2" fontWeight={600}>{item.name}</Typography><Chip label={item.type} size="small" variant="outlined" color={typeColor(item.type)} />{item.tags?.map(tag => <Chip key={tag} label={tag} size="small" variant="outlined" sx={{ height: 20, fontSize: 11 }} />)}</Box>}
                    secondary={item.description}
                  />
                </ListItemButton>
              </ListItem>
            ))}
            {filtered.length === 0 && <Typography variant="body2" color="text.secondary" sx={{ py: 2, textAlign: 'center' }}>{t('detail.mcp.registry.empty')}</Typography>}
          </List>
        )}
      </DialogContent>
      <DialogActions><ActionButton onClick={onClose}>{t('detail.mcp.form.cancel')}</ActionButton></DialogActions>
    </Dialog>
  )
}

// ── McpServerManager (unified server management UI) ──

export interface McpServerManagerProps {
  servers: McpServerConfig[]
  loading: boolean
  onAdd: (server: McpServerConfig) => Promise<void>
  onEdit: (oldName: string, server: McpServerConfig) => Promise<void>
  onDelete: (name: string) => Promise<void>
  onToggleEnabled: (server: McpServerConfig) => Promise<void>
  onImport: (servers: McpServerConfig[]) => Promise<void>
  onSyncToSandbox?: () => Promise<void>
  onValidate?: (server: McpServerConfig) => Promise<McpValidationResult>
  onValidateSaved?: (name: string) => Promise<McpValidationResult>
  // 卡片差异
  cardVariant?: 'workspace' | 'global'
  // 文本
  title?: string
  emptyText: string
  emptyHint?: string
  jsonTitle: string
  jsonHint: string
  deleteTitle: string
  deleteContent: (name: string) => string
  toolbarFilters?: React.ReactNode
  toolbarActions?: React.ReactNode
  t: (key: string) => string
}

export function McpServerManager({
  servers,
  loading,
  onAdd,
  onEdit,
  onDelete,
  onToggleEnabled,
  onImport,
  onSyncToSandbox,
  onValidate,
  onValidateSaved,
  cardVariant = 'workspace',
  title,
  emptyText,
  emptyHint,
  jsonTitle,
  jsonHint,
  deleteTitle,
  deleteContent,
  toolbarFilters,
  toolbarActions,
  t,
}: McpServerManagerProps) {
  const theme = useTheme()
  const isGlobal = cardVariant === 'global'

  // ── View & Dialog state ──
  const [viewMode, setViewMode] = useState<'cards' | 'list' | 'json'>('cards')
  const [addOpen, setAddOpen] = useState(false)
  const [editTarget, setEditTarget] = useState<McpServerConfig | null>(null)
  const [deleteTarget, setDeleteTarget] = useState<string | null>(null)
  const [mutating, setMutating] = useState(false)
  const [importOpen, setImportOpen] = useState(false)
  const [importText, setImportText] = useState('')
  const [importError, setImportError] = useState<string | null>(null)
  const [addMenuAnchor, setAddMenuAnchor] = useState<null | HTMLElement>(null)
  // 卡片/列表上的"验证"状态：{ [name]: 'pending' | result }
  const [validationStates, setValidationStates] = useState<Record<string, 'pending' | McpValidationResult>>({})


  // ── JSON text (与磁盘 .mcp.json 一致：仅含启用项、保留 transport、不含 enabled) ──
  const jsonText = useMemo(() => {
    const obj: Record<string, Record<string, unknown>> = {}
    for (const s of servers) {
      if (!s.enabled) continue
      const entry: Record<string, unknown> = { transport: s.type }
      if (s.type === 'stdio') {
        if (s.command) entry.command = s.command
        if (s.args && s.args.length > 0) entry.args = s.args
        if (s.env && Object.keys(s.env).length > 0) entry.env = s.env
      } else {
        if (s.url) entry.url = s.url
        if (s.headers && Object.keys(s.headers).length > 0) entry.headers = s.headers
      }
      obj[s.name] = entry
    }
    return JSON.stringify({ mcpServers: obj }, null, 2)
  }, [servers])

  // ── Handlers ──
  const withMutating = async (fn: () => Promise<void>) => {
    setMutating(true)
    try { await fn() } finally { setMutating(false) }
  }

  const handleAdd = (server: McpServerConfig) =>
    withMutating(async () => { await onAdd(server); setAddOpen(false) })

  const handleEdit = (server: McpServerConfig) => {
    if (!editTarget) return
    withMutating(async () => { await onEdit(editTarget.name, server); setEditTarget(null) })
  }

  const handleDelete = () => {
    if (!deleteTarget) return
    withMutating(async () => { await onDelete(deleteTarget); setDeleteTarget(null) })
  }

  const handleValidateCard = async (server: McpServerConfig) => {
    const validator = onValidateSaved
      ? () => onValidateSaved(server.name)
      : onValidate
        ? () => onValidate(server)
        : null
    if (!validator) return
    setValidationStates(prev => ({ ...prev, [server.name]: 'pending' }))
    try {
      const result = await validator()
      setValidationStates(prev => ({ ...prev, [server.name]: result }))
    } catch (e) {
      setValidationStates(prev => ({
        ...prev,
        [server.name]: {
          ok: false,
          latency_ms: 0,
          error: (e as Error).message,
          error_kind: 'transport_error',
        },
      }))
    }
  }

  const handleImport = async () => {
    try {
      const parsed = JSON.parse(stripJsoncComments(importText))
      const mcpObj = parsed.mcpServers ?? parsed
      if (typeof mcpObj !== 'object' || Array.isArray(mcpObj)) {
        setImportError(t('mcpServices.import.formatError')); return
      }
      const allServers: McpServerConfig[] = Object.entries(mcpObj).map(([name, cfg]) => {
        const c = cfg as Record<string, unknown>
        // 接受 transport / transport_type / type 三种历史字段命名，按优先级回退到启发式推断
        const tp = (c.transport as string)
          ?? (c.transport_type as string)
          ?? (c.type as string)
          ?? (c.command ? 'stdio' : c.url ? 'http' : 'stdio')
        return { name, type: tp as McpServerType, enabled: true, command: (c.command as string) ?? '', args: (c.args as string[]) ?? [], env: (c.env as Record<string, string>) ?? {}, url: (c.url as string) ?? '', headers: (c.headers as Record<string, string>) ?? {} }
      })
      if (allServers.length === 0) { setImportError(t('mcpServices.import.emptyError')); return }
      // STDIO 仅允许包管理器命令（npx/uvx 等），其余拒绝导入
      const ALLOWED_STDIO_CMDS = new Set(['npx', 'uvx'])
      const unsupported = allServers.filter(s =>
        s.type === 'stdio' && !ALLOWED_STDIO_CMDS.has((s.command ?? '').trim())
      )
      const newServers = allServers.filter(s => !unsupported.includes(s))
      if (newServers.length === 0) {
        setImportError(t('mcpServices.import.allLocalFileError')); return
      }
      setMutating(true)
      await onImport(newServers)
      setImportOpen(false); setImportText(''); setImportError(null)
    } catch { setImportError(t('mcpServices.import.parseError')) } finally { setMutating(false) }
  }

  // ── 单个 server 的"验证"按钮渲染器，复用于卡片/列表 ──
  const renderValidateButton = (server: McpServerConfig, iconSize = 16) => {
    if (!onValidate && !onValidateSaved) return null
    const state = validationStates[server.name]
    const pending = state === 'pending'
    const result = state && state !== 'pending' ? (state as McpValidationResult) : null
    let color: 'inherit' | 'success' | 'error' = 'inherit'
    let icon: React.ReactNode = <PlayArrowIcon sx={{ fontSize: iconSize }} />
    if (pending) {
      icon = <CircularProgress size={iconSize - 2} />
    } else if (result?.ok) {
      color = 'success'
      icon = <CheckCircleIcon sx={{ fontSize: iconSize }} />
    } else if (result && !result.ok) {
      color = 'error'
      icon = <ErrorOutlineIcon sx={{ fontSize: iconSize }} />
    }
    const tooltip = pending
      ? t('mcpServices.validate.pending')
      : result?.ok
        ? t('mcpServices.validate.success', {
          name: result.server_info?.name ?? '-',
          version: result.server_info?.version ?? '-',
        }) + ` (${(result.tools ?? []).length} tools, ${Math.round(result.latency_ms)}ms)`
        : result
          ? t(`mcpServices.validate.errorKind.${result.error_kind ?? 'transport_error'}`) + (result.error ? ` — ${result.error}` : '')
          : t('mcpServices.validate.button')
    return (
      <Tooltip title={tooltip} arrow>
        <span>
          <IconActionButton size="small" color={color} onClick={() => handleValidateCard(server)} disabled={pending || mutating}>
            {icon}
          </IconActionButton>
        </span>
      </Tooltip>
    )
  }

  // ── 持久化的验证状态 chip（已验证/未验证/失败）──
  const renderValidationChip = (server: McpServerConfig) => {
    const status = server.validation?.status ?? 'unvalidated'
    if (status === 'validated') {
      return (
        <Tooltip
          title={t('mcpServices.validate.chip.validatedTooltip', {
            time: server.validation?.validated_at?.slice(0, 19).replace('T', ' ') ?? '-',
            tools: server.validation?.tools_count ?? 0,
          })}
          arrow
        >
          <Chip
            icon={<CheckCircleIcon sx={{ fontSize: 12 }} />}
            label={t('mcpServices.validate.chip.validated')}
            size="small"
            color="success"
            variant="outlined"
            sx={{ height: 18, fontSize: 10, '& .MuiChip-icon': { ml: 0.5 }, '& .MuiChip-label': { px: 0.75 } }}
          />
        </Tooltip>
      )
    }
    if (status === 'failed') {
      return (
        <Tooltip title={server.validation?.last_error ?? t('mcpServices.validate.chip.failedTooltip')} arrow>
          <Chip
            icon={<ErrorOutlineIcon sx={{ fontSize: 12 }} />}
            label={t('mcpServices.validate.chip.failed')}
            size="small"
            color="error"
            variant="outlined"
            sx={{ height: 18, fontSize: 10, '& .MuiChip-icon': { ml: 0.5 }, '& .MuiChip-label': { px: 0.75 } }}
          />
        </Tooltip>
      )
    }
    return (
      <Tooltip title={t('mcpServices.validate.chip.unvalidatedTooltip')} arrow>
        <Chip
          label={t('mcpServices.validate.chip.unvalidated')}
          size="small"
          color="warning"
          variant="outlined"
          sx={{ height: 18, fontSize: 10, '& .MuiChip-label': { px: 0.75 } }}
        />
      </Tooltip>
    )
  }

  return (
    <Stack spacing={2}>
      {/* Toolbar */}
      <Card sx={CARD_VARIANTS.default.styles}>
        <Box sx={{ px: { xs: 1.5, sm: 2 }, py: 1.25, display: 'flex', alignItems: 'center', gap: 1.25, flexWrap: 'wrap' }}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.25, flexWrap: 'wrap', flex: '1 1 520px', minWidth: 0 }}>
            {title && (
              <Typography variant="subtitle2" sx={{ fontWeight: 600, flexShrink: 0 }}>
                {title}
              </Typography>
            )}
            {toolbarFilters}
          </Box>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, flexWrap: 'wrap', marginLeft: 'auto', width: { xs: '100%', sm: 'auto' } }}>
            {toolbarActions}
            {viewMode !== 'json' && (
              <>
                {onSyncToSandbox && (
                  <ActionButton size="small" variant="outlined" startIcon={<SyncIcon />} onClick={() => { onSyncToSandbox().catch(() => {}) }} disabled={mutating}>
                    {t('detail.mcp.syncToSandbox')}
                  </ActionButton>
                )}
                <ActionButton size="small" variant="contained" startIcon={<AddIcon />} endIcon={<ArrowDropDownIcon />} onClick={e => setAddMenuAnchor(e.currentTarget)}>
                  {t('detail.mcp.addServer')}
                </ActionButton>
                <Menu anchorEl={addMenuAnchor} open={!!addMenuAnchor} onClose={() => setAddMenuAnchor(null)}>
                  <MenuItem onClick={() => { setAddMenuAnchor(null); setAddOpen(true) }}>
                    <ListItemIcon><AddIcon fontSize="small" /></ListItemIcon>
                    {t('detail.mcp.addManual')}
                  </MenuItem>
                  <MenuItem onClick={() => { setAddMenuAnchor(null); setImportOpen(true); setImportText(''); setImportError(null) }}>
                    <ListItemIcon><ImportIcon fontSize="small" /></ListItemIcon>
                    {t('mcpServices.toolbar.importJson')}
                  </MenuItem>
                </Menu>
              </>
            )}
            <Box sx={{ display: 'flex', border: '1px solid', borderColor: 'divider', borderRadius: 1, overflow: 'hidden' }}>
              {(['cards', 'list', 'json'] as const).map(mode => (
                <IconActionButton
                  key={mode}
                  size="small"
                  onClick={() => setViewMode(mode)}
                  sx={{
                    borderRadius: 0,
                    bgcolor: viewMode === mode ? 'action.selected' : 'transparent',
                    px: 1,
                  }}
                >
                  <Tooltip title={
                    mode === 'cards' ? t('detail.mcp.switchToCards')
                      : mode === 'list' ? t('detail.mcp.switchToList')
                        : t('detail.mcp.switchToJson')
                  }>
                    {mode === 'cards' ? <ViewModuleIcon fontSize="small" />
                      : mode === 'list' ? <ListViewIcon fontSize="small" />
                        : <CodeIcon fontSize="small" />}
                  </Tooltip>
                </IconActionButton>
              ))}
            </Box>
          </Box>
        </Box>
      </Card>

      {/* Card view */}
      {viewMode === 'cards' && (
        loading ? (
          <Box sx={{ display: 'flex', justifyContent: 'center', py: 4 }}><CircularProgress size={28} /></Box>
        ) : servers.length === 0 ? (
          <Card sx={CARD_VARIANTS.default.styles}>
            <Box sx={{ textAlign: 'center', py: 4, px: 2 }}>
              <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>{emptyText}</Typography>
              {emptyHint && <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>{emptyHint}</Typography>}
              <ActionButton variant="outlined" startIcon={<AddIcon />} onClick={() => setAddOpen(true)}>{t('detail.mcp.addManual')}</ActionButton>
            </Box>
          </Card>
        ) : isGlobal ? (
          <Box sx={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(320px, 1fr))', gap: 2 }}>
            {servers.map(server => (
              <Card key={server.name} sx={{ ...CARD_VARIANTS.default.styles, display: 'flex', flexDirection: 'column', transition: 'border-color 0.2s, box-shadow 0.2s', '&:hover': { borderColor: 'primary.main', boxShadow: 2 } }}>
                <Box sx={{ p: 2, flex: 1, display: 'flex', flexDirection: 'column', gap: 1 }}>
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.75, flexWrap: 'wrap' }}>
                    <Chip label={server.type.toUpperCase()} size="small" color={typeColor(server.type) as 'info' | 'warning' | 'success'} variant="outlined" icon={typeIcon(server.type)} sx={{ fontSize: '0.7rem', height: 22 }} />
                    {server.enabled && (
                      <Chip label={t('mcpServices.toolbar.autoInject')} size="small" sx={{ fontSize: '0.65rem', height: 20, bgcolor: 'warning.main', color: 'warning.contrastText', fontWeight: 600 }} />
                    )}
                    {renderValidationChip(server)}
                    <Box sx={{ ml: 'auto', width: 8, height: 8, borderRadius: '50%', bgcolor: server.enabled ? 'success.main' : 'text.disabled' }} />
                  </Box>
                  <Typography variant="subtitle1" sx={{ fontWeight: 600, lineHeight: 1.3 }}>{server.name}</Typography>
                  <Typography variant="body2" color="text.secondary" sx={{ display: '-webkit-box', WebkitLineClamp: 2, WebkitBoxOrient: 'vertical', overflow: 'hidden', lineHeight: 1.5, fontFamily: 'monospace', fontSize: '0.75rem' }}>
                    {server.type === 'stdio' ? `${server.command ?? ''} ${(server.args ?? []).join(' ')}` : server.url ?? ''}
                  </Typography>
                </Box>
                <Box sx={{ px: 2, py: 1, borderTop: '1px solid', borderColor: 'divider', display: 'flex', alignItems: 'center', gap: 0.5 }}>
                  <Tooltip title={t('mcpServices.toolbar.autoInjectTooltip')}>
                    <Switch size="small" checked={server.enabled} onChange={() => onToggleEnabled(server)} disabled={mutating} color="warning" />
                  </Tooltip>
                  <Typography variant="caption" color="text.secondary" sx={{ mr: 'auto' }}>
                    {server.enabled ? t('mcpServices.toolbar.autoInjectOn') : t('mcpServices.toolbar.autoInjectOff')}
                  </Typography>
                  <Tooltip title={t('detail.mcp.edit')}><IconActionButton size="small" color="primary" onClick={() => setEditTarget(server)}><EditIcon sx={{ fontSize: 16 }} /></IconActionButton></Tooltip>
                  {renderValidateButton(server, 16)}
                  <Tooltip title={t('detail.mcp.delete')}><IconActionButton size="small" color="error" onClick={() => setDeleteTarget(server.name)}><DeleteIcon sx={{ fontSize: 16 }} /></IconActionButton></Tooltip>
                </Box>
              </Card>
            ))}
          </Box>
        ) : (
          <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', sm: 'repeat(auto-fill, minmax(260px, 1fr))' }, gap: 2 }}>
            {servers.map(server => (
              <Card key={server.name} sx={{ ...CARD_VARIANTS.default.styles, minWidth: 0, opacity: server.enabled ? 1 : 0.6, transition: 'all 0.2s ease' }}>
                <Box sx={{ p: 2 }}>
                  <Box sx={{ display: 'flex', alignItems: 'center', mb: 1, gap: 1, flexWrap: 'wrap' }}>
                    <Box sx={{ width: 8, height: 8, borderRadius: '50%', bgcolor: server.enabled ? 'success.main' : 'text.disabled', flexShrink: 0 }} />
                    <Typography variant="subtitle2" sx={{ fontWeight: 600, flexGrow: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', minWidth: 0 }}>{server.name}</Typography>
                    {renderValidationChip(server)}
                    <Chip label={server.type.toUpperCase()} size="small" color={typeColor(server.type) as 'info' | 'warning' | 'success'} variant="outlined" sx={{ height: 20, fontSize: 11 }} />
                  </Box>
                  <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mb: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                    {server.type === 'stdio' ? `${server.command ?? ''} ${(server.args ?? []).join(' ')}` : server.url ?? ''}
                  </Typography>
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                    <Tooltip title={server.enabled ? t('detail.mcp.disable') : t('detail.mcp.enable')}>
                      <Switch size="small" checked={server.enabled} onChange={() => onToggleEnabled(server)} disabled={mutating} />
                    </Tooltip>
                    <Box sx={{ flexGrow: 1 }} />
                    <Tooltip title={t('detail.mcp.edit')}><IconActionButton size="small" onClick={() => setEditTarget(server)}><EditIcon fontSize="small" /></IconActionButton></Tooltip>
                    {renderValidateButton(server, 18)}
                    <Tooltip title={t('detail.mcp.delete')}><IconActionButton size="small" onClick={() => setDeleteTarget(server.name)}><DeleteIcon fontSize="small" /></IconActionButton></Tooltip>
                  </Box>
                </Box>
              </Card>
            ))}
          </Box>
        )
      )}

      {/* List view */}
      {viewMode === 'list' && !loading && servers.length > 0 && (
        <Paper sx={{ ...UNIFIED_TABLE_STYLES.tableContentContainer, position: 'relative', minHeight: 0 }}>
          <Box sx={UNIFIED_TABLE_STYLES.tableViewport}>
            {servers.map((server, index) => (
              <Box key={server.name}>
                {index > 0 && <Divider />}
                <Box sx={{ display: 'flex', alignItems: { xs: 'flex-start', sm: 'center' }, flexWrap: { xs: 'wrap', sm: 'nowrap' }, px: { xs: 1.25, sm: 2 }, py: 1.25, gap: { xs: 0.75, sm: 1.5 }, ...UNIFIED_TABLE_STYLES.row }}>
                  <Chip label={server.type.toUpperCase()} size="small" color={typeColor(server.type) as 'info' | 'warning' | 'success'} variant="outlined" sx={{ fontSize: '0.7rem', height: 22, width: 64, flexShrink: 0 }} />
                  <Box sx={{ flexGrow: 1, minWidth: 0 }}>
                    <Box sx={{ display: 'flex', alignItems: 'baseline', gap: 1, flexDirection: { xs: 'column', sm: 'row' } }}>
                      <Typography variant="body2" sx={{ fontWeight: 600, flexShrink: 0, maxWidth: '100%', overflow: 'hidden', textOverflow: 'ellipsis' }}>{server.name}</Typography>
                      <Typography variant="caption" color="text.secondary" sx={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: { xs: 'normal', sm: 'nowrap' }, wordBreak: 'break-all', fontFamily: 'monospace' }}>
                        {server.type === 'stdio' ? `${server.command ?? ''} ${(server.args ?? []).join(' ')}` : server.url ?? ''}
                      </Typography>
                    </Box>
                  </Box>
                  {renderValidationChip(server)}
                  <Box sx={{ width: 8, height: 8, borderRadius: '50%', bgcolor: server.enabled ? 'success.main' : 'text.disabled', flexShrink: 0 }} />
                  {isGlobal && (
                    <Tooltip title={t('mcpServices.toolbar.autoInjectTooltip')}>
                      <Switch size="small" checked={server.enabled} onChange={() => onToggleEnabled(server)} disabled={mutating} color="warning" />
                    </Tooltip>
                  )}
                  <Box sx={{ display: 'flex', gap: 0.25, flexShrink: 0 }}>
                    <Tooltip title={t('detail.mcp.edit')}><IconActionButton size="small" color="primary" onClick={() => setEditTarget(server)}><EditIcon sx={{ fontSize: 14 }} /></IconActionButton></Tooltip>
                    {renderValidateButton(server, 14)}
                    <Tooltip title={t('detail.mcp.delete')}><IconActionButton size="small" color="error" onClick={() => setDeleteTarget(server.name)}><DeleteIcon sx={{ fontSize: 14 }} /></IconActionButton></Tooltip>
                  </Box>
                </Box>
              </Box>
            ))}
          </Box>
        </Paper>
      )}

      {/* JSON view (read-only) */}
      {viewMode === 'json' && (
        <Card sx={{ ...CARD_VARIANTS.default.styles, display: 'flex', flexDirection: 'column' }}>
          <Box sx={{ px: 2, py: 1.5, borderBottom: '1px solid', borderColor: 'divider', display: 'flex', alignItems: 'center', gap: 1 }}>
            <Typography variant="subtitle2" sx={{ fontWeight: 600, flexGrow: 1 }}>{jsonTitle}</Typography>
            <Chip label={t('mcpServices.toolbar.readOnly')} size="small" variant="outlined" sx={{ height: 20, fontSize: 11 }} />
          </Box>
          <Box sx={{ minHeight: 300 }}>
            <Editor
              height="400px"
              language="json"
              value={jsonText}
              theme={theme.palette.mode === 'dark' ? 'vs-dark' : 'vs'}
              options={{ readOnly: true, minimap: { enabled: false }, fontSize: 13, lineNumbers: 'on', wordWrap: 'off', scrollBeyondLastLine: false, renderLineHighlight: 'none', tabSize: 2, folding: true }}
            />
          </Box>
          <Box sx={{ px: 2, py: 1, borderTop: '1px solid', borderColor: 'divider' }}>
            <Typography variant="caption" color="text.secondary">{jsonHint}</Typography>
          </Box>
        </Card>
      )}

      {/* Add dialog */}
      <ServerFormDialog open={addOpen} onClose={() => setAddOpen(false)} onSubmit={handleAdd} onValidate={onValidate} initial={emptyServer()} title={t('detail.mcp.addTitle')} submitLabel={mutating ? t('detail.mcp.adding') : t('detail.mcp.add')} t={t} />

      {/* Edit dialog */}
      <ServerFormDialog open={!!editTarget} onClose={() => setEditTarget(null)} onSubmit={handleEdit} onValidate={onValidate} initial={editTarget ?? emptyServer()} title={t('detail.mcp.editTitle')} submitLabel={mutating ? t('detail.mcp.saving') : t('detail.mcp.save')} t={t} />

      {/* Delete dialog */}
      <Dialog open={!!deleteTarget} onClose={() => setDeleteTarget(null)} maxWidth="xs">
        <DialogTitle>{deleteTitle}</DialogTitle>
        <DialogContent><Typography variant="body2">{deleteContent(deleteTarget ?? '')}</Typography></DialogContent>
        <DialogActions>
          <ActionButton onClick={() => setDeleteTarget(null)}>{t('detail.mcp.form.cancel')}</ActionButton>
          <ActionButton variant="contained" color="error" onClick={handleDelete} disabled={mutating}>{mutating ? <CircularProgress size={20} /> : t('detail.mcp.delete')}</ActionButton>
        </DialogActions>
      </Dialog>

      {/* Import dialog */}
      <Dialog open={importOpen} onClose={() => setImportOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>{t('mcpServices.import.title')}</DialogTitle>
        <DialogContent sx={{ pt: '12px !important' }}>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 1.5 }}>{t('mcpServices.import.hint')}</Typography>
          {importError && <Alert severity="error" sx={{ mb: 1.5, py: 0.5 }}>{importError}</Alert>}
          <TextField
            multiline rows={12} fullWidth
            placeholder={`{\n  "mcpServers": {\n    "server-name": {\n      "command": "npx",\n      "args": ["-y", "@example/mcp-server"],\n      "env": { "API_KEY": "..." }\n    }\n  }\n}`}
            value={importText} onChange={e => { setImportText(e.target.value); setImportError(null) }}
            sx={{ fontFamily: 'monospace', fontSize: '0.8rem' }}
          />
        </DialogContent>
        <DialogActions>
          <ActionButton onClick={() => setImportOpen(false)}>{t('detail.mcp.form.cancel')}</ActionButton>
          <ActionButton variant="contained" onClick={handleImport} disabled={mutating || !importText.trim()}>{mutating ? <CircularProgress size={20} /> : t('mcpServices.import.importBtn')}</ActionButton>
        </DialogActions>
      </Dialog>
    </Stack>
  )
}
