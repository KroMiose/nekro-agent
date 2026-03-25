import { useState, useMemo } from 'react'
import {
  Box,
  Typography,
  TextField,
  InputAdornment,
  ToggleButtonGroup,
  ToggleButton,
  IconButton,
  Tooltip,
  Paper,
  useMediaQuery,
} from '@mui/material'
import { useTheme } from '@mui/material/styles'
import {
  Search as SearchIcon,
  Http as HttpIcon,
  Terminal as TerminalIcon,
  Refresh as RefreshIcon,
  Close as CloseIcon,
  FilterAltOff as FilterAltOffIcon,
  HelpOutline as HelpIcon,
  AutoAwesome as AutoInjectIcon,
} from '@mui/icons-material'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { useTranslation } from 'react-i18next'
import {
  mcpApi,
  type McpServerConfig,
  type McpServerType,
} from '../../services/api/workspace'
import { useNotification } from '../../hooks/useNotification'
import { UNIFIED_TABLE_STYLES } from '../../theme/variants'
import { McpServerManager } from './components/McpShared'

type FilterType = 'all' | McpServerType

// ─── Stat Card ──────────────────────────────────────────────

function StatCard({ label, value, icon, color }: { label: string; value: number; icon: React.ReactNode; color: string }) {
  return (
    <Paper variant="outlined" sx={{ px: 2, py: 1.5, display: 'flex', alignItems: 'center', gap: 1.5, borderRadius: 2, minWidth: 140, flex: '1 1 0' }}>
      <Box sx={{ width: 36, height: 36, borderRadius: 1.5, display: 'flex', alignItems: 'center', justifyContent: 'center', bgcolor: color, color: '#fff', flexShrink: 0 }}>
        {icon}
      </Box>
      <Box>
        <Typography variant="h6" sx={{ fontWeight: 700, lineHeight: 1.2 }}>{value}</Typography>
        <Typography variant="caption" color="text.secondary">{label}</Typography>
      </Box>
    </Paper>
  )
}

// ─── Main Page ──────────────────────────────────────────────

export default function McpServicesPage() {
  const theme = useTheme()
  const notification = useNotification()
  const queryClient = useQueryClient()
  const { t } = useTranslation('workspace')
  const isMobile = useMediaQuery(theme.breakpoints.down('md'))

  // ── Data ──
  const { data: servers = [], isLoading } = useQuery({
    queryKey: ['mcp-auto-inject'],
    queryFn: () => mcpApi.getAutoInject(),
  })

  // ── Search & Filter ──
  const [search, setSearch] = useState('')
  const [filter, setFilter] = useState<FilterType>('all')
  const hasActiveFilters = search.trim() !== '' || filter !== 'all'

  const filtered = useMemo(() => {
    let list = servers
    if (filter !== 'all') list = list.filter(s => s.type === filter)
    if (search.trim()) {
      const q = search.toLowerCase()
      list = list.filter(s => s.name.toLowerCase().includes(q) || (s.command ?? '').toLowerCase().includes(q) || (s.url ?? '').toLowerCase().includes(q))
    }
    return list
  }, [servers, filter, search])

  // ── Stats ──
  const stats = useMemo(() => ({
    total: servers.length,
    stdio: servers.filter(s => s.type === 'stdio').length,
    sse: servers.filter(s => s.type === 'sse').length,
    http: servers.filter(s => s.type === 'http').length,
  }), [servers])

  const invalidate = () => { queryClient.invalidateQueries({ queryKey: ['mcp-auto-inject'] }) }

  // ── Operations ──
  const updateList = async (updater: (current: McpServerConfig[]) => McpServerConfig[]) => {
    await mcpApi.setAutoInject(updater(servers))
    invalidate()
  }

  const handleAdd = async (server: McpServerConfig) => {
    try {
      await updateList(current => [...current, server])
      notification.success(t('mcpServices.notifications.addSuccess'))
    } catch (e) {
      notification.error(t('mcpServices.notifications.addFailed', { message: (e as Error).message }))
      throw e
    }
  }

  const handleEdit = async (oldName: string, server: McpServerConfig) => {
    try {
      await updateList(current => current.map(s => s.name === oldName ? server : s))
      notification.success(t('mcpServices.notifications.updateSuccess'))
    } catch (e) {
      notification.error(t('mcpServices.notifications.updateFailed', { message: (e as Error).message }))
      throw e
    }
  }

  const handleDelete = async (name: string) => {
    try {
      await updateList(current => current.filter(s => s.name !== name))
      notification.success(t('mcpServices.notifications.deleteSuccess'))
    } catch (e) {
      notification.error(t('mcpServices.notifications.deleteFailed', { message: (e as Error).message }))
      throw e
    }
  }

  const handleToggleEnabled = async (server: McpServerConfig) => {
    try {
      await updateList(current => current.map(s => s.name === server.name ? { ...s, enabled: !s.enabled } : s))
    } catch (e) {
      notification.error((e as Error).message)
      throw e
    }
  }

  const handleImport = async (newServers: McpServerConfig[]) => {
    const existingNames = new Set(servers.map(s => s.name))
    const toAdd = newServers.filter(s => !existingNames.has(s.name))
    await mcpApi.setAutoInject([...servers, ...toAdd])
    invalidate()
    const skipped = newServers.length - toAdd.length
    notification.success(
      skipped > 0
        ? t('mcpServices.import.successWithSkip', { count: toAdd.length, skipped })
        : t('mcpServices.import.success', { count: toAdd.length })
    )
  }

  return (
    <Box sx={{ ...UNIFIED_TABLE_STYLES.tableLayoutContainer, p: 3 }}>
      {/* Stat cards */}
      <Box sx={{ display: 'flex', gap: 2, mb: 3, flexWrap: 'wrap', flexShrink: 0 }}>
        <StatCard label={t('mcpServices.stats.total')} value={stats.total} icon={<AutoInjectIcon sx={{ fontSize: 20 }} />} color="#5c6bc0" />
        <StatCard label={t('mcpServices.stats.stdio')} value={stats.stdio} icon={<TerminalIcon sx={{ fontSize: 20 }} />} color="#0288d1" />
        <StatCard label={t('mcpServices.stats.sse')} value={stats.sse} icon={<HttpIcon sx={{ fontSize: 20 }} />} color="#ed6c02" />
        <StatCard label={t('mcpServices.stats.http')} value={stats.http} icon={<HttpIcon sx={{ fontSize: 20 }} />} color="#2e7d32" />
      </Box>

      {/* Search & filter toolbar */}
      <Box sx={{ mb: 2, flexShrink: 0 }}>
        <Box sx={{ display: 'flex', flexDirection: isMobile ? 'column' : 'row', gap: 1.25, alignItems: isMobile ? 'stretch' : 'center', flexWrap: 'wrap' }}>
          <TextField
            size="small"
            placeholder={t('mcpServices.search.placeholder')}
            value={search}
            onChange={e => setSearch(e.target.value)}
            sx={{ width: { xs: '100%', sm: 280, md: 320 }, maxWidth: '100%', flexShrink: 0 }}
            InputProps={{
              startAdornment: <InputAdornment position="start"><SearchIcon fontSize="small" /></InputAdornment>,
              endAdornment: search ? <InputAdornment position="end"><IconButton size="small" onClick={() => setSearch('')}><CloseIcon sx={{ fontSize: 16 }} /></IconButton></InputAdornment> : undefined,
            }}
          />
          <ToggleButtonGroup value={filter} exclusive onChange={(_, v: FilterType | null) => { if (v !== null) setFilter(v) }} size="small">
            <ToggleButton value="all" sx={{ px: 1.5, py: 0.5, fontSize: '0.8rem' }}>{t('mcpServices.filter.all')}</ToggleButton>
            <ToggleButton value="stdio" sx={{ px: 1.5, py: 0.5, fontSize: '0.8rem' }}>{t('mcpServices.filter.stdio')}</ToggleButton>
            <ToggleButton value="sse" sx={{ px: 1.5, py: 0.5, fontSize: '0.8rem' }}>{t('mcpServices.filter.sse')}</ToggleButton>
            <ToggleButton value="http" sx={{ px: 1.5, py: 0.5, fontSize: '0.8rem' }}>{t('mcpServices.filter.http')}</ToggleButton>
          </ToggleButtonGroup>
          {hasActiveFilters && (
            <Tooltip title={t('mcpServices.toolbar.clearFilters')}>
              <IconButton size="small" onClick={() => { setSearch(''); setFilter('all') }}><FilterAltOffIcon fontSize="small" /></IconButton>
            </Tooltip>
          )}
          <Box sx={{ flexGrow: 1 }} />
          <Tooltip title={t('mcpServices.toolbar.refresh')}>
            <IconButton onClick={() => invalidate()} disabled={isLoading} size="small"><RefreshIcon fontSize="small" /></IconButton>
          </Tooltip>
          <Tooltip title={t('mcpServices.pageDesc')} arrow>
            <IconButton size="small" sx={{ color: 'text.disabled' }}><HelpIcon fontSize="small" /></IconButton>
          </Tooltip>
        </Box>
      </Box>

      {/* Server manager (card/list/json + dialogs) */}
      <McpServerManager
        servers={filtered}
        loading={isLoading}
        onAdd={handleAdd}
        onEdit={handleEdit}
        onDelete={handleDelete}
        onToggleEnabled={handleToggleEnabled}
        onImport={handleImport}
        cardVariant="global"
        emptyText={hasActiveFilters ? t('mcpServices.empty.noMatch') : t('mcpServices.empty.title')}
        emptyHint={hasActiveFilters ? undefined : t('mcpServices.empty.hint')}
        jsonTitle={t('mcpServices.toolbar.jsonViewTitle')}
        jsonHint={t('mcpServices.toolbar.jsonViewHint')}
        deleteTitle={t('mcpServices.deleteDialog.title')}
        deleteContent={name => t('mcpServices.deleteDialog.content', { name })}
        t={t}
      />
    </Box>
  )
}
