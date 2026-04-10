import { useState, useMemo } from 'react'
import { useTheme } from '@mui/material/styles'
import {
  Box,
  Tooltip,
} from '@mui/material'
import {
  Http as HttpIcon,
  Terminal as TerminalIcon,
  Refresh as RefreshIcon,
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
import SegmentedControl from '../../components/common/SegmentedControl'
import SearchField from '../../components/common/SearchField'
import IconActionButton from '../../components/common/IconActionButton'
import StatCard from '../../components/common/StatCard'

type FilterType = 'all' | McpServerType

// ─── Main Page ──────────────────────────────────────────────

export default function McpServicesPage() {
  const notification = useNotification()
  const queryClient = useQueryClient()
  const { t } = useTranslation('workspace')
  const theme = useTheme()

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
        <StatCard label={t('mcpServices.stats.total')} value={stats.total} icon={<AutoInjectIcon sx={{ fontSize: 20 }} />} color={theme.palette.primary.main} />
        <StatCard label={t('mcpServices.stats.stdio')} value={stats.stdio} icon={<TerminalIcon sx={{ fontSize: 20 }} />} color={theme.palette.info.main} />
        <StatCard label={t('mcpServices.stats.sse')} value={stats.sse} icon={<HttpIcon sx={{ fontSize: 20 }} />} color={theme.palette.warning.main} />
        <StatCard label={t('mcpServices.stats.http')} value={stats.http} icon={<HttpIcon sx={{ fontSize: 20 }} />} color={theme.palette.success.main} />
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
        title=""
        emptyText={hasActiveFilters ? t('mcpServices.empty.noMatch') : t('mcpServices.empty.title')}
        emptyHint={hasActiveFilters ? undefined : t('mcpServices.empty.hint')}
        jsonTitle={t('mcpServices.toolbar.jsonViewTitle')}
        jsonHint={t('mcpServices.toolbar.jsonViewHint')}
        deleteTitle={t('mcpServices.deleteDialog.title')}
        deleteContent={name => t('mcpServices.deleteDialog.content', { name })}
        toolbarFilters={
          <>
            <SearchField
              placeholder={t('mcpServices.search.placeholder')}
              value={search}
              onChange={setSearch}
              onClear={() => setSearch('')}
              sx={{ width: { xs: '100%', sm: 280, md: 320 }, maxWidth: '100%', flexShrink: 0 }}
            />
            <SegmentedControl
              value={filter}
              options={[
                { value: 'all', label: t('mcpServices.filter.all') },
                { value: 'stdio', label: t('mcpServices.filter.stdio') },
                { value: 'sse', label: t('mcpServices.filter.sse') },
                { value: 'http', label: t('mcpServices.filter.http') },
              ]}
              onChange={v => setFilter(v)}
            />
            {hasActiveFilters && (
              <Tooltip title={t('mcpServices.toolbar.clearFilters')}>
                <IconActionButton size="small" onClick={() => { setSearch(''); setFilter('all') }}>
                  <FilterAltOffIcon fontSize="small" />
                </IconActionButton>
              </Tooltip>
            )}
          </>
        }
        toolbarActions={
          <>
            <Tooltip title={t('mcpServices.toolbar.refresh')}>
              <IconActionButton tone="primary" onClick={() => invalidate()} disabled={isLoading} size="small">
                <RefreshIcon fontSize="small" />
              </IconActionButton>
            </Tooltip>
            <Tooltip title={t('mcpServices.pageDesc')} arrow>
              <IconActionButton size="small">
                <HelpIcon fontSize="small" />
              </IconActionButton>
            </Tooltip>
          </>
        }
        t={t}
      />
    </Box>
  )
}
