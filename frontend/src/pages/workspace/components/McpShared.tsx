import { useState, useEffect, useMemo } from 'react'
import {
  Box,
  Button,
  Chip,
  TextField,
  CircularProgress,
  Stack,
  IconButton,
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
} from '@mui/icons-material'
import { useQuery } from '@tanstack/react-query'
import { useTheme } from '@mui/material/styles'
import { Editor } from '@monaco-editor/react'
import {
  mcpApi,
  type McpServerConfig,
  type McpRegistryItem,
  type McpServerType,
} from '../../../services/api/workspace'
import { stripJsoncComments, typeColor, typeIcon, emptyServer } from './mcpUtils'
import { CARD_VARIANTS, UNIFIED_TABLE_STYLES } from '../../../theme/variants'

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
        <Box key={i} sx={{ display: 'flex', gap: 1, mb: 0.5, alignItems: 'center' }}>
          <TextField size="small" label={keyLabel} value={k} onChange={e => handleChange(k, 'key', e.target.value)} sx={{ flex: 1 }} />
          <TextField size="small" label={valueLabel} value={v} onChange={e => handleChange(k, 'value', e.target.value)} sx={{ flex: 2 }} />
          <IconButton size="small" onClick={() => handleRemove(k)}><DeleteIcon fontSize="small" /></IconButton>
        </Box>
      ))}
      <Button size="small" startIcon={<AddIcon />} onClick={handleAdd}>{keyLabel}</Button>
    </Box>
  )
}

// ── ServerFormDialog ──

export function ServerFormDialog({
  open, onClose, onSubmit, initial, title, submitLabel, t,
}: {
  open: boolean; onClose: () => void; onSubmit: (server: McpServerConfig) => void
  initial: McpServerConfig; title: string; submitLabel: string; t: (key: string) => string
}) {
  const [form, setForm] = useState<McpServerConfig>(initial)
  useEffect(() => { if (open) setForm(initial) }, [open, initial])

  const ALLOWED_STDIO_CMDS = new Set(['npx', 'uvx', 'bunx', 'pnpx'])

  const handleSubmit = () => {
    if (!form.name.trim()) return
    if (form.type === 'stdio' && !ALLOWED_STDIO_CMDS.has((form.command ?? '').trim())) return
    onSubmit({ ...form, args: form.args ?? [], env: form.env ?? {}, headers: form.headers ?? {} })
  }

  const stdioCommandInvalid = form.type === 'stdio' && (form.command ?? '').trim() !== '' && !ALLOWED_STDIO_CMDS.has((form.command ?? '').trim())

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
              <TextField label={t('detail.mcp.form.command')} value={form.command ?? ''} onChange={e => setForm(f => ({ ...f, command: e.target.value }))} size="small" fullWidth placeholder="npx / uvx / bunx / pnpx" error={stdioCommandInvalid} helperText={stdioCommandInvalid ? t('detail.mcp.form.stdioCommandError') : undefined} />
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
        </Stack>
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose}>{t('detail.mcp.form.cancel')}</Button>
        <Button variant="contained" onClick={handleSubmit} disabled={!form.name.trim() || stdioCommandInvalid}>{submitLabel}</Button>
      </DialogActions>
    </Dialog>
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
      <DialogActions><Button onClick={onClose}>{t('detail.mcp.form.cancel')}</Button></DialogActions>
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
  // 卡片差异
  cardVariant?: 'workspace' | 'global'
  // 文本
  emptyText: string
  emptyHint?: string
  jsonTitle: string
  jsonHint: string
  deleteTitle: string
  deleteContent: (name: string) => string
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
  cardVariant = 'workspace',
  emptyText,
  emptyHint,
  jsonTitle,
  jsonHint,
  deleteTitle,
  deleteContent,
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

  // ── JSON text ──
  const jsonText = useMemo(() => {
    const obj: Record<string, Record<string, unknown>> = {}
    for (const s of servers) {
      if (s.type === 'stdio') {
        obj[s.name] = { command: s.command, args: s.args, env: s.env }
      } else {
        obj[s.name] = { url: s.url, headers: s.headers }
      }
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

  const handleImport = async () => {
    try {
      const parsed = JSON.parse(stripJsoncComments(importText))
      const mcpObj = parsed.mcpServers ?? parsed
      if (typeof mcpObj !== 'object' || Array.isArray(mcpObj)) {
        setImportError(t('mcpServices.import.formatError')); return
      }
      const allServers: McpServerConfig[] = Object.entries(mcpObj).map(([name, cfg]) => {
        const c = cfg as Record<string, unknown>
        const tp = (c.transport_type as string) ?? (c.command ? 'stdio' : c.url ? 'http' : 'stdio')
        return { name, type: tp as McpServerType, enabled: true, command: (c.command as string) ?? '', args: (c.args as string[]) ?? [], env: (c.env as Record<string, string>) ?? {}, url: (c.url as string) ?? '', headers: (c.headers as Record<string, string>) ?? {} }
      })
      if (allServers.length === 0) { setImportError(t('mcpServices.import.emptyError')); return }
      // STDIO 仅允许包管理器命令（npx/uvx 等），其余拒绝导入
      const ALLOWED_STDIO_CMDS = new Set(['npx', 'uvx', 'bunx', 'pnpx'])
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

  return (
    <Stack spacing={2}>
      {/* Toolbar */}
      <Card sx={CARD_VARIANTS.default.styles}>
        <Box sx={{ px: 2, py: 1.25, display: 'flex', alignItems: 'center', gap: 1, flexWrap: 'wrap' }}>
          <Typography variant="subtitle2" sx={{ fontWeight: 600, flexGrow: 1 }}>
            {t('detail.mcp.title')}
          </Typography>
          {viewMode !== 'json' && (
            <>
              {onSyncToSandbox && (
                <Button size="small" variant="outlined" startIcon={<SyncIcon />} onClick={() => { onSyncToSandbox().catch(() => {}) }} disabled={mutating}>
                  {t('detail.mcp.syncToSandbox')}
                </Button>
              )}
              <Button size="small" variant="contained" startIcon={<AddIcon />} endIcon={<ArrowDropDownIcon />} onClick={e => setAddMenuAnchor(e.currentTarget)}>
                {t('detail.mcp.addServer')}
              </Button>
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
              <IconButton
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
              </IconButton>
            ))}
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
              <Button variant="outlined" startIcon={<AddIcon />} onClick={() => setAddOpen(true)}>{t('detail.mcp.addManual')}</Button>
            </Box>
          </Card>
        ) : isGlobal ? (
          <Box sx={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(320px, 1fr))', gap: 2 }}>
            {servers.map(server => (
              <Card key={server.name} sx={{ ...CARD_VARIANTS.default.styles, display: 'flex', flexDirection: 'column', opacity: server.enabled ? 1 : 0.55, transition: 'border-color 0.2s, box-shadow 0.2s, opacity 0.2s', '&:hover': { borderColor: 'primary.main', boxShadow: 2 } }}>
                <Box sx={{ p: 2, flex: 1, display: 'flex', flexDirection: 'column', gap: 1 }}>
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.75 }}>
                    <Chip label={server.type.toUpperCase()} size="small" color={typeColor(server.type) as 'info' | 'warning' | 'success'} variant="outlined" icon={typeIcon(server.type)} sx={{ fontSize: '0.7rem', height: 22 }} />
                    <Chip label={t('mcpServices.toolbar.autoInject')} size="small" sx={{ fontSize: '0.65rem', height: 20, bgcolor: 'warning.main', color: 'warning.contrastText', fontWeight: 600 }} />
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
                  <Tooltip title={t('detail.mcp.edit')}><IconButton size="small" color="primary" onClick={() => setEditTarget(server)}><EditIcon sx={{ fontSize: 16 }} /></IconButton></Tooltip>
                  <Tooltip title={t('detail.mcp.delete')}><IconButton size="small" color="error" onClick={() => setDeleteTarget(server.name)}><DeleteIcon sx={{ fontSize: 16 }} /></IconButton></Tooltip>
                </Box>
              </Card>
            ))}
          </Box>
        ) : (
          <Box sx={{ display: 'flex', gap: 2, flexWrap: 'wrap' }}>
            {servers.map(server => (
              <Card key={server.name} sx={{ ...CARD_VARIANTS.default.styles, width: 280, opacity: server.enabled ? 1 : 0.6, transition: 'all 0.2s ease' }}>
                <Box sx={{ p: 2 }}>
                  <Box sx={{ display: 'flex', alignItems: 'center', mb: 1, gap: 1 }}>
                    <Box sx={{ width: 8, height: 8, borderRadius: '50%', bgcolor: server.enabled ? 'success.main' : 'text.disabled', flexShrink: 0 }} />
                    <Typography variant="subtitle2" sx={{ fontWeight: 600, flexGrow: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{server.name}</Typography>
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
                    <Tooltip title={t('detail.mcp.edit')}><IconButton size="small" onClick={() => setEditTarget(server)}><EditIcon fontSize="small" /></IconButton></Tooltip>
                    <Tooltip title={t('detail.mcp.delete')}><IconButton size="small" onClick={() => setDeleteTarget(server.name)}><DeleteIcon fontSize="small" /></IconButton></Tooltip>
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
                <Box sx={{ display: 'flex', alignItems: 'center', px: 2, py: 1.25, gap: 1.5, ...UNIFIED_TABLE_STYLES.row }}>
                  <Chip label={server.type.toUpperCase()} size="small" color={typeColor(server.type) as 'info' | 'warning' | 'success'} variant="outlined" sx={{ fontSize: '0.7rem', height: 22, width: 64, flexShrink: 0 }} />
                  <Box sx={{ flexGrow: 1, minWidth: 0 }}>
                    <Box sx={{ display: 'flex', alignItems: 'baseline', gap: 1 }}>
                      <Typography variant="body2" sx={{ fontWeight: 600, flexShrink: 0 }}>{server.name}</Typography>
                      <Typography variant="caption" color="text.secondary" sx={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', fontFamily: 'monospace' }}>
                        {server.type === 'stdio' ? `${server.command ?? ''} ${(server.args ?? []).join(' ')}` : server.url ?? ''}
                      </Typography>
                    </Box>
                  </Box>
                  <Box sx={{ width: 8, height: 8, borderRadius: '50%', bgcolor: server.enabled ? 'success.main' : 'text.disabled', flexShrink: 0 }} />
                  {isGlobal && (
                    <Tooltip title={t('mcpServices.toolbar.autoInjectTooltip')}>
                      <Switch size="small" checked={server.enabled} onChange={() => onToggleEnabled(server)} disabled={mutating} color="warning" />
                    </Tooltip>
                  )}
                  <Box sx={{ display: 'flex', gap: 0.25, flexShrink: 0 }}>
                    <Tooltip title={t('detail.mcp.edit')}><IconButton size="small" color="primary" onClick={() => setEditTarget(server)}><EditIcon sx={{ fontSize: 14 }} /></IconButton></Tooltip>
                    <Tooltip title={t('detail.mcp.delete')}><IconButton size="small" color="error" onClick={() => setDeleteTarget(server.name)}><DeleteIcon sx={{ fontSize: 14 }} /></IconButton></Tooltip>
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
      <ServerFormDialog open={addOpen} onClose={() => setAddOpen(false)} onSubmit={handleAdd} initial={emptyServer()} title={t('detail.mcp.addTitle')} submitLabel={mutating ? t('detail.mcp.adding') : t('detail.mcp.add')} t={t} />

      {/* Edit dialog */}
      <ServerFormDialog open={!!editTarget} onClose={() => setEditTarget(null)} onSubmit={handleEdit} initial={editTarget ?? emptyServer()} title={t('detail.mcp.editTitle')} submitLabel={mutating ? t('detail.mcp.saving') : t('detail.mcp.save')} t={t} />

      {/* Delete dialog */}
      <Dialog open={!!deleteTarget} onClose={() => setDeleteTarget(null)} maxWidth="xs">
        <DialogTitle>{deleteTitle}</DialogTitle>
        <DialogContent><Typography variant="body2">{deleteContent(deleteTarget ?? '')}</Typography></DialogContent>
        <DialogActions>
          <Button onClick={() => setDeleteTarget(null)}>{t('detail.mcp.form.cancel')}</Button>
          <Button variant="contained" color="error" onClick={handleDelete} disabled={mutating}>{mutating ? <CircularProgress size={20} /> : t('detail.mcp.delete')}</Button>
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
          <Button onClick={() => setImportOpen(false)}>{t('detail.mcp.form.cancel')}</Button>
          <Button variant="contained" onClick={handleImport} disabled={mutating || !importText.trim()}>{mutating ? <CircularProgress size={20} /> : t('mcpServices.import.importBtn')}</Button>
        </DialogActions>
      </Dialog>
    </Stack>
  )
}
