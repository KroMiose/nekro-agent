import { useState, useEffect, useMemo } from 'react'
import {
  Box,
  Button,
  Card,
  CardContent,
  Typography,
  Chip,
  TextField,
  CircularProgress,
  Alert,
  Stack,
  IconButton,
  Tooltip,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Switch,
  alpha,
  List,
  ListItem,
  ListItemButton,
  ListItemText,
  InputAdornment,
} from '@mui/material'
import { useTheme } from '@mui/material/styles'
import {
  Save as SaveIcon,
  Delete as DeleteIcon,
  Add as AddIcon,
  Edit as EditIcon,
  Search as SearchIcon,
  Code as CodeIcon,
  ViewModule as ViewModuleIcon,
  Terminal as TerminalIcon,
  Http as HttpIcon,
} from '@mui/icons-material'
import { Editor } from '@monaco-editor/react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import {
  workspaceApi,
  mcpApi,
  type WorkspaceDetail,
  type McpServerConfig,
  type McpRegistryItem,
  type McpServerType,
} from '../../../services/api/workspace'
import { useNotification } from '../../../hooks/useNotification'
import { CARD_VARIANTS } from '../../../theme/variants'
import { useTranslation } from 'react-i18next'

// ── 辅助函数 ──

/** JSONC 注释剥离（逐字符解析，正确处理字符串内的 //） */
const stripJsoncComments = (text: string): string => {
  let result = ''
  let i = 0
  let inString = false
  let escaped = false
  while (i < text.length) {
    const ch = text[i]
    if (escaped) { result += ch; escaped = false; i++; continue }
    if (ch === '\\' && inString) { result += ch; escaped = true; i++; continue }
    if (ch === '"') { inString = !inString; result += ch; i++; continue }
    if (!inString) {
      if (ch === '/' && text[i + 1] === '/') {
        while (i < text.length && text[i] !== '\n') i++
        continue
      }
      if (ch === '/' && text[i + 1] === '*') {
        i += 2
        while (i < text.length && !(text[i] === '*' && text[i + 1] === '/')) i++
        i += 2
        continue
      }
    }
    result += ch; i++
  }
  return result
}

const typeColor = (type: McpServerType) => {
  switch (type) {
    case 'stdio': return 'info'
    case 'sse': return 'warning'
    case 'http': return 'success'
    default: return 'default'
  }
}

const typeIcon = (type: McpServerType) => {
  switch (type) {
    case 'stdio': return <TerminalIcon sx={{ fontSize: 16 }} />
    case 'sse': case 'http': return <HttpIcon sx={{ fontSize: 16 }} />
    default: return <TerminalIcon sx={{ fontSize: 16 }} />
  }
}

// ── 空表单 ──
const emptyServer = (): McpServerConfig => ({
  name: '',
  type: 'stdio',
  enabled: true,
  command: '',
  args: [],
  env: {},
  url: '',
  headers: {},
})

// ── KeyValueEditor ──
function KeyValueEditor({
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
          <TextField
            size="small"
            label={keyLabel}
            value={k}
            onChange={e => handleChange(k, 'key', e.target.value)}
            sx={{ flex: 1 }}
          />
          <TextField
            size="small"
            label={valueLabel}
            value={v}
            onChange={e => handleChange(k, 'value', e.target.value)}
            sx={{ flex: 2 }}
          />
          <IconButton size="small" onClick={() => handleRemove(k)}>
            <DeleteIcon fontSize="small" />
          </IconButton>
        </Box>
      ))}
      <Button size="small" startIcon={<AddIcon />} onClick={handleAdd}>
        {keyLabel}
      </Button>
    </Box>
  )
}

// ── ServerFormDialog ──
function ServerFormDialog({
  open,
  onClose,
  onSubmit,
  initial,
  title,
  submitLabel,
  t,
}: {
  open: boolean
  onClose: () => void
  onSubmit: (server: McpServerConfig) => void
  initial: McpServerConfig
  title: string
  submitLabel: string
  t: (key: string) => string
}) {
  const [form, setForm] = useState<McpServerConfig>(initial)

  useEffect(() => {
    if (open) setForm(initial)
  }, [open, initial])

  const handleSubmit = () => {
    if (!form.name.trim()) return
    onSubmit({
      ...form,
      args: form.args ?? [],
      env: form.env ?? {},
      headers: form.headers ?? {},
    })
  }

  return (
    <Dialog open={open} onClose={onClose} maxWidth="sm" fullWidth>
      <DialogTitle>{title}</DialogTitle>
      <DialogContent sx={{ pt: '12px !important' }}>
        <Stack spacing={2}>
          <TextField
            label={t('detail.mcp.form.name')}
            value={form.name}
            onChange={e => setForm(f => ({ ...f, name: e.target.value }))}
            size="small"
            fullWidth
            required
          />
          <Box sx={{ display: 'flex', gap: 1 }}>
            {(['stdio', 'sse', 'http'] as McpServerType[]).map(tp => (
              <Chip
                key={tp}
                label={tp.toUpperCase()}
                color={form.type === tp ? typeColor(tp) as 'info' | 'warning' | 'success' : 'default'}
                variant={form.type === tp ? 'filled' : 'outlined'}
                onClick={() => setForm(f => ({ ...f, type: tp }))}
                icon={typeIcon(tp)}
                size="small"
              />
            ))}
          </Box>
          {form.type === 'stdio' ? (
            <>
              <TextField
                label={t('detail.mcp.form.command')}
                value={form.command ?? ''}
                onChange={e => setForm(f => ({ ...f, command: e.target.value }))}
                size="small"
                fullWidth
                placeholder="npx / uvx / node / python"
              />
              <TextField
                label={t('detail.mcp.form.args')}
                value={(form.args ?? []).join(' ')}
                onChange={e => setForm(f => ({ ...f, args: e.target.value.split(' ').filter(Boolean) }))}
                size="small"
                fullWidth
                placeholder="-y @modelcontextprotocol/server-github"
                helperText={t('detail.mcp.form.argsHint')}
              />
              <Typography variant="caption" color="text.secondary">
                {t('detail.mcp.form.envLabel')}
              </Typography>
              <KeyValueEditor
                value={form.env ?? {}}
                onChange={env => setForm(f => ({ ...f, env }))}
                keyLabel="Key"
                valueLabel="Value"
              />
            </>
          ) : (
            <>
              <TextField
                label={t('detail.mcp.form.url')}
                value={form.url ?? ''}
                onChange={e => setForm(f => ({ ...f, url: e.target.value }))}
                size="small"
                fullWidth
                placeholder="https://your-mcp-server.example.com/mcp"
              />
              <Typography variant="caption" color="text.secondary">
                {t('detail.mcp.form.headersLabel')}
              </Typography>
              <KeyValueEditor
                value={form.headers ?? {}}
                onChange={headers => setForm(f => ({ ...f, headers }))}
                keyLabel="Header"
                valueLabel="Value"
              />
            </>
          )}
        </Stack>
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose}>{t('detail.mcp.form.cancel')}</Button>
        <Button
          variant="contained"
          onClick={handleSubmit}
          disabled={!form.name.trim()}
        >
          {submitLabel}
        </Button>
      </DialogActions>
    </Dialog>
  )
}

// ── RegistryDialog ──
function RegistryDialog({
  open,
  onClose,
  onSelect,
  t,
}: {
  open: boolean
  onClose: () => void
  onSelect: (item: McpRegistryItem) => void
  t: (key: string) => string
}) {
  const { data: registry, isLoading } = useQuery({
    queryKey: ['mcp-registry'],
    queryFn: () => mcpApi.getRegistry(),
    enabled: open,
  })
  const [search, setSearch] = useState('')

  const filtered = useMemo(
    () =>
      (registry ?? []).filter(
        item =>
          item.name.toLowerCase().includes(search.toLowerCase()) ||
          item.description.toLowerCase().includes(search.toLowerCase()) ||
          item.tags?.some(tag => tag.toLowerCase().includes(search.toLowerCase()))
      ),
    [registry, search]
  )

  return (
    <Dialog open={open} onClose={onClose} maxWidth="sm" fullWidth>
      <DialogTitle>{t('detail.mcp.registry.title')}</DialogTitle>
      <DialogContent sx={{ pt: '12px !important' }}>
        <TextField
          size="small"
          fullWidth
          placeholder={t('detail.mcp.registry.search')}
          value={search}
          onChange={e => setSearch(e.target.value)}
          sx={{ mb: 1 }}
          InputProps={{
            startAdornment: (
              <InputAdornment position="start">
                <SearchIcon fontSize="small" />
              </InputAdornment>
            ),
          }}
        />
        {isLoading ? (
          <Box sx={{ display: 'flex', justifyContent: 'center', py: 3 }}>
            <CircularProgress size={28} />
          </Box>
        ) : (
          <List disablePadding>
            {filtered.map(item => (
              <ListItem key={item.id} disablePadding>
                <ListItemButton onClick={() => onSelect(item)} sx={{ borderRadius: 1 }}>
                  <ListItemText
                    primary={
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                        <Typography variant="body2" fontWeight={600}>
                          {item.name}
                        </Typography>
                        <Chip label={item.type} size="small" variant="outlined" color={typeColor(item.type)} />
                        {item.tags?.map(tag => (
                          <Chip key={tag} label={tag} size="small" variant="outlined" sx={{ height: 20, fontSize: 11 }} />
                        ))}
                      </Box>
                    }
                    secondary={item.description}
                  />
                </ListItemButton>
              </ListItem>
            ))}
            {filtered.length === 0 && (
              <Typography variant="body2" color="text.secondary" sx={{ py: 2, textAlign: 'center' }}>
                {t('detail.mcp.registry.empty')}
              </Typography>
            )}
          </List>
        )}
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose}>{t('detail.mcp.form.cancel')}</Button>
      </DialogActions>
    </Dialog>
  )
}

// ── Main: MCPTab ──

export default function MCPTab({ workspace }: { workspace: WorkspaceDetail }) {
  const theme = useTheme()
  const notification = useNotification()
  const queryClient = useQueryClient()
  const { t } = useTranslation('workspace')

  // 视图模式: cards / json
  const [viewMode, setViewMode] = useState<'cards' | 'json'>('cards')

  // ── 卡片视图 state ──
  const { data: servers, isLoading: serversLoading } = useQuery({
    queryKey: ['workspace-mcp-servers', workspace.id],
    queryFn: () => workspaceApi.getMcpServers(workspace.id),
  })

  const [addOpen, setAddOpen] = useState(false)
  const [registryOpen, setRegistryOpen] = useState(false)
  const [editTarget, setEditTarget] = useState<McpServerConfig | null>(null)
  const [deleteTarget, setDeleteTarget] = useState<string | null>(null)
  const [mutating, setMutating] = useState(false)

  const invalidate = () => {
    queryClient.invalidateQueries({ queryKey: ['workspace-mcp-servers', workspace.id] })
    queryClient.invalidateQueries({ queryKey: ['workspace-mcp', workspace.id] })
    queryClient.invalidateQueries({ queryKey: ['workspace', workspace.id] })
  }

  const handleAdd = async (server: McpServerConfig) => {
    setMutating(true)
    try {
      await workspaceApi.addMcpServer(workspace.id, server)
      notification.success(t('detail.mcp.addSuccess'))
      setAddOpen(false)
      invalidate()
    } catch (e) {
      notification.error(t('detail.mcp.addFailed', { message: (e as Error).message }))
    } finally {
      setMutating(false)
    }
  }

  const handleEdit = async (server: McpServerConfig) => {
    if (!editTarget) return
    setMutating(true)
    try {
      await workspaceApi.updateMcpServer(workspace.id, editTarget.name, server)
      notification.success(t('detail.mcp.updateSuccess'))
      setEditTarget(null)
      invalidate()
    } catch (e) {
      notification.error(t('detail.mcp.updateFailed', { message: (e as Error).message }))
    } finally {
      setMutating(false)
    }
  }

  const handleDelete = async () => {
    if (!deleteTarget) return
    setMutating(true)
    try {
      await workspaceApi.deleteMcpServer(workspace.id, deleteTarget)
      notification.success(t('detail.mcp.deleteSuccess'))
      setDeleteTarget(null)
      invalidate()
    } catch (e) {
      notification.error(t('detail.mcp.deleteFailed', { message: (e as Error).message }))
    } finally {
      setMutating(false)
    }
  }

  const handleToggleEnabled = async (server: McpServerConfig) => {
    setMutating(true)
    try {
      await workspaceApi.updateMcpServer(workspace.id, server.name, {
        ...server,
        enabled: !server.enabled,
      })
      invalidate()
    } catch (e) {
      notification.error((e as Error).message)
    } finally {
      setMutating(false)
    }
  }

  const handleRegistrySelect = (item: McpRegistryItem) => {
    setRegistryOpen(false)
    const envFromKeys: Record<string, string> = {}
    item.env_keys?.forEach(k => { envFromKeys[k.key] = '' })
    setEditTarget(null)
    // 预填充表单并打开添加对话框
    setAddOpen(true)
    setRegistryPrefill({
      name: item.id,
      type: item.type,
      enabled: true,
      command: item.command ?? '',
      args: item.args ?? [],
      env: envFromKeys,
      url: item.url ?? '',
      headers: {},
    })
  }

  const [registryPrefill, setRegistryPrefill] = useState<McpServerConfig | null>(null)

  // ── JSON 视图 state ──
  const [mcpText, setMcpText] = useState('')
  const [mcpError, setMcpError] = useState<string | null>(null)
  const [savingMcp, setSavingMcp] = useState(false)

  const { data: mcpData } = useQuery({
    queryKey: ['workspace-mcp', workspace.id],
    queryFn: () => workspaceApi.getMcpConfig(workspace.id),
  })

  useEffect(() => {
    if (mcpData !== undefined) setMcpText(JSON.stringify(mcpData, null, 2))
  }, [mcpData])

  const validateMcpText = (v: string): string | null => {
    try {
      JSON.parse(stripJsoncComments(v))
      return null
    } catch {
      return t('detail.mcp.jsonError')
    }
  }

  const handleMcpChange = (v: string) => {
    setMcpText(v)
    setMcpError(validateMcpText(v))
  }

  const handleSaveMcp = async () => {
    const err = validateMcpText(mcpText)
    if (err) {
      notification.warning(t('detail.mcp.jsonErrorFix'))
      return
    }
    setSavingMcp(true)
    try {
      await workspaceApi.updateMcpConfig(workspace.id, JSON.parse(stripJsoncComments(mcpText)))
      notification.success(t('detail.mcp.saveSuccess'))
      invalidate()
    } catch (e) {
      notification.error(t('detail.mcp.saveFailed', { message: (e as Error).message }))
    } finally {
      setSavingMcp(false)
    }
  }

  return (
    <Stack spacing={2}>
      {/* 标题栏 */}
      <Card sx={CARD_VARIANTS.default.styles}>
        <CardContent sx={{ py: 1.5, '&:last-child': { pb: 1.5 } }}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <Typography variant="subtitle2" sx={{ fontWeight: 600, flexGrow: 1 }}>
              {t('detail.mcp.title')}
            </Typography>
            {viewMode === 'cards' && (
              <>
                <Button
                  size="small"
                  variant="outlined"
                  startIcon={<AddIcon />}
                  onClick={() => setRegistryOpen(true)}
                >
                  {t('detail.mcp.fromTemplate')}
                </Button>
                <Button
                  size="small"
                  variant="contained"
                  startIcon={<AddIcon />}
                  onClick={() => {
                    setRegistryPrefill(null)
                    setAddOpen(true)
                  }}
                >
                  {t('detail.mcp.addManual')}
                </Button>
              </>
            )}
            {viewMode === 'json' && (
              <Button
                size="small"
                variant="contained"
                startIcon={savingMcp ? <CircularProgress size={14} color="inherit" /> : <SaveIcon />}
                onClick={handleSaveMcp}
                disabled={savingMcp || !!mcpError}
              >
                {t('detail.mcp.save')}
              </Button>
            )}
            <Tooltip title={viewMode === 'cards' ? t('detail.mcp.switchToJson') : t('detail.mcp.switchToCards')}>
              <IconButton
                size="small"
                onClick={() => setViewMode(v => (v === 'cards' ? 'json' : 'cards'))}
                sx={{
                  border: '1px solid',
                  borderColor: 'divider',
                  borderRadius: 1,
                }}
              >
                {viewMode === 'cards' ? <CodeIcon fontSize="small" /> : <ViewModuleIcon fontSize="small" />}
              </IconButton>
            </Tooltip>
          </Box>
        </CardContent>
      </Card>

      {/* 卡片视图 */}
      {viewMode === 'cards' && (
        <>
          {serversLoading ? (
            <Box sx={{ display: 'flex', justifyContent: 'center', py: 4 }}>
              <CircularProgress size={28} />
            </Box>
          ) : !servers || servers.length === 0 ? (
            <Card sx={CARD_VARIANTS.default.styles}>
              <CardContent>
                <Box sx={{ textAlign: 'center', py: 4 }}>
                  <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                    {t('detail.mcp.empty')}
                  </Typography>
                  <Button
                    variant="outlined"
                    startIcon={<AddIcon />}
                    onClick={() => setRegistryOpen(true)}
                  >
                    {t('detail.mcp.fromTemplate')}
                  </Button>
                </Box>
              </CardContent>
            </Card>
          ) : (
            <Box sx={{ display: 'flex', gap: 2, flexWrap: 'wrap' }}>
              {servers.map(server => (
                <Card
                  key={server.name}
                  sx={{
                    ...CARD_VARIANTS.default.styles,
                    width: 280,
                    position: 'relative',
                    opacity: server.enabled ? 1 : 0.6,
                    transition: 'all 0.2s ease',
                  }}
                >
                  <CardContent sx={{ pb: '12px !important' }}>
                    <Box sx={{ display: 'flex', alignItems: 'center', mb: 1, gap: 1 }}>
                      <Box
                        sx={{
                          width: 8,
                          height: 8,
                          borderRadius: '50%',
                          bgcolor: server.enabled ? 'success.main' : 'text.disabled',
                          flexShrink: 0,
                        }}
                      />
                      <Typography variant="subtitle2" sx={{ fontWeight: 600, flexGrow: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                        {server.name}
                      </Typography>
                      <Chip
                        label={server.type.toUpperCase()}
                        size="small"
                        color={typeColor(server.type) as 'info' | 'warning' | 'success'}
                        variant="outlined"
                        sx={{ height: 20, fontSize: 11 }}
                      />
                    </Box>
                    <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mb: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                      {server.type === 'stdio'
                        ? `${server.command ?? ''} ${(server.args ?? []).join(' ')}`
                        : server.url ?? ''}
                    </Typography>
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                      <Tooltip title={server.enabled ? t('detail.mcp.disable') : t('detail.mcp.enable')}>
                        <Switch
                          size="small"
                          checked={server.enabled}
                          onChange={() => handleToggleEnabled(server)}
                          disabled={mutating}
                        />
                      </Tooltip>
                      <Box sx={{ flexGrow: 1 }} />
                      <Tooltip title={t('detail.mcp.edit')}>
                        <IconButton
                          size="small"
                          onClick={() => setEditTarget(server)}
                          sx={{
                            '&:hover': { bgcolor: alpha(theme.palette.primary.main, 0.1) },
                          }}
                        >
                          <EditIcon fontSize="small" />
                        </IconButton>
                      </Tooltip>
                      <Tooltip title={t('detail.mcp.delete')}>
                        <IconButton
                          size="small"
                          onClick={() => setDeleteTarget(server.name)}
                          sx={{
                            '&:hover': { bgcolor: alpha(theme.palette.error.main, 0.1) },
                          }}
                        >
                          <DeleteIcon fontSize="small" />
                        </IconButton>
                      </Tooltip>
                    </Box>
                  </CardContent>
                </Card>
              ))}
            </Box>
          )}
        </>
      )}

      {/* JSON 视图 */}
      {viewMode === 'json' && (
        <Card sx={CARD_VARIANTS.default.styles}>
          <CardContent>
            {mcpError && <Alert severity="error" sx={{ mb: 1, py: 0 }}>{mcpError}</Alert>}
            <Box
              sx={{
                border: '1px solid',
                borderColor: mcpError ? 'error.main' : 'divider',
                borderRadius: 1,
                overflow: 'hidden',
              }}
            >
              <Editor
                height="400px"
                language="jsonc"
                value={mcpText}
                onChange={v => handleMcpChange(v ?? '')}
                theme={theme.palette.mode === 'dark' ? 'vs-dark' : 'vs'}
                options={{
                  minimap: { enabled: false },
                  fontSize: 13,
                  lineNumbers: 'on',
                  wordWrap: 'off',
                  scrollBeyondLastLine: false,
                  renderLineHighlight: 'none',
                  tabSize: 2,
                  folding: true,
                  formatOnPaste: true,
                }}
              />
            </Box>
            <Typography variant="caption" color="text.secondary" sx={{ mt: 0.5, display: 'block' }}>
              {t('detail.mcp.jsonHint')}
            </Typography>
          </CardContent>
        </Card>
      )}

      {/* 添加服务器对话框 */}
      <ServerFormDialog
        open={addOpen}
        onClose={() => { setAddOpen(false); setRegistryPrefill(null) }}
        onSubmit={handleAdd}
        initial={registryPrefill ?? emptyServer()}
        title={t('detail.mcp.addTitle')}
        submitLabel={mutating ? t('detail.mcp.adding') : t('detail.mcp.add')}
        t={t}
      />

      {/* 编辑服务器对话框 */}
      <ServerFormDialog
        open={!!editTarget}
        onClose={() => setEditTarget(null)}
        onSubmit={handleEdit}
        initial={editTarget ?? emptyServer()}
        title={t('detail.mcp.editTitle')}
        submitLabel={mutating ? t('detail.mcp.saving') : t('detail.mcp.save')}
        t={t}
      />

      {/* 注册表对话框 */}
      <RegistryDialog
        open={registryOpen}
        onClose={() => setRegistryOpen(false)}
        onSelect={handleRegistrySelect}
        t={t}
      />

      {/* 删除确认对话框 */}
      <Dialog open={!!deleteTarget} onClose={() => setDeleteTarget(null)} maxWidth="xs">
        <DialogTitle>{t('detail.mcp.deleteTitle')}</DialogTitle>
        <DialogContent>
          <Typography variant="body2">
            {t('detail.mcp.deleteConfirm', { name: deleteTarget ?? '' })}
          </Typography>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDeleteTarget(null)}>{t('detail.mcp.form.cancel')}</Button>
          <Button
            variant="contained"
            color="error"
            onClick={handleDelete}
            disabled={mutating}
          >
            {mutating ? <CircularProgress size={20} /> : t('detail.mcp.delete')}
          </Button>
        </DialogActions>
      </Dialog>
    </Stack>
  )
}
