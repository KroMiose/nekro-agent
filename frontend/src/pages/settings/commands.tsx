import { useState, useMemo } from 'react'
import {
  Box,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  TablePagination,
  Switch,
  Chip,
  TextField,
  InputAdornment,
  Typography,
  Tooltip,
  IconButton,
  Collapse,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Stack,
  alpha,
} from '@mui/material'
import {
  Search as SearchIcon,
  ExpandMore as ExpandMoreIcon,
  ExpandLess as ExpandLessIcon,
  RestartAlt as ResetIcon,
} from '@mui/icons-material'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useTranslation } from 'react-i18next'
import type { TFunction } from 'i18next'
import { commandsApi, type CommandState } from '../../services/api/commands'
import { useNotification } from '../../hooks/useNotification'
import { UNIFIED_TABLE_STYLES } from '../../theme/variants'

const PERMISSION_COLORS: Record<string, 'error' | 'warning' | 'success' | 'default' | 'info'> = {
  super_user: 'error',
  advanced: 'warning',
  user: 'info',
  public: 'success',
}

export default function CommandsPage() {
  const { t } = useTranslation('settings')
  const notification = useNotification()
  const queryClient = useQueryClient()

  const [search, setSearch] = useState('')
  const [categoryFilter, setCategoryFilter] = useState<string>('')
  const [sourceFilter, setSourceFilter] = useState<string>('')
  const [page, setPage] = useState(0)
  const [rowsPerPage, setRowsPerPage] = useState(20)
  const [expandedRow, setExpandedRow] = useState<string | null>(null)

  const { data: commands = [], isLoading } = useQuery({
    queryKey: ['commands'],
    queryFn: () => commandsApi.listCommands(),
  })

  const toggleMutation = useMutation({
    mutationFn: ({ name, enabled }: { name: string; enabled: boolean }) =>
      commandsApi.setCommandState(name, enabled),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['commands'] })
      notification.success(t('commands.messages.toggleSuccess', '已更新命令状态'))
    },
    onError: () => {
      notification.error(t('commands.messages.toggleFailed', '更新失败'))
    },
  })

  const resetMutation = useMutation({
    mutationFn: (name: string) => commandsApi.resetCommandState(name),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['commands'] })
      notification.success(t('commands.messages.resetSuccess', '已重置命令状态'))
    },
    onError: () => {
      notification.error(t('commands.messages.resetFailed', '重置失败'))
    },
  })

  // 提取分类和来源列表
  const { categories, sources } = useMemo(() => {
    const cats = new Set<string>()
    const srcs = new Set<string>()
    commands.forEach((cmd) => {
      cats.add(cmd.category)
      srcs.add(cmd.source)
    })
    return {
      categories: Array.from(cats).sort(),
      sources: Array.from(srcs).sort(),
    }
  }, [commands])

  // 过滤
  const filtered = useMemo(() => {
    return commands.filter((cmd) => {
      const matchSearch =
        !search ||
        cmd.name.toLowerCase().includes(search.toLowerCase()) ||
        cmd.description.toLowerCase().includes(search.toLowerCase()) ||
        cmd.aliases.some((a) => a.toLowerCase().includes(search.toLowerCase()))
      const matchCategory = !categoryFilter || cmd.category === categoryFilter
      const matchSource = !sourceFilter || cmd.source === sourceFilter
      return matchSearch && matchCategory && matchSource
    })
  }, [commands, search, categoryFilter, sourceFilter])

  // 分页
  const paginated = useMemo(() => {
    const start = page * rowsPerPage
    return filtered.slice(start, start + rowsPerPage)
  }, [filtered, page, rowsPerPage])

  const handleToggle = (cmd: CommandState) => {
    toggleMutation.mutate({ name: cmd.name, enabled: !cmd.enabled })
  }

  const handleReset = (name: string) => {
    resetMutation.mutate(name)
  }

  return (
    <Box sx={{ height: '100%', display: 'flex', flexDirection: 'column', gap: 2, p: 2 }}>
      {/* 搜索和过滤栏 */}
      <Stack direction="row" spacing={2} flexWrap="wrap" useFlexGap>
        <TextField
          size="small"
          placeholder={t('commands.search', '搜索命令...')}
          value={search}
          onChange={(e) => {
            setSearch(e.target.value)
            setPage(0)
          }}
          sx={{ minWidth: 220 }}
          InputProps={{
            startAdornment: (
              <InputAdornment position="start">
                <SearchIcon fontSize="small" />
              </InputAdornment>
            ),
          }}
        />
        <FormControl size="small" sx={{ minWidth: 140 }}>
          <InputLabel>{t('commands.filters.category', '分类')}</InputLabel>
          <Select
            value={categoryFilter}
            label={t('commands.filters.category', '分类')}
            onChange={(e) => {
              setCategoryFilter(e.target.value)
              setPage(0)
            }}
          >
            <MenuItem value="">{t('commands.filters.all', '全部')}</MenuItem>
            {categories.map((cat) => (
              <MenuItem key={cat} value={cat}>
                {cat}
              </MenuItem>
            ))}
          </Select>
        </FormControl>
        <FormControl size="small" sx={{ minWidth: 140 }}>
          <InputLabel>{t('commands.filters.source', '来源')}</InputLabel>
          <Select
            value={sourceFilter}
            label={t('commands.filters.source', '来源')}
            onChange={(e) => {
              setSourceFilter(e.target.value)
              setPage(0)
            }}
          >
            <MenuItem value="">{t('commands.filters.all', '全部')}</MenuItem>
            {sources.map((src) => (
              <MenuItem key={src} value={src}>
                {src === 'built_in' ? t('commands.sources.builtIn', '内置') : src}
              </MenuItem>
            ))}
          </Select>
        </FormControl>
        <Typography variant="body2" sx={{ alignSelf: 'center', color: 'text.secondary', ml: 'auto' }}>
          {t('commands.total', '共 {{count}} 个命令', { count: filtered.length })}
        </Typography>
      </Stack>

      {/* 表格 */}
      <TableContainer sx={{ ...UNIFIED_TABLE_STYLES.container, flex: 1, overflow: 'auto' }}>
        <Table stickyHeader size="small">
          <TableHead>
            <TableRow>
              <TableCell sx={UNIFIED_TABLE_STYLES.header} width={40} />
              <TableCell sx={UNIFIED_TABLE_STYLES.header}>
                {t('commands.table.name', '命令名')}
              </TableCell>
              <TableCell sx={UNIFIED_TABLE_STYLES.header}>
                {t('commands.table.description', '描述')}
              </TableCell>
              <TableCell sx={UNIFIED_TABLE_STYLES.header} width={100}>
                {t('commands.table.category', '分类')}
              </TableCell>
              <TableCell sx={UNIFIED_TABLE_STYLES.header} width={100}>
                {t('commands.table.source', '来源')}
              </TableCell>
              <TableCell sx={UNIFIED_TABLE_STYLES.header} width={90}>
                {t('commands.table.permission', '权限')}
              </TableCell>
              <TableCell sx={UNIFIED_TABLE_STYLES.header} width={80} align="center">
                {t('commands.table.enabled', '启用')}
              </TableCell>
              <TableCell sx={UNIFIED_TABLE_STYLES.header} width={60} align="center">
                {t('commands.table.actions', '操作')}
              </TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {isLoading ? (
              <TableRow>
                <TableCell colSpan={8} align="center" sx={{ py: 4 }}>
                  <Typography color="text.secondary">
                    {t('commands.loading', '加载中...')}
                  </Typography>
                </TableCell>
              </TableRow>
            ) : paginated.length === 0 ? (
              <TableRow>
                <TableCell colSpan={8} align="center" sx={{ py: 4 }}>
                  <Typography color="text.secondary">
                    {t('commands.empty', '暂无命令')}
                  </Typography>
                </TableCell>
              </TableRow>
            ) : (
              paginated.map((cmd) => (
                <CommandRow
                  key={cmd.name}
                  cmd={cmd}
                  expanded={expandedRow === cmd.name}
                  onToggleExpand={() =>
                    setExpandedRow(expandedRow === cmd.name ? null : cmd.name)
                  }
                  onToggleEnabled={() => handleToggle(cmd)}
                  onReset={() => handleReset(cmd.name)}
                  t={t}
                />
              ))
            )}
          </TableBody>
        </Table>
      </TableContainer>

      {/* 分页 */}
      <TablePagination
        component="div"
        count={filtered.length}
        page={page}
        onPageChange={(_, p) => setPage(p)}
        rowsPerPage={rowsPerPage}
        onRowsPerPageChange={(e) => {
          setRowsPerPage(parseInt(e.target.value, 10))
          setPage(0)
        }}
        rowsPerPageOptions={[10, 20, 50]}
        labelRowsPerPage={t('commands.rowsPerPage', '每页')}
      />
    </Box>
  )
}

function CommandRow({
  cmd,
  expanded,
  onToggleExpand,
  onToggleEnabled,
  onReset,
  t,
}: {
  cmd: CommandState
  expanded: boolean
  onToggleExpand: () => void
  onToggleEnabled: () => void
  onReset: () => void
  t: TFunction<'settings'>
}) {
  return (
    <>
      <TableRow sx={UNIFIED_TABLE_STYLES.row}>
        <TableCell sx={UNIFIED_TABLE_STYLES.cell}>
          <IconButton size="small" onClick={onToggleExpand}>
            {expanded ? <ExpandLessIcon fontSize="small" /> : <ExpandMoreIcon fontSize="small" />}
          </IconButton>
        </TableCell>
        <TableCell sx={UNIFIED_TABLE_STYLES.cell}>
          <Typography variant="body2" fontWeight={600} fontFamily="monospace">
            {cmd.name}
          </Typography>
          {cmd.aliases.length > 0 && (
            <Typography variant="caption" color="text.secondary">
              {cmd.aliases.join(', ')}
            </Typography>
          )}
        </TableCell>
        <TableCell sx={UNIFIED_TABLE_STYLES.cell}>
          <Typography variant="body2" noWrap sx={{ maxWidth: 300 }}>
            {cmd.description}
          </Typography>
        </TableCell>
        <TableCell sx={UNIFIED_TABLE_STYLES.cell}>
          <Chip label={cmd.category} size="small" variant="outlined" />
        </TableCell>
        <TableCell sx={UNIFIED_TABLE_STYLES.cell}>
          <Chip
            label={cmd.source === 'built_in' ? t('commands.sources.builtIn', '内置') : cmd.source}
            size="small"
            color={cmd.source === 'built_in' ? 'primary' : 'default'}
            variant="outlined"
          />
        </TableCell>
        <TableCell sx={UNIFIED_TABLE_STYLES.cell}>
          <Stack direction="row" spacing={0.5} alignItems="center" flexWrap="wrap" useFlexGap>
            <Chip
              label={t(`commands.permissions.${cmd.permission}`, cmd.permission)}
              size="small"
              color={PERMISSION_COLORS[cmd.permission] || 'default'}
            />
            {cmd.permission === 'advanced' && (
              <Chip
                label={t('commands.permissions.super_user', '超级管理员')}
                size="small"
                color="error"
              />
            )}
          </Stack>
        </TableCell>
        <TableCell sx={UNIFIED_TABLE_STYLES.cell} align="center">
          <Switch checked={cmd.enabled} onChange={onToggleEnabled} size="small" />
        </TableCell>
        <TableCell sx={UNIFIED_TABLE_STYLES.cell} align="center">
          <Tooltip title={t('commands.actions.reset', '重置为默认')}>
            <IconButton size="small" onClick={onReset}>
              <ResetIcon fontSize="small" />
            </IconButton>
          </Tooltip>
        </TableCell>
      </TableRow>
      <TableRow>
        <TableCell colSpan={8} sx={{ py: 0, border: 'none' }}>
          <Collapse in={expanded} timeout="auto" unmountOnExit>
            <Box sx={(theme) => ({
              p: 2,
              my: 1,
              borderRadius: 1,
              backgroundColor: alpha(theme.palette.primary.main, 0.04),
            })}>
              <Stack spacing={1}>
                <DetailItem
                  label={t('commands.detail.namespace', '命名空间')}
                  value={cmd.namespace}
                />
                <DetailItem
                  label={t('commands.detail.usage', '用法')}
                  value={cmd.usage}
                  mono
                />
                {cmd.aliases.length > 0 && (
                  <DetailItem
                    label={t('commands.detail.aliases', '别名')}
                    value={cmd.aliases.join(', ')}
                    mono
                  />
                )}
                {cmd.params_schema &&
                  (cmd.params_schema.properties as Record<string, unknown> | undefined) &&
                  Object.keys(cmd.params_schema.properties as Record<string, unknown>).length >
                    0 && (
                    <DetailItem
                      label={t('commands.detail.params', '参数')}
                      value={formatParams(cmd.params_schema as Record<string, unknown>)}
                      mono
                    />
                  )}
              </Stack>
            </Box>
          </Collapse>
        </TableCell>
      </TableRow>
    </>
  )
}

function DetailItem({
  label,
  value,
  mono,
}: {
  label: string
  value: string
  mono?: boolean
}) {
  return (
    <Stack direction="row" spacing={1} alignItems="baseline">
      <Typography variant="caption" color="text.secondary" sx={{ minWidth: 70 }}>
        {label}:
      </Typography>
      <Typography
        variant="body2"
        sx={mono ? { fontFamily: 'monospace', fontSize: '0.8rem' } : undefined}
      >
        {value}
      </Typography>
    </Stack>
  )
}

function formatParams(schema: Record<string, unknown>): string {
  const props = schema.properties as Record<string, Record<string, unknown>> | undefined
  if (!props) return ''
  const required = (schema.required as string[]) || []
  return Object.entries(props)
    .map(([name, prop]) => {
      const type = prop.type as string
      const desc = prop.description as string | undefined
      const isRequired = required.includes(name)
      const suffix = isRequired ? '' : '?'
      const descStr = desc ? ` (${desc})` : ''
      return `${name}${suffix}: ${type}${descStr}`
    })
    .join(', ')
}
