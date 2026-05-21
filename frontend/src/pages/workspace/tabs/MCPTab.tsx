import { useMemo, useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import {
  Box,
  Card,
  Chip,
  CircularProgress,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  List,
  ListItem,
  ListItemButton,
  ListItemText,
  Stack,
  Tooltip,
  Typography,
} from '@mui/material'
import {
  Terminal as TerminalIcon,
  Http as HttpIcon,
  CheckCircle as CheckCircleIcon,
  ErrorOutline as ErrorOutlineIcon,
  PlayArrow as PlayArrowIcon,
  AutoAwesome as AutoInjectIcon,
  SyncOutlined as SyncIcon,
  OpenInNew as OpenInNewIcon,
  Add as AddIcon,
  RemoveCircleOutline as RemoveIcon,
} from '@mui/icons-material'
import { useTranslation } from 'react-i18next'
import { Link as RouterLink } from 'react-router-dom'
import {
  workspaceApi,
  type WorkspaceDetail,
  type McpServerConfig,
  type McpServerType,
  type McpValidationResult,
} from '../../../services/api/workspace'
import { useNotification } from '../../../hooks/useNotification'
import { CARD_VARIANTS } from '../../../theme/variants'
import ActionButton from '../../../components/common/ActionButton'
import IconActionButton from '../../../components/common/IconActionButton'

const typeColor = (type: McpServerType) =>
  type === 'stdio' ? 'info' : type === 'sse' ? 'warning' : 'success'
const typeIcon = (type: McpServerType) =>
  type === 'stdio'
    ? <TerminalIcon sx={{ fontSize: 16 }} />
    : <HttpIcon sx={{ fontSize: 16 }} />

export default function MCPTab({ workspace }: { workspace: WorkspaceDetail }) {
  const notification = useNotification()
  const queryClient = useQueryClient()
  const { t } = useTranslation('workspace')

  const { data: servers = [], isLoading } = useQuery({
    queryKey: ['workspace-mcp-servers', workspace.id],
    queryFn: () => workspaceApi.getMcpServers(workspace.id),
  })

  const [addOpen, setAddOpen] = useState(false)
  const [removingName, setRemovingName] = useState<string | null>(null)
  const [addingName, setAddingName] = useState<string | null>(null)
  const [validationStates, setValidationStates] = useState<
    Record<string, 'pending' | McpValidationResult>
  >({})

  const { data: available = [], isLoading: availableLoading } = useQuery({
    queryKey: ['workspace-mcp-available', workspace.id],
    queryFn: () => workspaceApi.getAvailableMcpServers(workspace.id),
    enabled: addOpen,
  })

  const invalidate = () => {
    queryClient.invalidateQueries({ queryKey: ['workspace-mcp-servers', workspace.id] })
    queryClient.invalidateQueries({ queryKey: ['workspace-mcp-available', workspace.id] })
    queryClient.invalidateQueries({ queryKey: ['workspace', workspace.id] })
  }

  const handleAdd = async (server: McpServerConfig) => {
    setAddingName(server.name)
    try {
      await workspaceApi.addMcpServerToWorkspace(workspace.id, server.name)
      notification.success(t('detail.mcp.addSuccess'))
      invalidate()
    } catch (e) {
      notification.error(t('detail.mcp.addFailed', { message: (e as Error).message }))
    } finally {
      setAddingName(null)
    }
  }

  const handleRemove = async (server: McpServerConfig) => {
    setRemovingName(server.name)
    try {
      await workspaceApi.removeMcpServerFromWorkspace(workspace.id, server.name)
      notification.success(t('detail.mcp.removeSuccess', { name: server.name }))
      invalidate()
    } catch (e) {
      notification.error(t('detail.mcp.removeFailed', { message: (e as Error).message }))
    } finally {
      setRemovingName(null)
    }
  }

  const handleValidate = async (server: McpServerConfig) => {
    setValidationStates(prev => ({ ...prev, [server.name]: 'pending' }))
    try {
      const result = await workspaceApi.testMcpServer(workspace.id, server.name)
      setValidationStates(prev => ({ ...prev, [server.name]: result }))
      invalidate()
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

  const handleSyncToSandbox = async () => {
    try {
      await workspaceApi.syncMcpToSandbox(workspace.id)
      notification.success(t('detail.mcp.syncSuccess'))
    } catch (e) {
      notification.error(t('detail.mcp.syncFailed', { message: (e as Error).message }))
    }
  }

  const stats = useMemo(() => ({
    total: servers.length,
    validated: servers.filter(s => s.validation?.status === 'validated').length,
  }), [servers])

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

  const renderValidateBtn = (server: McpServerConfig) => {
    const state = validationStates[server.name]
    const pending = state === 'pending'
    const result = state && state !== 'pending' ? (state as McpValidationResult) : null
    let color: 'inherit' | 'success' | 'error' = 'inherit'
    let icon: React.ReactNode = <PlayArrowIcon sx={{ fontSize: 16 }} />
    if (pending) icon = <CircularProgress size={14} />
    else if (result?.ok) { color = 'success'; icon = <CheckCircleIcon sx={{ fontSize: 16 }} /> }
    else if (result && !result.ok) { color = 'error'; icon = <ErrorOutlineIcon sx={{ fontSize: 16 }} /> }
    const tooltip = pending
      ? t('mcpServices.validate.pending')
      : result?.ok
        ? `${t('mcpServices.validate.success', { name: result.server_info?.name ?? '-', version: result.server_info?.version ?? '-' })} (${(result.tools ?? []).length} tools, ${Math.round(result.latency_ms)}ms)`
        : result
          ? t(`mcpServices.validate.errorKind.${result.error_kind ?? 'transport_error'}`) + (result.error ? ` — ${result.error}` : '')
          : t('mcpServices.validate.button')
    return (
      <Tooltip title={tooltip} arrow>
        <span>
          <IconActionButton size="small" color={color} onClick={() => handleValidate(server)} disabled={pending}>
            {icon}
          </IconActionButton>
        </span>
      </Tooltip>
    )
  }

  return (
    <Stack spacing={2} sx={{ p: { xs: 1.5, sm: 2 } }}>
      {/* Header / Toolbar */}
      <Card sx={CARD_VARIANTS.default.styles}>
        <Box sx={{ px: 2, py: 1.5, display: 'flex', alignItems: 'center', gap: 1.5, flexWrap: 'wrap' }}>
          <Box>
            <Typography variant="subtitle1" sx={{ fontWeight: 600 }}>{t('detail.mcp.title')}</Typography>
            <Typography variant="caption" color="text.secondary">
              {t('detail.mcp.workspaceHint', {
                total: stats.total,
                validated: stats.validated,
              })}
            </Typography>
          </Box>
          <Box sx={{ ml: 'auto', display: 'flex', alignItems: 'center', gap: 1 }}>
            <ActionButton
              size="small"
              variant="contained"
              startIcon={<AddIcon />}
              onClick={() => setAddOpen(true)}
            >
              {t('detail.mcp.addBtn')}
            </ActionButton>
            <ActionButton
              size="small"
              variant="outlined"
              startIcon={<SyncIcon />}
              onClick={handleSyncToSandbox}
            >
              {t('detail.mcp.syncToSandbox')}
            </ActionButton>
            <ActionButton
              size="small"
              variant="outlined"
              component={RouterLink}
              to="/workspace/mcp-services"
              endIcon={<OpenInNewIcon />}
            >
              {t('detail.mcp.manageLibrary')}
            </ActionButton>
          </Box>
        </Box>
      </Card>

      {/* Server list */}
      {isLoading ? (
        <Box sx={{ display: 'flex', justifyContent: 'center', py: 4 }}><CircularProgress size={28} /></Box>
      ) : servers.length === 0 ? (
        <Card sx={CARD_VARIANTS.default.styles}>
          <Box sx={{ textAlign: 'center', py: 4, px: 2 }}>
            <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
              {t('detail.mcp.empty')}
            </Typography>
            <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
              {t('detail.mcp.emptyHint')}
            </Typography>
            <ActionButton variant="contained" startIcon={<AddIcon />} onClick={() => setAddOpen(true)}>
              {t('detail.mcp.addBtn')}
            </ActionButton>
          </Box>
        </Card>
      ) : (
        <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', sm: 'repeat(auto-fill, minmax(320px, 1fr))' }, gap: 2 }}>
          {servers.map(server => (
            <Card key={server.name} sx={{ ...CARD_VARIANTS.default.styles, display: 'flex', flexDirection: 'column' }}>
              <Box sx={{ p: 2, flex: 1, display: 'flex', flexDirection: 'column', gap: 1 }}>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.75, flexWrap: 'wrap' }}>
                  <Chip
                    label={server.type.toUpperCase()}
                    size="small"
                    color={typeColor(server.type)}
                    variant="outlined"
                    icon={typeIcon(server.type)}
                    sx={{ fontSize: '0.7rem', height: 22 }}
                  />
                  {server.auto_inject && (
                    <Tooltip title={t('detail.mcp.autoInjectTooltip')} arrow>
                      <Chip
                        icon={<AutoInjectIcon sx={{ fontSize: 12 }} />}
                        label={t('mcpServices.toolbar.autoInject')}
                        size="small"
                        sx={{
                          fontSize: '0.65rem',
                          height: 20,
                          bgcolor: 'warning.main',
                          color: 'warning.contrastText',
                          fontWeight: 600,
                          '& .MuiChip-icon': { color: 'warning.contrastText', ml: 0.5 },
                        }}
                      />
                    </Tooltip>
                  )}
                  {renderValidationChip(server)}
                </Box>
                <Typography variant="subtitle1" sx={{ fontWeight: 600, lineHeight: 1.3 }}>
                  {server.name}
                </Typography>
                <Typography
                  variant="body2"
                  color="text.secondary"
                  sx={{
                    display: '-webkit-box',
                    WebkitLineClamp: 2,
                    WebkitBoxOrient: 'vertical',
                    overflow: 'hidden',
                    lineHeight: 1.5,
                    fontFamily: 'monospace',
                    fontSize: '0.75rem',
                  }}
                >
                  {server.type === 'stdio'
                    ? `${server.command ?? ''} ${(server.args ?? []).join(' ')}`
                    : server.url ?? ''}
                </Typography>
              </Box>
              <Box
                sx={{
                  px: 2,
                  py: 1,
                  borderTop: '1px solid',
                  borderColor: 'divider',
                  display: 'flex',
                  alignItems: 'center',
                  gap: 0.5,
                }}
              >
                <Box sx={{ flexGrow: 1 }} />
                {renderValidateBtn(server)}
                <Tooltip title={t('detail.mcp.removeTooltip')} arrow>
                  <span>
                    <IconActionButton
                      size="small"
                      color="error"
                      onClick={() => handleRemove(server)}
                      disabled={removingName === server.name}
                    >
                      {removingName === server.name ? <CircularProgress size={14} /> : <RemoveIcon sx={{ fontSize: 18 }} />}
                    </IconActionButton>
                  </span>
                </Tooltip>
              </Box>
            </Card>
          ))}
        </Box>
      )}

      {/* Add dialog */}
      <Dialog open={addOpen} onClose={() => setAddOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>{t('detail.mcp.addDialog.title')}</DialogTitle>
        <DialogContent dividers sx={{ p: 0 }}>
          {availableLoading ? (
            <Box sx={{ display: 'flex', justifyContent: 'center', py: 4 }}><CircularProgress size={28} /></Box>
          ) : available.length === 0 ? (
            <Box sx={{ p: 3, textAlign: 'center' }}>
              <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
                {t('detail.mcp.addDialog.empty')}
              </Typography>
              <ActionButton size="small" component={RouterLink} to="/workspace/mcp-services" endIcon={<OpenInNewIcon />}>
                {t('detail.mcp.manageLibrary')}
              </ActionButton>
            </Box>
          ) : (
            <List disablePadding>
              {available.map(server => (
                <ListItem key={server.name} disablePadding>
                  <ListItemButton
                    onClick={() => handleAdd(server)}
                    disabled={addingName === server.name}
                  >
                    <ListItemText
                      primary={
                        <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.75 }}>
                          <Typography variant="body2" fontWeight={600}>{server.name}</Typography>
                          <Chip label={server.type.toUpperCase()} size="small" color={typeColor(server.type)} variant="outlined" sx={{ height: 18, fontSize: 10 }} />
                          {server.auto_inject && (
                            <Chip
                              icon={<AutoInjectIcon sx={{ fontSize: 11 }} />}
                              label={t('mcpServices.toolbar.autoInject')}
                              size="small"
                              sx={{
                                height: 18,
                                fontSize: 10,
                                bgcolor: 'warning.main',
                                color: 'warning.contrastText',
                                fontWeight: 600,
                                '& .MuiChip-icon': { color: 'warning.contrastText', ml: 0.5 },
                              }}
                            />
                          )}
                          {server.validation?.status === 'validated' && (
                            <CheckCircleIcon sx={{ fontSize: 14, color: 'success.main' }} />
                          )}
                        </Box>
                      }
                      secondary={
                        <Typography variant="caption" color="text.secondary" sx={{ fontFamily: 'monospace', wordBreak: 'break-all' }}>
                          {server.type === 'stdio'
                            ? `${server.command ?? ''} ${(server.args ?? []).join(' ')}`
                            : server.url ?? ''}
                        </Typography>
                      }
                    />
                    {addingName === server.name && <CircularProgress size={16} sx={{ ml: 1 }} />}
                  </ListItemButton>
                </ListItem>
              ))}
            </List>
          )}
        </DialogContent>
        <DialogActions>
          <ActionButton onClick={() => setAddOpen(false)}>{t('detail.mcp.form.cancel')}</ActionButton>
        </DialogActions>
      </Dialog>
    </Stack>
  )
}
