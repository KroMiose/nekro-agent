import { useEffect, useMemo, useState } from 'react'
import {
  Alert,
  alpha,
  Box,
  Button,
  Chip,
  Dialog,
  DialogActions,
  DialogContent,
  DialogContentText,
  DialogTitle,
  Drawer,
  IconButton,
  InputAdornment,
  MenuItem,
  Paper,
  Stack,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  TextField,
  Tooltip,
  Typography,
  type Theme,
  useMediaQuery,
  useTheme,
} from '@mui/material'
import {
  AccessTime as AccessTimeIcon,
  DeleteOutline as DeleteOutlineIcon,
  ErrorOutline as ErrorOutlineIcon,
  OpenInNew as OpenInNewIcon,
  FlashOn as FlashOnIcon,
  FilterAltOff as FilterAltOffIcon,
  PauseCircleOutline as PauseCircleOutlineIcon,
  PlayArrow as PlayArrowIcon,
  Refresh as RefreshIcon,
  Repeat as RepeatIcon,
  Schedule as ScheduleIcon,
  Search as SearchIcon,
  Close as CloseIcon,
  VisibilityOutlined as VisibilityOutlinedIcon,
} from '@mui/icons-material'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { useNotification } from '../../hooks/useNotification'
import { pluginsApi } from '../../services/api/plugins'
import {
  TimerSortBy,
  TimerTaskItem,
  TimerTaskStatus,
  TimerTaskType,
  TimerTimeRange,
  timersApi,
} from '../../services/api/timers'
import { workspaceApi } from '../../services/api/workspace'
import { CHIP_VARIANTS, UNIFIED_TABLE_STYLES } from '../../theme/variants'
import TablePaginationStyled from '../../components/common/TablePaginationStyled'

type QuickFilter = 'all' | 'activeRecurring' | 'paused' | 'upcoming24h' | 'errors'

const DEFAULT_ROWS_PER_PAGE = 10

function formatDateTime(value: string | null | undefined) {
  if (!value) return '-'
  return new Date(value).toLocaleString()
}

function formatTaskRule(task: TimerTaskItem, t: (key: string, options?: Record<string, unknown>) => string) {
  if (task.task_type === 'one_shot') {
    return {
      primary: formatDateTime(task.trigger_at),
      secondary: task.is_temporary ? t('timers.types.oneShotTemporary') : (task.timezone || t('timers.misc.oneShotRule')),
    }
  }
  return {
    primary: task.cron_expr || '-',
    secondary: [task.workday_mode ? t(`timers.workdayMode.${task.workday_mode}`) : '', task.timezone || '']
      .filter(Boolean)
      .join(' · '),
  }
}

function getStatusColor(theme: Theme, status: TimerTaskStatus) {
  if (status === 'active') return theme.palette.success.main
  if (status === 'paused') return theme.palette.warning.main
  return theme.palette.error.main
}

function getTypeColor(theme: Theme, taskType: TimerTaskType) {
  return taskType === 'recurring' ? theme.palette.primary.main : theme.palette.info.main
}

function StatCard({
  label,
  value,
  icon,
  color,
  active,
  onClick,
}: {
  label: string
  value: number
  icon: React.ReactNode
  color: string
  active: boolean
  onClick: () => void
}) {
  return (
    <Paper
      variant="outlined"
      onClick={onClick}
      sx={{
        cursor: 'pointer',
        px: 2,
        py: 1.5,
        height: '100%',
        display: 'flex',
        alignItems: 'center',
        gap: 1.5,
        borderRadius: 2,
        borderColor: active ? alpha(color, 0.4) : 'divider',
        bgcolor: active ? alpha(color, 0.04) : undefined,
      }}
    >
      <Box
        sx={{
          width: 36,
          height: 36,
          borderRadius: 1.5,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          bgcolor: color,
          color: '#fff',
          flexShrink: 0,
        }}
      >
        {icon}
      </Box>
      <Box sx={{ minWidth: 0 }}>
        <Typography variant="h6" sx={{ fontWeight: 700, lineHeight: 1.2 }}>
          {value}
        </Typography>
        <Typography variant="caption" color="text.secondary">
          {label}
        </Typography>
      </Box>
    </Paper>
  )
}

function DetailSection({
  title,
  children,
}: {
  title: string
  children: React.ReactNode
}) {
  return (
    <Paper
      variant="outlined"
      sx={{
        p: 2,
        borderRadius: 2,
      }}
    >
      <Typography
        variant="subtitle2"
        sx={{
          fontWeight: 700,
          mb: 1.5,
          textTransform: 'uppercase',
          letterSpacing: 0.4,
          color: 'text.secondary',
        }}
      >
        {title}
      </Typography>
      <Stack spacing={1.25}>
        {children}
      </Stack>
    </Paper>
  )
}

function DetailField({
  label,
  value,
  mono = false,
  multiline = false,
  tone = 'default',
}: {
  label: string
  value: React.ReactNode
  mono?: boolean
  multiline?: boolean
  tone?: 'default' | 'error' | 'muted'
}) {
  return (
    <Box
      sx={{
        display: 'grid',
        gridTemplateColumns: { xs: '1fr', sm: '132px minmax(0, 1fr)' },
        gap: { xs: 0.5, sm: 1.5 },
        alignItems: multiline ? 'start' : 'center',
      }}
    >
      <Typography variant="caption" color="text.secondary" sx={{ fontWeight: 600 }}>
        {label}
      </Typography>
      <Typography
        variant="body2"
        sx={{
          fontFamily: mono ? 'ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace' : 'inherit',
          color: tone === 'error' ? 'error.main' : tone === 'muted' ? 'text.secondary' : 'text.primary',
          whiteSpace: multiline ? 'pre-wrap' : 'normal',
          wordBreak: 'break-word',
          minWidth: 0,
        }}
      >
        {value}
      </Typography>
    </Box>
  )
}

function DetailChipWrap({ children }: { children: React.ReactNode }) {
  return (
    <Stack direction="row" spacing={0.75} useFlexGap flexWrap="wrap">
      {children}
    </Stack>
  )
}

export default function WorkspaceTimersPage() {
  const theme = useTheme()
  const isMobile = useMediaQuery(theme.breakpoints.down('md'))
  const { t } = useTranslation('workspace')
  const notification = useNotification()
  const queryClient = useQueryClient()
  const navigate = useNavigate()
  const [searchParams, setSearchParams] = useSearchParams()

  const [search, setSearch] = useState('')
  const [workspaceId, setWorkspaceId] = useState<number | ''>('')
  const [taskType, setTaskType] = useState<TimerTaskType | ''>('')
  const [status, setStatus] = useState<TimerTaskStatus | ''>('')
  const [timeRange, setTimeRange] = useState<TimerTimeRange>('all')
  const [sortBy, setSortBy] = useState<TimerSortBy>('next_run_asc')
  const [quickFilter, setQuickFilter] = useState<QuickFilter>('all')
  const [selectedTask, setSelectedTask] = useState<TimerTaskItem | null>(null)
  const [confirmDeleteTask, setConfirmDeleteTask] = useState<TimerTaskItem | null>(null)
  const [page, setPage] = useState(0)
  const [rowsPerPage, setRowsPerPage] = useState(DEFAULT_ROWS_PER_PAGE)

  useEffect(() => {
    const initialWorkspaceId = searchParams.get('workspace_id')
    const initialChatKey = searchParams.get('chat_key')
    if (initialWorkspaceId) {
      const parsed = Number(initialWorkspaceId)
      if (!Number.isNaN(parsed)) setWorkspaceId(parsed)
    }
    if (initialChatKey) {
      setSearch(initialChatKey)
    }
    if (initialWorkspaceId || initialChatKey) {
      setSearchParams({}, { replace: true })
    }
  // 仅在挂载时处理外部跳转参数
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const summaryQuery = useQuery({
    queryKey: ['timers-summary'],
    queryFn: () => timersApi.getSummary(),
  })

  const listQuery = useQuery({
    queryKey: ['timers-list', search, workspaceId, taskType, status, timeRange, sortBy],
    queryFn: () =>
      timersApi.getList({
        search: search || undefined,
        workspace_id: workspaceId === '' ? undefined : workspaceId,
        task_type: taskType || undefined,
        status: status || undefined,
        time_range: timeRange,
        sort_by: sortBy,
      }),
  })

  const workspacesQuery = useQuery({
    queryKey: ['workspace-list'],
    queryFn: () => workspaceApi.getList(),
  })

  const pluginsQuery = useQuery({
    queryKey: ['plugins'],
    queryFn: () => pluginsApi.getPlugins(),
  })

  const detailQuery = useQuery({
    queryKey: ['timer-detail', selectedTask?.task_type, selectedTask?.id],
    queryFn: () => timersApi.getDetail(selectedTask!.task_type, selectedTask!.id),
    enabled: !!selectedTask,
  })

  const invalidateTimers = () => {
    queryClient.invalidateQueries({ queryKey: ['timers-summary'] })
    queryClient.invalidateQueries({ queryKey: ['timers-list'] })
    if (selectedTask) {
      queryClient.invalidateQueries({ queryKey: ['timer-detail', selectedTask.task_type, selectedTask.id] })
    }
  }

  const runNowMutation = useMutation({
    mutationFn: ({ taskType, taskId }: { taskType: TimerTaskType; taskId: string }) => timersApi.runNow(taskType, taskId),
    onSuccess: () => {
      notification.success(t('timers.notifications.runNowSuccess'))
      invalidateTimers()
    },
    onError: (error: Error) => notification.error(t('timers.notifications.runNowFailed', { message: error.message })),
  })

  const pauseMutation = useMutation({
    mutationFn: (taskId: string) => timersApi.pause(taskId),
    onSuccess: () => {
      notification.success(t('timers.notifications.pauseSuccess'))
      invalidateTimers()
    },
    onError: (error: Error) => notification.error(t('timers.notifications.pauseFailed', { message: error.message })),
  })

  const resumeMutation = useMutation({
    mutationFn: (taskId: string) => timersApi.resume(taskId),
    onSuccess: () => {
      notification.success(t('timers.notifications.resumeSuccess'))
      invalidateTimers()
    },
    onError: (error: Error) => notification.error(t('timers.notifications.resumeFailed', { message: error.message })),
  })

  const deleteMutation = useMutation({
    mutationFn: ({ taskType, taskId }: { taskType: TimerTaskType; taskId: string }) => timersApi.delete(taskType, taskId),
    onSuccess: () => {
      notification.success(t('timers.notifications.deleteSuccess'))
      invalidateTimers()
      setConfirmDeleteTask(null)
      if (selectedTask) setSelectedTask(null)
    },
    onError: (error: Error) => notification.error(t('timers.notifications.deleteFailed', { message: error.message })),
  })

  const items = useMemo(() => listQuery.data?.items ?? [], [listQuery.data?.items])
  const pagedItems = useMemo(
    () => items.slice(page * rowsPerPage, page * rowsPerPage + rowsPerPage),
    [items, page, rowsPerPage],
  )

  useEffect(() => {
    setPage(0)
  }, [search, workspaceId, taskType, status, timeRange, sortBy, quickFilter])

  const quickFilterCounts = summaryQuery.data

  const activeFiltersCount = [
    search.trim() !== '',
    workspaceId !== '',
    taskType !== '',
    status !== '',
    timeRange !== 'all',
    sortBy !== 'next_run_asc',
  ].filter(Boolean).length

  const handleResetFilters = () => {
    setSearch('')
    setWorkspaceId('')
    setTaskType('')
    setStatus('')
    setTimeRange('all')
    setSortBy('next_run_asc')
    setQuickFilter('all')
  }

  const handleApplyQuickFilter = (filter: QuickFilter) => {
    setQuickFilter(filter)
    if (filter === 'all') {
      setStatus('')
      setTimeRange('all')
      setTaskType('')
      return
    }
    if (filter === 'activeRecurring') {
      setTaskType('recurring')
      setStatus('active')
      setTimeRange('all')
      return
    }
    if (filter === 'paused') {
      setStatus('paused')
      setTaskType('')
      setTimeRange('all')
      return
    }
    if (filter === 'upcoming24h') {
      setStatus('')
      setTaskType('')
      setTimeRange('24h')
      return
    }
    setStatus('error')
    setTaskType('')
    setTimeRange('all')
  }

  const currentDetail = detailQuery.data ?? selectedTask
  const currentRule = currentDetail ? formatTaskRule(currentDetail, t) : null
  const timerPlugin = useMemo(
    () =>
      (pluginsQuery.data ?? []).find(
        plugin =>
          plugin.id === 'timer' ||
          plugin.id.endsWith('.timer') ||
          plugin.moduleName === 'timer',
      ),
    [pluginsQuery.data],
  )
  const timerPluginUnavailable = timerPlugin ? !timerPlugin.enabled : false

  const abnormalHint = quickFilterCounts && quickFilterCounts.errors > 0
    ? t('timers.healthHint', { count: quickFilterCounts.errors })
    : null

  return (
    <Box
      sx={{
        ...UNIFIED_TABLE_STYLES.tableLayoutContainer,
        p: 3,
        height: 'calc(100vh - 64px)',
      }}
    >
      <Box
        sx={{
          flexShrink: 0,
          display: 'grid',
          gap: 2,
          mb: 3,
          gridTemplateColumns: {
            xs: '1fr',
            sm: 'repeat(2, minmax(0, 1fr))',
            lg: 'repeat(5, minmax(0, 1fr))',
          },
        }}
      >
        <Box>
          <StatCard
            label={t('timers.stats.total')}
            value={quickFilterCounts?.total ?? 0}
            icon={<ScheduleIcon />}
            color={theme.palette.primary.main}
            active={quickFilter === 'all'}
            onClick={() => handleApplyQuickFilter('all')}
          />
        </Box>
        <Box>
          <StatCard
            label={t('timers.stats.activeRecurring')}
            value={quickFilterCounts?.active_recurring ?? 0}
            icon={<RepeatIcon />}
            color={theme.palette.success.main}
            active={quickFilter === 'activeRecurring'}
            onClick={() => handleApplyQuickFilter('activeRecurring')}
          />
        </Box>
        <Box>
          <StatCard
            label={t('timers.stats.paused')}
            value={quickFilterCounts?.paused ?? 0}
            icon={<PauseCircleOutlineIcon />}
            color={theme.palette.warning.main}
            active={quickFilter === 'paused'}
            onClick={() => handleApplyQuickFilter('paused')}
          />
        </Box>
        <Box>
          <StatCard
            label={t('timers.stats.upcoming24h')}
            value={quickFilterCounts?.upcoming_24h ?? 0}
            icon={<AccessTimeIcon />}
            color={theme.palette.info.main}
            active={quickFilter === 'upcoming24h'}
            onClick={() => handleApplyQuickFilter('upcoming24h')}
          />
        </Box>
        <Box>
          <StatCard
            label={t('timers.stats.errors')}
            value={quickFilterCounts?.errors ?? 0}
            icon={<ErrorOutlineIcon />}
            color={theme.palette.error.main}
            active={quickFilter === 'errors'}
            onClick={() => handleApplyQuickFilter('errors')}
          />
        </Box>
      </Box>

      {abnormalHint && (
        <Alert severity="warning" sx={{ mb: 2, flexShrink: 0, py: 0 }}>
          {abnormalHint}
        </Alert>
      )}

      {timerPluginUnavailable && (
        <Alert
          severity="warning"
          sx={{ mb: 2, flexShrink: 0 }}
          action={
            <Button
              color="inherit"
              size="small"
              onClick={() => navigate('/plugins/management?plugin_id=timer')}
            >
              {t('timers.pluginAlert.action')}
            </Button>
          }
        >
          {t('timers.pluginAlert.message')}
        </Alert>
      )}

      <Box sx={{ mb: 2, flexShrink: 0 }}>
        <Stack
          direction={isMobile ? 'column' : 'row'}
          spacing={1.25}
          alignItems={isMobile ? 'stretch' : 'center'}
          flexWrap="wrap"
          useFlexGap
        >
        <TextField
          placeholder={t('timers.filters.searchPlaceholder')}
          size="small"
          value={search}
          onChange={event => setSearch(event.target.value)}
          sx={{ width: { xs: '100%', sm: 280, md: 320 }, maxWidth: '100%', flexShrink: 0 }}
          InputProps={{
            startAdornment: (
              <InputAdornment position="start">
                <SearchIcon fontSize="small" />
              </InputAdornment>
            ),
            endAdornment: search ? (
              <InputAdornment position="end">
                <IconButton size="small" onClick={() => setSearch('')}>
                  <CloseIcon sx={{ fontSize: 16 }} />
                </IconButton>
              </InputAdornment>
            ) : undefined,
          }}
        />
        <TextField
          select
          size="small"
          label={t('timers.filters.workspace')}
          value={workspaceId}
          onChange={event => {
            const value = event.target.value
            setWorkspaceId(value === '' ? '' : Number(value))
          }}
          sx={{ minWidth: 170 }}
        >
          <MenuItem value="">{t('timers.filters.allWorkspaces')}</MenuItem>
          {(workspacesQuery.data ?? []).map(workspace => (
            <MenuItem key={workspace.id} value={workspace.id}>
              {workspace.name}
            </MenuItem>
          ))}
        </TextField>
        <TextField
          select
          size="small"
          label={t('timers.filters.type')}
          value={taskType}
          onChange={event => setTaskType((event.target.value || '') as TimerTaskType | '')}
          sx={{ minWidth: 130 }}
        >
          <MenuItem value="">{t('timers.filters.allTypes')}</MenuItem>
          <MenuItem value="one_shot">{t('timers.types.oneShot')}</MenuItem>
          <MenuItem value="recurring">{t('timers.types.recurring')}</MenuItem>
        </TextField>
        <TextField
          select
          size="small"
          label={t('timers.filters.status')}
          value={status}
          onChange={event => setStatus((event.target.value || '') as TimerTaskStatus | '')}
          sx={{ minWidth: 130 }}
        >
          <MenuItem value="">{t('timers.filters.allStatuses')}</MenuItem>
          <MenuItem value="active">{t('timers.status.active')}</MenuItem>
          <MenuItem value="paused">{t('timers.status.paused')}</MenuItem>
          <MenuItem value="error">{t('timers.status.error')}</MenuItem>
        </TextField>
        <TextField
          select
          size="small"
          label={t('timers.filters.timeRange')}
          value={timeRange}
          onChange={event => setTimeRange(event.target.value as TimerTimeRange)}
          sx={{ minWidth: 140 }}
        >
          <MenuItem value="all">{t('timers.timeRange.all')}</MenuItem>
          <MenuItem value="today">{t('timers.timeRange.today')}</MenuItem>
          <MenuItem value="24h">{t('timers.timeRange.next24h')}</MenuItem>
          <MenuItem value="7d">{t('timers.timeRange.next7d')}</MenuItem>
          <MenuItem value="overdue">{t('timers.timeRange.overdue')}</MenuItem>
        </TextField>
        <TextField
          select
          size="small"
          label={t('timers.filters.sortBy')}
          value={sortBy}
          onChange={event => setSortBy(event.target.value as TimerSortBy)}
          sx={{ minWidth: 150 }}
        >
          <MenuItem value="next_run_asc">{t('timers.sort.nextRun')}</MenuItem>
          <MenuItem value="recent_update">{t('timers.sort.recentUpdate')}</MenuItem>
          <MenuItem value="recent_run">{t('timers.sort.recentRun')}</MenuItem>
          <MenuItem value="error_first">{t('timers.sort.errorFirst')}</MenuItem>
        </TextField>
        <Box sx={{ flexGrow: 1 }} />
        <Stack direction="row" spacing={1} alignItems="center" flexWrap="wrap">
          <Button
            variant={quickFilter === 'errors' ? 'contained' : 'outlined'}
            startIcon={<ErrorOutlineIcon />}
            onClick={() => handleApplyQuickFilter(quickFilter === 'errors' ? 'all' : 'errors')}
            size="small"
          >
            {t('timers.actions.onlyErrors')}
          </Button>
          <IconButton onClick={() => invalidateTimers()} size="small">
            <RefreshIcon fontSize="small" />
          </IconButton>
          <IconButton
            size="small"
            onClick={handleResetFilters}
            disabled={activeFiltersCount === 0 && quickFilter === 'all'}
          >
            <FilterAltOffIcon fontSize="small" />
          </IconButton>
        </Stack>
        <Typography
          variant="body2"
          color="text.secondary"
          sx={{ alignSelf: 'center', ml: isMobile ? 0 : 'auto' }}
        >
          {t('timers.filters.totalCount', { count: items.length })}
        </Typography>
        </Stack>
      </Box>

      <Paper
        sx={{
          ...UNIFIED_TABLE_STYLES.tableContentContainer,
          position: 'relative',
        }}
      >
        <TableContainer sx={UNIFIED_TABLE_STYLES.tableViewport}>
          <Table stickyHeader>
            <TableHead>
              <TableRow>
                <TableCell sx={UNIFIED_TABLE_STYLES.header}>{t('timers.table.task')}</TableCell>
                <TableCell sx={UNIFIED_TABLE_STYLES.header} width={88}>{t('timers.table.type')}</TableCell>
                <TableCell sx={UNIFIED_TABLE_STYLES.header} width={88}>{t('timers.table.status')}</TableCell>
                <TableCell sx={UNIFIED_TABLE_STYLES.header}>{t('timers.table.workspace')}</TableCell>
                <TableCell sx={UNIFIED_TABLE_STYLES.header}>{t('timers.table.channel')}</TableCell>
                <TableCell sx={UNIFIED_TABLE_STYLES.header}>{t('timers.table.rule')}</TableCell>
                <TableCell sx={UNIFIED_TABLE_STYLES.header} width={170}>{t('timers.table.nextRun')}</TableCell>
                <TableCell sx={UNIFIED_TABLE_STYLES.header} width={170}>{t('timers.table.lastRun')}</TableCell>
                <TableCell sx={UNIFIED_TABLE_STYLES.header}>{t('timers.table.issue')}</TableCell>
                <TableCell align="center" sx={UNIFIED_TABLE_STYLES.header} width={140}>{t('timers.table.actions')}</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {listQuery.isLoading ? (
                <TableRow>
                  <TableCell colSpan={10} sx={UNIFIED_TABLE_STYLES.cell}>
                    <Typography variant="body2" color="text.secondary">
                      {t('timers.loading')}
                    </Typography>
                  </TableCell>
                </TableRow>
              ) : pagedItems.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={10} sx={UNIFIED_TABLE_STYLES.cell}>
                    <Box sx={{ py: 6, textAlign: 'center' }}>
                      <Typography variant="subtitle1" sx={{ fontWeight: 600 }}>
                        {items.length === 0 && activeFiltersCount === 0 && quickFilter === 'all'
                          ? t('timers.empty.title')
                          : t('timers.empty.filteredTitle')}
                      </Typography>
                      <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
                        {items.length === 0 && activeFiltersCount === 0 && quickFilter === 'all'
                          ? t('timers.empty.description')
                          : t('timers.empty.filteredDescription')}
                      </Typography>
                    </Box>
                  </TableCell>
                </TableRow>
              ) : (
                pagedItems.map(task => {
                  const rule = formatTaskRule(task, t)
                  const statusColor = getStatusColor(theme, task.status)
                  const typeColor = getTypeColor(theme, task.task_type)
                  const hasIssue = task.last_error || task.consecutive_failures > 0 || task.status === 'error'
                  return (
                    <TableRow
                      key={`${task.task_type}:${task.id}`}
                      hover
                      sx={{
                        ...UNIFIED_TABLE_STYLES.row,
                      }}
                    >
                      <TableCell sx={{ ...UNIFIED_TABLE_STYLES.cell, minWidth: 220 }}>
                        <Typography variant="body2" sx={{ fontWeight: 600 }}>
                          {task.title || t('timers.misc.untitled')}
                        </Typography>
                        <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mt: 0.5 }}>
                          ID: {task.id}
                        </Typography>
                      </TableCell>
                      <TableCell sx={{ ...UNIFIED_TABLE_STYLES.cell, width: 88 }}>
                        <Chip
                          label={task.task_type === 'recurring' ? t('timers.types.recurring') : t('timers.types.oneShot')}
                          size="small"
                          sx={CHIP_VARIANTS.getCustomColorChip(typeColor, true)}
                        />
                      </TableCell>
                      <TableCell sx={{ ...UNIFIED_TABLE_STYLES.cell, width: 88 }}>
                        <Chip
                          label={t(`timers.status.${task.status}`)}
                          size="small"
                          sx={CHIP_VARIANTS.getCustomColorChip(statusColor, true)}
                        />
                      </TableCell>
                      <TableCell sx={{ ...UNIFIED_TABLE_STYLES.cell, minWidth: 150 }}>
                        <Typography variant="body2" sx={{ fontWeight: 500 }}>
                          {task.workspace_name || t('timers.misc.unlinkedWorkspace')}
                        </Typography>
                        {task.workspace_id && (
                          <Typography variant="caption" color="text.secondary">
                            workspace #{task.workspace_id}
                          </Typography>
                        )}
                      </TableCell>
                      <TableCell sx={{ ...UNIFIED_TABLE_STYLES.cell, minWidth: 180 }}>
                        <Tooltip
                          title={
                            <Box>
                              <Typography variant="caption" sx={{ display: 'block' }}>
                                {task.chat_key}
                              </Typography>
                              {task.is_primary_channel && (
                                <Typography variant="caption" sx={{ display: 'block', mt: 0.25 }}>
                                  {t('timers.misc.primaryChannel')}
                                </Typography>
                              )}
                            </Box>
                          }
                          placement="top-start"
                        >
                          <Typography
                            variant="body2"
                            sx={{
                              fontWeight: 500,
                              overflow: 'hidden',
                              textOverflow: 'ellipsis',
                              whiteSpace: 'nowrap',
                              maxWidth: 220,
                              cursor: 'help',
                            }}
                          >
                            {task.channel_name || t('timers.misc.unknownChannel')}
                          </Typography>
                        </Tooltip>
                      </TableCell>
                      <TableCell sx={{ ...UNIFIED_TABLE_STYLES.cell, minWidth: 200 }}>
                        <Typography variant="body2">{rule.primary}</Typography>
                        <Typography variant="caption" color="text.secondary">
                          {rule.secondary}
                        </Typography>
                      </TableCell>
                      <TableCell sx={UNIFIED_TABLE_STYLES.cell}>{formatDateTime(task.next_run_at || task.trigger_at)}</TableCell>
                      <TableCell sx={UNIFIED_TABLE_STYLES.cell}>{formatDateTime(task.last_run_at)}</TableCell>
                      <TableCell sx={{ ...UNIFIED_TABLE_STYLES.cell, minWidth: 150 }}>
                        {hasIssue ? (
                          <Tooltip title={task.last_error || t('timers.misc.failureCount', { count: task.consecutive_failures })}>
                            <Box sx={{ color: 'error.main' }}>
                              <Typography variant="body2">
                                {task.last_error
                                  ? t('timers.misc.hasError')
                                  : t('timers.misc.failureCount', { count: task.consecutive_failures })}
                              </Typography>
                            </Box>
                          </Tooltip>
                        ) : (
                          <Typography variant="body2" color="text.secondary">-</Typography>
                        )}
                      </TableCell>
                      <TableCell align="center" sx={{ ...UNIFIED_TABLE_STYLES.cell, width: 140 }}>
                        <Stack direction="row" spacing={0.5} justifyContent="center">
                          <Tooltip title={t('timers.actions.view')}>
                            <IconButton size="small" onClick={() => setSelectedTask(task)}>
                              <VisibilityOutlinedIcon fontSize="small" />
                            </IconButton>
                          </Tooltip>
                          <Tooltip title={t('timers.actions.runNow')}>
                            <span>
                              <IconButton
                                size="small"
                                disabled={!task.actionable || runNowMutation.isPending}
                                onClick={() => {
                                  runNowMutation.mutate({ taskType: task.task_type, taskId: task.id })
                                }}
                              >
                                <FlashOnIcon fontSize="small" />
                              </IconButton>
                            </span>
                          </Tooltip>
                          {task.task_type === 'recurring' && (
                            <Tooltip title={task.status === 'paused' ? t('timers.actions.resume') : t('timers.actions.pause')}>
                              <span>
                                <IconButton
                                  size="small"
                                  disabled={!task.actionable || pauseMutation.isPending || resumeMutation.isPending}
                                  onClick={() => {
                                    if (task.status === 'paused') {
                                      resumeMutation.mutate(task.id)
                                    } else {
                                      pauseMutation.mutate(task.id)
                                    }
                                  }}
                                >
                                  {task.status === 'paused'
                                    ? <PlayArrowIcon fontSize="small" />
                                    : <PauseCircleOutlineIcon fontSize="small" />}
                                </IconButton>
                              </span>
                            </Tooltip>
                          )}
                          <Tooltip title={t('timers.actions.delete')}>
                            <span>
                              <IconButton
                                size="small"
                                color="error"
                                disabled={!task.actionable || deleteMutation.isPending}
                                onClick={() => setConfirmDeleteTask(task)}
                              >
                                <DeleteOutlineIcon fontSize="small" />
                              </IconButton>
                            </span>
                          </Tooltip>
                        </Stack>
                      </TableCell>
                    </TableRow>
                  )
                })
              )}
            </TableBody>
          </Table>
        </TableContainer>
        <TablePaginationStyled
          component="div"
          count={items.length}
          page={page}
          rowsPerPage={rowsPerPage}
          onPageChange={(_, newPage) => setPage(newPage)}
          onRowsPerPageChange={event => {
            setRowsPerPage(parseInt(event.target.value, 10))
            setPage(0)
          }}
          loading={listQuery.isLoading}
          rowsPerPageOptions={[10, 25, 50]}
          showFirstLastPageButtons={false}
        />
      </Paper>

      <Drawer
        anchor="right"
        open={!!selectedTask}
        onClose={() => setSelectedTask(null)}
        PaperProps={{
          sx: {
            width: { xs: '100%', sm: 520, md: 640 },
            maxWidth: '100vw',
            mt: { xs: '56px', sm: '64px' },
            height: { xs: 'calc(100% - 56px)', sm: 'calc(100% - 64px)' },
            p: 0,
          },
        }}
      >
        {currentDetail && (
          <Box sx={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
            <Box
              sx={{
                px: 3,
                py: 2,
                borderBottom: '1px solid',
                borderColor: 'divider',
                bgcolor: alpha(theme.palette.primary.main, 0.04),
              }}
            >
              <Stack spacing={1}>
                <Stack direction="row" spacing={1} alignItems="center">
                  <Typography variant="subtitle1" sx={{ fontWeight: 700, flex: 1, lineHeight: 1.3 }}>
                    {currentDetail.title || t('timers.misc.untitled')}
                  </Typography>
                  <Chip
                    label={currentDetail.task_type === 'recurring' ? t('timers.types.recurring') : t('timers.types.oneShot')}
                    size="small"
                    variant="outlined"
                    sx={CHIP_VARIANTS.getCustomColorChip(getTypeColor(theme, currentDetail.task_type), false)}
                  />
                  <Chip
                    label={t(`timers.status.${currentDetail.status}`)}
                    size="small"
                    sx={CHIP_VARIANTS.getCustomColorChip(getStatusColor(theme, currentDetail.status), true)}
                  />
                </Stack>
                <Typography variant="caption" color="text.secondary">
                  {currentDetail.event_desc || t('timers.misc.noDescription')}
                </Typography>
              </Stack>
            </Box>

            <Box sx={{ flex: 1, overflowY: 'auto', p: 3 }}>
              <Stack spacing={2}>
                <Alert
                  severity={currentDetail.last_error || currentDetail.status === 'error' ? 'error' : 'success'}
                  variant="outlined"
                  sx={{ py: 0.25 }}
                >
                  {currentDetail.last_error || currentDetail.status === 'error'
                    ? (currentDetail.last_error || t('timers.detail.healthAlertError'))
                    : t('timers.detail.healthAlertNormal')}
                </Alert>

                <DetailSection title={t('timers.detail.basic')}>
                  <DetailField label="ID" value={currentDetail.id} mono />
                  <DetailField
                    label={t('timers.detail.tags')}
                    value={(
                      <DetailChipWrap>
                        <Chip
                          label={currentDetail.task_type === 'recurring' ? t('timers.types.recurring') : t('timers.types.oneShot')}
                          size="small"
                          variant="outlined"
                          sx={CHIP_VARIANTS.getCustomColorChip(getTypeColor(theme, currentDetail.task_type), false)}
                        />
                        <Chip
                          label={t(`timers.status.${currentDetail.status}`)}
                          size="small"
                          sx={CHIP_VARIANTS.getCustomColorChip(getStatusColor(theme, currentDetail.status), true)}
                        />
                        <Chip
                          label={t(`timers.source.${currentDetail.source}`)}
                          size="small"
                          variant="outlined"
                          sx={{ height: 22, fontSize: '0.7rem' }}
                        />
                        {currentDetail.is_temporary && (
                          <Chip
                            label={t('timers.types.oneShotTemporary')}
                            size="small"
                            color="warning"
                            variant="outlined"
                            sx={{ height: 22, fontSize: '0.7rem' }}
                          />
                        )}
                      </DetailChipWrap>
                    )}
                  />
                  <DetailField label={t('timers.detail.createdAt')} value={formatDateTime(currentDetail.create_time)} />
                  <DetailField label={t('timers.detail.updatedAt')} value={formatDateTime(currentDetail.update_time)} />
                </DetailSection>

                <DetailSection title={t('timers.detail.schedule')}>
                  {currentRule && (
                    <Paper
                      variant="outlined"
                      sx={{
                        p: 1.25,
                        borderRadius: 1.5,
                        bgcolor: alpha(theme.palette.primary.main, 0.03),
                      }}
                    >
                      <Typography variant="body2" sx={{ fontWeight: 600 }}>
                        {currentRule.primary}
                      </Typography>
                      {currentRule.secondary && (
                        <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mt: 0.25 }}>
                          {currentRule.secondary}
                        </Typography>
                      )}
                    </Paper>
                  )}
                  {currentDetail.task_type === 'one_shot' ? (
                    <DetailField label={t('timers.detail.triggerAt')} value={formatDateTime(currentDetail.trigger_at)} />
                  ) : (
                    <>
                      <DetailField label="Cron" value={currentDetail.cron_expr || '-'} mono />
                      <DetailField
                        label={t('timers.detail.workdayMode')}
                        value={currentDetail.workday_mode ? t(`timers.workdayMode.${currentDetail.workday_mode}`) : '-'}
                      />
                    </>
                  )}
                  <DetailField
                    label={t('timers.detail.scheduleTags')}
                    value={(
                      <DetailChipWrap>
                        {currentDetail.workday_mode && (
                          <Chip
                            label={t(`timers.workdayMode.${currentDetail.workday_mode}`)}
                            size="small"
                            variant="outlined"
                            sx={{ height: 22, fontSize: '0.7rem' }}
                          />
                        )}
                        {currentDetail.timezone && (
                          <Chip
                            label={currentDetail.timezone}
                            size="small"
                            variant="outlined"
                            sx={{ height: 22, fontSize: '0.7rem' }}
                          />
                        )}
                      </DetailChipWrap>
                    )}
                  />
                  <DetailField label={t('timers.detail.timezone')} value={currentDetail.timezone || '-'} />
                  <DetailField label={t('timers.table.nextRun')} value={formatDateTime(currentDetail.next_run_at || currentDetail.trigger_at)} />
                  <DetailField label={t('timers.table.lastRun')} value={formatDateTime(currentDetail.last_run_at)} />
                </DetailSection>

                <DetailSection title={t('timers.detail.health')}>
                  <DetailField
                    label={t('timers.detail.healthTags')}
                    value={(
                      <DetailChipWrap>
                        <Chip
                          label={t('timers.detail.failureCountChip', { count: currentDetail.consecutive_failures })}
                          size="small"
                          sx={currentDetail.consecutive_failures > 0
                            ? CHIP_VARIANTS.getCustomColorChip(theme.palette.error.main, true)
                            : CHIP_VARIANTS.getCustomColorChip(theme.palette.success.main, true)}
                        />
                        <Chip
                          label={currentDetail.last_error || currentDetail.status === 'error'
                            ? t('timers.detail.healthStateAbnormal')
                            : t('timers.detail.healthStateNormal')}
                          size="small"
                          variant="outlined"
                          color={currentDetail.last_error || currentDetail.status === 'error' ? 'error' : 'success'}
                          sx={{ height: 22, fontSize: '0.7rem' }}
                        />
                      </DetailChipWrap>
                    )}
                  />
                  <DetailField label={t('timers.detail.failureCount')} value={String(currentDetail.consecutive_failures)} tone={currentDetail.consecutive_failures > 0 ? 'error' : 'default'} />
                  <DetailField
                    label={t('timers.detail.lastError')}
                    value={currentDetail.last_error || '-'}
                    multiline
                    tone={currentDetail.last_error ? 'error' : 'muted'}
                  />
                </DetailSection>

                <DetailSection title={t('timers.detail.linkage')}>
                  <DetailField
                    label={t('timers.detail.linkageTags')}
                    value={(
                      <DetailChipWrap>
                        <Chip
                          label={currentDetail.workspace_name || t('timers.misc.unlinkedWorkspace')}
                          size="small"
                          variant="outlined"
                          color={currentDetail.workspace_id ? 'primary' : 'warning'}
                          sx={{ height: 22, fontSize: '0.7rem' }}
                        />
                        <Chip
                          label={currentDetail.channel_name || t('timers.misc.unknownChannel')}
                          size="small"
                          variant="outlined"
                          color="info"
                          sx={{ height: 22, fontSize: '0.7rem' }}
                        />
                        {currentDetail.is_primary_channel && (
                          <Chip
                            label={t('timers.misc.primaryChannel')}
                            size="small"
                            sx={CHIP_VARIANTS.getCustomColorChip(theme.palette.warning.main, true)}
                          />
                        )}
                      </DetailChipWrap>
                    )}
                  />
                  <DetailField
                    label={t('timers.table.workspace')}
                    value={currentDetail.workspace_id ? (
                      <Box
                        component="button"
                        type="button"
                        sx={{
                          p: 0,
                          border: 'none',
                          background: 'transparent',
                          display: 'inline-flex',
                          alignItems: 'center',
                          gap: 0.5,
                          color: 'primary.main',
                          cursor: 'pointer',
                          textDecoration: 'underline',
                          textUnderlineOffset: '2px',
                          font: 'inherit',
                        }}
                        onClick={() => navigate(`/workspace/${currentDetail.workspace_id}`)}
                      >
                        {currentDetail.workspace_name || t('timers.misc.unlinkedWorkspace')}
                        <OpenInNewIcon sx={{ fontSize: 14 }} />
                      </Box>
                    ) : (
                      currentDetail.workspace_name || t('timers.misc.unlinkedWorkspace')
                    )}
                  />
                  <DetailField
                    label={t('timers.table.channel')}
                    value={(
                      <Box
                        component="button"
                        type="button"
                        sx={{
                          p: 0,
                          border: 'none',
                          background: 'transparent',
                          display: 'inline-flex',
                          alignItems: 'center',
                          gap: 0.5,
                          color: 'primary.main',
                          cursor: 'pointer',
                          textDecoration: 'underline',
                          textUnderlineOffset: '2px',
                          font: 'inherit',
                        }}
                        onClick={() => navigate(`/chat-channel?chat_key=${encodeURIComponent(currentDetail.chat_key)}`)}
                      >
                        {currentDetail.channel_name || t('timers.misc.unknownChannel')}
                        <OpenInNewIcon sx={{ fontSize: 14 }} />
                      </Box>
                    )}
                  />
                  <DetailField label="chat_key" value={currentDetail.chat_key} mono />
                </DetailSection>
              </Stack>
            </Box>

            <Box sx={{ px: 3, py: 2, borderTop: '1px solid', borderColor: 'divider' }}>
              <Stack direction="row" spacing={1} justifyContent="flex-end">
                <Button
                  variant="outlined"
                  startIcon={<FlashOnIcon />}
                  disabled={!currentDetail.actionable || runNowMutation.isPending}
                  onClick={() => runNowMutation.mutate({ taskType: currentDetail.task_type, taskId: currentDetail.id })}
                >
                  {t('timers.actions.runNow')}
                </Button>
                {currentDetail.task_type === 'recurring' && (
                  <Button
                    variant="outlined"
                    startIcon={currentDetail.status === 'paused' ? <PlayArrowIcon /> : <PauseCircleOutlineIcon />}
                    disabled={!currentDetail.actionable || pauseMutation.isPending || resumeMutation.isPending}
                    onClick={() => {
                      if (currentDetail.status === 'paused') {
                        resumeMutation.mutate(currentDetail.id)
                      } else {
                        pauseMutation.mutate(currentDetail.id)
                      }
                    }}
                  >
                    {currentDetail.status === 'paused' ? t('timers.actions.resume') : t('timers.actions.pause')}
                  </Button>
                )}
                <Button
                  color="error"
                  variant="outlined"
                  startIcon={<DeleteOutlineIcon />}
                  disabled={!currentDetail.actionable || deleteMutation.isPending}
                  onClick={() => setConfirmDeleteTask(currentDetail)}
                >
                  {t('timers.actions.delete')}
                </Button>
              </Stack>
            </Box>
          </Box>
        )}
      </Drawer>

      <Dialog open={!!confirmDeleteTask} onClose={() => setConfirmDeleteTask(null)}>
        <DialogTitle>{t('timers.deleteDialog.title')}</DialogTitle>
        <DialogContent>
          <DialogContentText>
            {t('timers.deleteDialog.content', { name: confirmDeleteTask?.title || confirmDeleteTask?.id || '' })}
          </DialogContentText>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setConfirmDeleteTask(null)}>
            {t('timers.actions.cancel')}
          </Button>
          <Button
            color="error"
            onClick={() => {
              if (!confirmDeleteTask) return
              deleteMutation.mutate({ taskType: confirmDeleteTask.task_type, taskId: confirmDeleteTask.id })
            }}
          >
            {t('timers.actions.delete')}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  )
}
