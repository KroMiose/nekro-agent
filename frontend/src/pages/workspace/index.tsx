import { useState } from 'react'
import {
  Box,
  Button,
  Card,
  CardContent,
  Typography,
  Chip,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogContentText,
  DialogActions,
  TextField,
  MenuItem,
  CircularProgress,
  Grid2,
  Alert,
  useTheme,
  alpha,
  Tooltip,
  IconButton,
  Skeleton,
  Checkbox,
  Paper,
  Autocomplete,
} from '@mui/material'
import {
  Add as AddIcon,
  Delete as DeleteIcon,
  ArrowForward as ArrowForwardIcon,
  Workspaces as WorkspacesIcon,
  CheckCircle as CheckCircleIcon,
  RemoveCircle as RemoveCircleIcon,
  ErrorOutline as ErrorOutlineIcon,
  Casino as CasinoIcon,
  PlayArrow as PlayArrowIcon,
  Stop as StopIcon,
  Refresh as RefreshIcon,
  Build as BuildIcon,
  RotateRight as RotateRightIcon,
  Hub as HubIcon,
  Extension as ExtensionIcon,
  SmartToy as SmartToyIcon,
  CheckBox as CheckBoxIcon,
  Close as CloseIcon,
  SelectAll as SelectAllIcon,
  DeselectOutlined as DeselectIcon,
  Tune as TuneIcon,
} from '@mui/icons-material'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import {
  workspaceApi,
  WorkspaceSummary,
  CreateWorkspaceBody,
} from '../../services/api/workspace'
import { ccModelPresetApi, CCModelPresetInfo } from '../../services/api/cc-model-preset'
import { useNotification } from '../../hooks/useNotification'
import { CARD_VARIANTS, CHIP_VARIANTS, SCROLLBAR_VARIANTS } from '../../theme/variants'
import NameGeneratorDialog from '../../components/common/NameGeneratorDialog'
import { useTranslation } from 'react-i18next'
import { useSystemEvents } from '../../hooks/useSystemEvents'

type BatchOp = 'start' | 'stop' | 'restart' | 'rebuild' | 'resetSession'

const defaultForm: CreateWorkspaceBody = {
  name: '',
  description: '',
  runtime_policy: 'agent',
}

function useStatusColor(status: string) {
  const theme = useTheme()
  const map: Record<string, string> = {
    active: theme.palette.success.main,
    stopped: theme.palette.text.secondary as string,
    failed: theme.palette.error.main,
    deleting: theme.palette.warning.main,
  }
  return map[status] ?? (theme.palette.text.secondary as string)
}

function usePolicyColor(policy: WorkspaceSummary['runtime_policy']) {
  const theme = useTheme()
  const map: Record<WorkspaceSummary['runtime_policy'], string> = {
    agent: theme.palette.primary.main,
    relaxed: theme.palette.info?.main ?? theme.palette.primary.light,
    strict: theme.palette.warning.main,
  }
  return map[policy]
}

function StatusChip({ status, ccActive = false }: { status: string; ccActive?: boolean }) {
  const { t } = useTranslation('workspace')
  const color = useStatusColor(status)
  const knownStatuses = ['active', 'stopped', 'failed', 'deleting']
  const label = knownStatuses.includes(status) ? t(`status.${status}`) : status
  const isActiveWithCC = status === 'active' && ccActive

  return (
    <Chip
      label={label}
      size="small"
      sx={{
        ...CHIP_VARIANTS.getCustomColorChip(color, true),
        ...(isActiveWithCC && {
          '@keyframes ccGlow': {
            '0%': { boxShadow: `0 0 0 0 ${alpha(color, 0.5)}, 0 0 4px 1px ${alpha(color, 0.3)}` },
            '50%': { boxShadow: `0 0 0 4px ${alpha(color, 0)}, 0 0 8px 3px ${alpha(color, 0.5)}` },
            '100%': { boxShadow: `0 0 0 0 ${alpha(color, 0.5)}, 0 0 4px 1px ${alpha(color, 0.3)}` },
          },
          animation: 'ccGlow 1.8s ease-in-out infinite',
          fontWeight: 700,
        }),
      }}
    />
  )
}

function PolicyChip({ policy }: { policy: WorkspaceSummary['runtime_policy'] }) {
  const { t } = useTranslation('workspace')
  const color = usePolicyColor(policy)
  return <Chip label={t(`policy.${policy}`)} size="small" sx={CHIP_VARIANTS.getCustomColorChip(color, true)} />
}

// ── 概览统计卡片 ────────────────────────────────────────────────────────────

function StatCard({
  icon,
  value,
  label,
  color,
  loading,
}: {
  icon: React.ReactNode
  value: number
  label: string
  color: string
  loading?: boolean
}) {
  return (
    <Card sx={{ ...CARD_VARIANTS.default.styles, flex: 1 }}>
      <CardContent sx={{ p: 2, '&:last-child': { pb: 2 } }}>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5 }}>
          <Box
            sx={{
              color,
              bgcolor: alpha(color, 0.1),
              borderRadius: 2,
              p: 1.1,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              flexShrink: 0,
            }}
          >
            {icon}
          </Box>
          <Box sx={{ minWidth: 0 }}>
            {loading ? (
              <Skeleton variant="text" width={28} height={32} />
            ) : (
              <Typography variant="h5" fontWeight={700} lineHeight={1.1}>
                {value}
              </Typography>
            )}
            <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mt: 0.1 }}>
              {label}
            </Typography>
          </Box>
        </Box>
      </CardContent>
    </Card>
  )
}

// ── 工作区卡片 ──────────────────────────────────────────────────────────────

function WorkspaceCard({
  ws,
  effectiveStatus,
  ccActive,
  batchMode,
  isSelected,
  onToggleSelect,
  onEnter,
  onDelete,
}: {
  ws: WorkspaceSummary
  effectiveStatus: WorkspaceSummary['status']
  ccActive: boolean
  batchMode: boolean
  isSelected: boolean
  onToggleSelect: () => void
  onEnter: () => void
  onDelete: () => void
}) {
  const { t } = useTranslation('workspace')
  const statusColor = useStatusColor(effectiveStatus)
  const theme = useTheme()

  const handleCardClick = () => {
    if (batchMode) onToggleSelect()
  }

  // 优先使用 channel_display_names（频道名），fallback 到 channel_names（chat_key）
  const displayNames = ws.channel_display_names?.length ? ws.channel_display_names : ws.channel_names
  const channelExtra = ws.channel_count - displayNames.length

  // 构建频道 Tooltip 内容
  const channelTooltip = [
    ...displayNames,
    ...(channelExtra > 0 ? [t('card.channelMore', { n: channelExtra })] : []),
  ].join(' · ')

  const createDate = new Date(ws.create_time).toLocaleDateString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
  })

  return (
    <Card
      sx={{
        ...CARD_VARIANTS.default.styles,
        height: '100%',
        display: 'flex',
        flexDirection: 'column',
        cursor: batchMode ? 'pointer' : 'default',
        transition: 'all 0.2s ease',
        overflow: 'hidden',
        position: 'relative',
        border: isSelected
          ? `2px solid ${theme.palette.primary.main}`
          : '2px solid transparent',
        '&:hover': batchMode
          ? { boxShadow: `0 4px 16px ${alpha(theme.palette.primary.main, 0.18)}` }
          : { transform: 'translateY(-2px)', boxShadow: `0 8px 24px ${alpha(statusColor, 0.15)}` },
      }}
      onClick={handleCardClick}
    >
      {/* 顶部状态色条 */}
      <Box sx={{ height: 3, bgcolor: statusColor, flexShrink: 0 }} />

      {/* 批量模式：左上角 checkbox */}
      {batchMode && (
        <Box
          sx={{ position: 'absolute', top: 10, left: 10, zIndex: 2 }}
          onClick={e => { e.stopPropagation(); onToggleSelect() }}
        >
          <Checkbox
            size="small"
            checked={isSelected}
            sx={{
              p: 0.25,
              bgcolor: alpha(theme.palette.background.paper, 0.9),
              borderRadius: 1,
              boxShadow: `0 1px 4px ${alpha(theme.palette.common.black, 0.15)}`,
              '&:hover': { bgcolor: theme.palette.background.paper },
            }}
          />
        </Box>
      )}

      <CardContent sx={{ flexGrow: 1, p: 2, pb: 1.5 }}>
        {/* 第一行：名称 + 状态点 + ID */}
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1, pl: batchMode ? 3.5 : 0 }}>
          <Box
            sx={{
              width: 7,
              height: 7,
              borderRadius: '50%',
              bgcolor: statusColor,
              flexShrink: 0,
              boxShadow: `0 0 0 2px ${alpha(statusColor, 0.25)}`,
            }}
          />
          <Typography
            variant="subtitle1"
            sx={{
              fontWeight: 700,
              lineHeight: 1.25,
              overflow: 'hidden',
              textOverflow: 'ellipsis',
              whiteSpace: 'nowrap',
              flexGrow: 1,
              minWidth: 0,
            }}
          >
            {ws.name}
          </Typography>
          <Typography
            variant="caption"
            color="text.disabled"
            sx={{ fontFamily: 'monospace', flexShrink: 0, fontSize: '0.68rem' }}
          >
            #{ws.id}
          </Typography>
        </Box>

        {/* 第二行：状态 + 策略 chip */}
        <Box sx={{ display: 'flex', gap: 0.75, mb: 1.25, flexWrap: 'wrap', alignItems: 'center' }}>
          <StatusChip status={effectiveStatus} ccActive={ccActive} />
          <PolicyChip policy={ws.runtime_policy} />
        </Box>

        {/* 描述（最多 2 行） */}
        <Typography
          variant="body2"
          color={ws.description ? 'text.secondary' : 'text.disabled'}
          sx={{
            mb: 1.25,
            overflow: 'hidden',
            textOverflow: 'ellipsis',
            display: '-webkit-box',
            WebkitLineClamp: 2,
            WebkitBoxOrient: 'vertical',
            fontSize: '0.78rem',
            lineHeight: 1.55,
            minHeight: '2.4em',
            fontStyle: ws.description ? 'normal' : 'italic',
          }}
        >
          {ws.description || t('card.noDescription')}
        </Typography>

        {/* 详细信息区 */}
        <Box
          sx={{
            pt: 1,
            borderTop: `1px solid ${alpha(theme.palette.divider, 0.6)}`,
            display: 'flex',
            flexDirection: 'column',
            gap: 0.6,
          }}
        >
          {/* 绑定频道 */}
          {ws.channel_count > 0 ? (
            <Tooltip title={channelTooltip} placement="top-start">
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.6, minWidth: 0 }}>
                <HubIcon sx={{ fontSize: 13, color: 'text.disabled', flexShrink: 0 }} />
                <Typography
                  variant="caption"
                  sx={{
                    fontSize: '0.72rem',
                    color: 'text.secondary',
                    overflow: 'hidden',
                    textOverflow: 'ellipsis',
                    whiteSpace: 'nowrap',
                    minWidth: 0,
                  }}
                >
                  {displayNames[0]}
                  {channelExtra > 0 && (
                    <Box component="span" sx={{ color: 'text.disabled', ml: 0.5 }}>
                      {t('card.channelMore', { n: channelExtra })}
                    </Box>
                  )}
                  {displayNames.length > 1 && channelExtra === 0 && (
                    <Box component="span" sx={{ color: 'text.disabled', ml: 0.5 }}>
                      · {displayNames[1]}
                    </Box>
                  )}
                </Typography>
              </Box>
            </Tooltip>
          ) : (
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.6 }}>
              <HubIcon sx={{ fontSize: 13, color: 'text.disabled', flexShrink: 0 }} />
              <Typography variant="caption" sx={{ fontSize: '0.72rem', color: 'text.disabled', fontStyle: 'italic' }}>
                {t('detail.overview.channels.noChannels').split('。')[0]}
              </Typography>
            </Box>
          )}

          {/* 模型预设 */}
          {ws.cc_model_preset_name && (
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.6, minWidth: 0 }}>
              <SmartToyIcon sx={{ fontSize: 13, color: 'text.disabled', flexShrink: 0 }} />
              <Typography
                variant="caption"
                sx={{
                  fontSize: '0.72rem',
                  color: 'text.secondary',
                  overflow: 'hidden',
                  textOverflow: 'ellipsis',
                  whiteSpace: 'nowrap',
                }}
              >
                {ws.cc_model_preset_name}
              </Typography>
            </Box>
          )}

          {/* Skill/MCP + 创建时间（同行，两端对齐） */}
          <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 1 }}>
            <Tooltip title={`${ws.skill_count} Skills / ${ws.mcp_count} MCP`} placement="top-start">
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.4 }}>
                <ExtensionIcon sx={{ fontSize: 13, color: ws.skill_count > 0 || ws.mcp_count > 0 ? 'text.secondary' : 'text.disabled' }} />
                <Typography
                  variant="caption"
                  sx={{
                    fontSize: '0.72rem',
                    color: ws.skill_count > 0 || ws.mcp_count > 0 ? 'text.secondary' : 'text.disabled',
                  }}
                >
                  {ws.skill_count} / {ws.mcp_count}
                </Typography>
              </Box>
            </Tooltip>
            <Typography variant="caption" sx={{ fontSize: '0.68rem', color: 'text.disabled', flexShrink: 0 }}>
              {createDate}
            </Typography>
          </Box>
        </Box>
      </CardContent>

      {/* 操作按钮区（非批量模式显示） */}
      {!batchMode && (
        <Box
          sx={{ px: 2, pb: 2, pt: 0.5, display: 'flex', gap: 1 }}
          onClick={e => e.stopPropagation()}
        >
          <Button
            variant="contained"
            size="small"
            endIcon={<ArrowForwardIcon />}
            onClick={onEnter}
            sx={{ flexGrow: 1 }}
          >
            {t('card.enter')}
          </Button>
          <Tooltip title={t('card.delete')}>
            <IconButton
              size="small"
              color="error"
              onClick={onDelete}
              sx={{
                border: `1px solid ${alpha(theme.palette.error.main, 0.3)}`,
                borderRadius: 1,
              }}
            >
              <DeleteIcon fontSize="small" />
            </IconButton>
          </Tooltip>
        </Box>
      )}
    </Card>
  )
}

// ── 主页面 ──────────────────────────────────────────────────────────────────

export default function WorkspaceListPage() {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const notification = useNotification()
  const theme = useTheme()
  const { t } = useTranslation('workspace')

  const [createOpen, setCreateOpen] = useState(false)
  const [nameGenOpen, setNameGenOpen] = useState(false)
  const [deleteTarget, setDeleteTarget] = useState<WorkspaceSummary | null>(null)
  const [form, setForm] = useState<CreateWorkspaceBody>(defaultForm)

  // 批量选择状态
  const [batchMode, setBatchMode] = useState(false)
  const [selectedIds, setSelectedIds] = useState<Set<number>>(new Set())
  const [batchConfirmOp, setBatchConfirmOp] = useState<BatchOp | null>(null)
  const [batchRunning, setBatchRunning] = useState(false)

  // 批量设置 CC 模型组
  const [batchPresetOpen, setBatchPresetOpen] = useState(false)
  const [batchPresetSelected, setBatchPresetSelected] = useState<CCModelPresetInfo | null>(null)
  const [batchPresetRunning, setBatchPresetRunning] = useState(false)

  // 全局 SSE 实时状态
  const { workspaceStatuses, workspaceCcActive } = useSystemEvents()

  const { data: workspaces = [], isLoading, error } = useQuery({
    queryKey: ['workspaces'],
    queryFn: workspaceApi.getList,
  })

  const { data: allPresets = [] } = useQuery({
    queryKey: ['cc-model-presets'],
    queryFn: ccModelPresetApi.getList,
    enabled: batchPresetOpen,
  })

  const createMutation = useMutation({
    mutationFn: workspaceApi.create,
    onSuccess: workspace => {
      queryClient.invalidateQueries({ queryKey: ['workspaces'] })
      notification.success(t('createDialog.createSuccess', { name: workspace.name }))
      setCreateOpen(false)
      setForm(defaultForm)
    },
    onError: (err: Error) => notification.error(t('createDialog.createFailed', { message: err.message })),
  })

  const deleteMutation = useMutation({
    mutationFn: (id: number) => workspaceApi.delete(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['workspaces'] })
      notification.success(t('deleteDialog.deleteSuccess'))
      setDeleteTarget(null)
    },
    onError: (err: Error) => notification.error(t('deleteDialog.deleteFailed', { message: err.message })),
  })

  const handleCreate = () => {
    if (!form.name.trim()) {
      notification.warning(t('createDialog.nameRequired'))
      return
    }
    createMutation.mutate(form)
  }

  const toggleSelect = (id: number) => {
    setSelectedIds(prev => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })
  }

  const handleSelectAll = () => setSelectedIds(new Set(workspaces.map(w => w.id)))
  const handleDeselectAll = () => setSelectedIds(new Set())

  const exitBatchMode = () => {
    setBatchMode(false)
    setSelectedIds(new Set())
  }

  const batchOpFns: Record<BatchOp, (id: number) => Promise<void>> = {
    start: workspaceApi.sandboxStart,
    stop: workspaceApi.sandboxStop,
    restart: workspaceApi.sandboxRestart,
    rebuild: workspaceApi.sandboxRebuild,
    resetSession: workspaceApi.resetSession,
  }

  const handleBatchConfirm = async () => {
    if (!batchConfirmOp) return
    setBatchRunning(true)
    const ids = [...selectedIds]
    const opFn = batchOpFns[batchConfirmOp]
    await Promise.allSettled(ids.map(id => opFn(id)))
    setBatchRunning(false)
    setBatchConfirmOp(null)
    queryClient.invalidateQueries({ queryKey: ['workspaces'] })
  }

  const handleBatchSetPreset = async () => {
    setBatchPresetRunning(true)
    const ids = [...selectedIds]
    const presetId = batchPresetSelected?.id ?? null
    await Promise.allSettled(ids.map(id => workspaceApi.setCCModelPreset(id, presetId)))
    setBatchPresetRunning(false)
    setBatchPresetOpen(false)
    setBatchPresetSelected(null)
    queryClient.invalidateQueries({ queryKey: ['workspaces'] })
    notification.success(t('list.batchPreset.success', { count: ids.length }))
  }

  const opLabels: Record<BatchOp, string> = {
    start: t('list.batchBar.start'),
    stop: t('list.batchBar.stop'),
    restart: t('list.batchBar.restart'),
    rebuild: t('list.batchBar.rebuild'),
    resetSession: t('list.batchBar.resetSession'),
  }

  const totalCount = workspaces.length
  const activeCount = workspaces.filter(w => w.status === 'active').length
  const stoppedCount = workspaces.filter(w => w.status === 'stopped').length
  const failedCount = workspaces.filter(w => w.status === 'failed' || w.status === 'deleting').length

  return (
    <Box
      sx={{
        p: 3,
        height: '100%',
        overflow: 'auto',
        ...SCROLLBAR_VARIANTS.thin.styles,
        // 底部留出批量操作栏的空间
        pb: batchMode && selectedIds.size > 0 ? '80px' : 3,
        transition: 'padding-bottom 0.25s ease',
      }}
    >
      {/* ── 概览区 + 创建按钮 ── */}
      <Box sx={{ display: 'flex', gap: 2, mb: 3, alignItems: 'stretch' }}>
        <StatCard
          icon={<WorkspacesIcon sx={{ fontSize: 22 }} />}
          value={totalCount}
          label={t('list.statCards.total')}
          color={theme.palette.primary.main}
          loading={isLoading}
        />
        <StatCard
          icon={<CheckCircleIcon sx={{ fontSize: 22 }} />}
          value={activeCount}
          label={t('list.statCards.active')}
          color={theme.palette.success.main}
          loading={isLoading}
        />
        <StatCard
          icon={<RemoveCircleIcon sx={{ fontSize: 22 }} />}
          value={stoppedCount}
          label={t('list.statCards.stopped')}
          color={theme.palette.text.secondary as string}
          loading={isLoading}
        />
        <StatCard
          icon={<ErrorOutlineIcon sx={{ fontSize: 22 }} />}
          value={failedCount}
          label={t('list.statCards.failed')}
          color={theme.palette.error.main}
          loading={isLoading}
        />
        <Box sx={{ flexShrink: 0, display: 'flex', alignItems: 'stretch' }}>
          <Button
            variant="contained"
            startIcon={<AddIcon />}
            onClick={() => setCreateOpen(true)}
            sx={{ px: 3, whiteSpace: 'nowrap' }}
          >
            {t('list.createBtn')}
          </Button>
        </Box>
      </Box>

      {/* 错误提示 */}
      {error && (
        <Alert severity="error" sx={{ mb: 3 }}>
          {t('list.loadError', { message: (error as Error).message })}
        </Alert>
      )}

      {/* Section 分隔标签 */}
      {!isLoading && (
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5, mb: 2 }}>
          <Typography
            variant="caption"
            color="text.secondary"
            sx={{ fontWeight: 600, fontSize: '0.7rem', letterSpacing: '0.1em', textTransform: 'uppercase', flexShrink: 0 }}
          >
            {t('list.sectionTitle')}
          </Typography>
          <Box sx={{ flex: 1, height: 1, bgcolor: 'divider' }} />
          {workspaces.length > 0 && (
            <>
              <Typography variant="caption" color="text.disabled" sx={{ flexShrink: 0 }}>
                {t('list.total', { count: workspaces.length })}
              </Typography>
              {batchMode ? (
                <>
                  <Button
                    size="small"
                    variant="text"
                    startIcon={<SelectAllIcon sx={{ fontSize: 14 }} />}
                    onClick={handleSelectAll}
                    sx={{ minWidth: 0, px: 1, fontSize: '0.75rem' }}
                  >
                    {t('list.selectAll')}
                  </Button>
                  <Button
                    size="small"
                    variant="text"
                    startIcon={<DeselectIcon sx={{ fontSize: 14 }} />}
                    onClick={handleDeselectAll}
                    sx={{ minWidth: 0, px: 1, fontSize: '0.75rem' }}
                  >
                    {t('list.deselectAll')}
                  </Button>
                  <Button
                    size="small"
                    variant="text"
                    startIcon={<CloseIcon sx={{ fontSize: 14 }} />}
                    onClick={exitBatchMode}
                    sx={{ minWidth: 0, px: 1, fontSize: '0.75rem', color: 'text.secondary' }}
                  >
                    {t('list.batchBar.cancel')}
                  </Button>
                </>
              ) : (
                <Button
                  size="small"
                  variant="text"
                  startIcon={<CheckBoxIcon sx={{ fontSize: 14 }} />}
                  onClick={() => setBatchMode(true)}
                  sx={{ minWidth: 0, px: 1, fontSize: '0.75rem' }}
                >
                  {t('list.batchSelect')}
                </Button>
              )}
            </>
          )}
        </Box>
      )}

      {/* 工作区列表 */}
      {isLoading ? (
        <Grid2 container spacing={2}>
          {[1, 2, 3].map(i => (
            <Grid2 size={{ xs: 12, sm: 6, md: 4 }} key={i}>
              <Skeleton variant="rounded" height={260} sx={{ borderRadius: 2 }} />
            </Grid2>
          ))}
        </Grid2>
      ) : workspaces.length === 0 ? (
        <Box sx={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', pt: 6, gap: 2 }}>
          <WorkspacesIcon sx={{ fontSize: 56, opacity: 0.2 }} />
          <Typography variant="h6" color="text.secondary">{t('list.empty.title')}</Typography>
          <Typography variant="body2" color="text.secondary">{t('list.empty.hint')}</Typography>
        </Box>
      ) : (
        <Grid2 container spacing={2}>
          {workspaces.map(ws => {
            const sseSnap = workspaceStatuses.get(ws.id)
            const effectiveStatus = (sseSnap?.status ?? ws.status) as WorkspaceSummary['status']
            const ccActive = workspaceCcActive.get(ws.id) ?? false
            return (
              <Grid2 size={{ xs: 12, sm: 6, md: 4 }} key={ws.id}>
                <WorkspaceCard
                  ws={ws}
                  effectiveStatus={effectiveStatus}
                  ccActive={ccActive}
                  batchMode={batchMode}
                  isSelected={selectedIds.has(ws.id)}
                  onToggleSelect={() => toggleSelect(ws.id)}
                  onEnter={() => navigate(`/workspace/${ws.id}`)}
                  onDelete={() => setDeleteTarget(ws)}
                />
              </Grid2>
            )
          })}
        </Grid2>
      )}

      {/* ── 批量操作工具栏（固定在页面底部） ── */}
      {batchMode && selectedIds.size > 0 && (
        <Paper
          elevation={12}
          sx={{
            position: 'fixed',
            bottom: 20,
            left: '50%',
            transform: 'translateX(-50%)',
            zIndex: 1200,
            px: 2,
            py: 1,
            borderRadius: 3,
            display: 'inline-flex',
            alignItems: 'center',
            gap: 0.5,
            whiteSpace: 'nowrap',
            boxShadow: `0 8px 32px ${alpha(theme.palette.common.black, 0.2)}, 0 2px 8px ${alpha(theme.palette.common.black, 0.1)}`,
            backdropFilter: 'blur(12px)',
            bgcolor: alpha(theme.palette.background.paper, 0.97),
            border: `1px solid ${alpha(theme.palette.divider, 0.5)}`,
          }}
        >
          {/* 已选数量 */}
          <Typography variant="body2" sx={{ fontWeight: 700, color: 'primary.main', px: 0.5, flexShrink: 0 }}>
            {t('list.batchBar.selected', { count: selectedIds.size })}
          </Typography>

          <Box sx={{ width: '1px', height: 18, bgcolor: 'divider', mx: 0.5, flexShrink: 0 }} />

          {/* 操作按钮组 */}
          <Button
            size="small"
            variant="text"
            color="success"
            startIcon={<PlayArrowIcon sx={{ fontSize: '0.9rem !important' }} />}
            onClick={() => setBatchConfirmOp('start')}
            disabled={batchRunning}
            sx={{ minWidth: 0, px: 1, fontSize: '0.8rem' }}
          >
            {t('list.batchBar.start')}
          </Button>
          <Button
            size="small"
            variant="text"
            color="error"
            startIcon={<StopIcon sx={{ fontSize: '0.9rem !important' }} />}
            onClick={() => setBatchConfirmOp('stop')}
            disabled={batchRunning}
            sx={{ minWidth: 0, px: 1, fontSize: '0.8rem' }}
          >
            {t('list.batchBar.stop')}
          </Button>
          <Button
            size="small"
            variant="text"
            color="primary"
            startIcon={<RefreshIcon sx={{ fontSize: '0.9rem !important' }} />}
            onClick={() => setBatchConfirmOp('restart')}
            disabled={batchRunning}
            sx={{ minWidth: 0, px: 1, fontSize: '0.8rem' }}
          >
            {t('list.batchBar.restart')}
          </Button>
          <Button
            size="small"
            variant="text"
            color="warning"
            startIcon={<BuildIcon sx={{ fontSize: '0.9rem !important' }} />}
            onClick={() => setBatchConfirmOp('rebuild')}
            disabled={batchRunning}
            sx={{ minWidth: 0, px: 1, fontSize: '0.8rem' }}
          >
            {t('list.batchBar.rebuild')}
          </Button>
          <Button
            size="small"
            variant="text"
            startIcon={<RotateRightIcon sx={{ fontSize: '0.9rem !important' }} />}
            onClick={() => setBatchConfirmOp('resetSession')}
            disabled={batchRunning}
            sx={{ minWidth: 0, px: 1, fontSize: '0.8rem', color: 'text.secondary' }}
          >
            {t('list.batchBar.resetSession')}
          </Button>

          <Box sx={{ width: '1px', height: 18, bgcolor: 'divider', mx: 0.5, flexShrink: 0 }} />

          <Button
            size="small"
            variant="text"
            color="info"
            startIcon={<TuneIcon sx={{ fontSize: '0.9rem !important' }} />}
            onClick={() => setBatchPresetOpen(true)}
            disabled={batchRunning}
            sx={{ minWidth: 0, px: 1, fontSize: '0.8rem' }}
          >
            {t('list.batchBar.setPreset')}
          </Button>

          <Box sx={{ width: '1px', height: 18, bgcolor: 'divider', mx: 0.5, flexShrink: 0 }} />

          {/* 关闭按钮 */}
          <Tooltip title={t('list.batchBar.cancel')}>
            <IconButton size="small" onClick={exitBatchMode} sx={{ p: 0.5 }}>
              <CloseIcon sx={{ fontSize: '1rem' }} />
            </IconButton>
          </Tooltip>
        </Paper>
      )}

      {/* 创建对话框 */}
      <Dialog
        open={createOpen}
        onClose={() => !createMutation.isPending && setCreateOpen(false)}
        maxWidth="sm"
        fullWidth
      >
        <DialogTitle>{t('createDialog.title')}</DialogTitle>
        <DialogContent>
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2, pt: 1 }}>
            <Box sx={{ display: 'flex', gap: 1, alignItems: 'flex-start' }}>
              <TextField
                label={t('createDialog.nameLabel')}
                required
                fullWidth
                autoComplete="off"
                value={form.name}
                onChange={e => setForm(prev => ({ ...prev, name: e.target.value }))}
                disabled={createMutation.isPending}
              />
              <Tooltip title={t('createDialog.randomNameTooltip')}>
                <IconButton
                  onClick={() => setNameGenOpen(true)}
                  disabled={createMutation.isPending}
                  sx={{ mt: 1 }}
                >
                  <CasinoIcon />
                </IconButton>
              </Tooltip>
            </Box>
            <TextField
              label={t('createDialog.descLabel')}
              fullWidth
              multiline
              rows={2}
              autoComplete="off"
              value={form.description ?? ''}
              onChange={e => setForm(prev => ({ ...prev, description: e.target.value }))}
              disabled={createMutation.isPending}
            />
            <TextField
              label={t('createDialog.policyLabel')}
              select
              fullWidth
              value={form.runtime_policy ?? 'agent'}
              onChange={e =>
                setForm(prev => ({
                  ...prev,
                  runtime_policy: e.target.value as CreateWorkspaceBody['runtime_policy'],
                }))
              }
              disabled={createMutation.isPending}
            >
              <MenuItem value="agent">{t('createDialog.policyAgent')}</MenuItem>
              <MenuItem value="relaxed">{t('createDialog.policyRelaxed')}</MenuItem>
              <MenuItem value="strict">{t('createDialog.policyStrict')}</MenuItem>
            </TextField>
          </Box>
        </DialogContent>
        <DialogActions sx={{ px: 3, pb: 2 }}>
          <Button onClick={() => setCreateOpen(false)} disabled={createMutation.isPending}>
            {t('createDialog.cancel')}
          </Button>
          <Button
            variant="contained"
            onClick={handleCreate}
            disabled={createMutation.isPending || !form.name.trim()}
          >
            {createMutation.isPending ? <CircularProgress size={20} /> : t('createDialog.create')}
          </Button>
        </DialogActions>
      </Dialog>

      {/* 名称生成器对话框 */}
      <NameGeneratorDialog
        open={nameGenOpen}
        onClose={() => setNameGenOpen(false)}
        onSelect={(name) => {
          setForm(prev => ({ ...prev, name }))
          setNameGenOpen(false)
        }}
      />

      {/* 批量设置 CC 模型组对话框 */}
      <Dialog
        open={batchPresetOpen}
        onClose={() => !batchPresetRunning && setBatchPresetOpen(false)}
        maxWidth="sm"
        fullWidth
      >
        <DialogTitle>{t('list.batchPreset.title')}</DialogTitle>
        <DialogContent>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
            {t('list.batchPreset.hint', { count: selectedIds.size })}
          </Typography>
          <Autocomplete
            options={allPresets}
            value={batchPresetSelected}
            onChange={(_, val: CCModelPresetInfo | null) => setBatchPresetSelected(val)}
            getOptionLabel={opt => opt.name}
            isOptionEqualToValue={(opt, val) => opt.id === val.id}
            renderInput={params => (
              <TextField
                {...params}
                label={t('list.batchPreset.selectLabel')}
                placeholder={t('list.batchPreset.clearHint')}
              />
            )}
            noOptionsText={t('list.batchPreset.noPresets')}
          />
        </DialogContent>
        <DialogActions sx={{ px: 3, pb: 2 }}>
          <Button onClick={() => setBatchPresetOpen(false)} disabled={batchPresetRunning}>
            {t('list.batchPreset.cancel')}
          </Button>
          <Button
            variant="contained"
            onClick={handleBatchSetPreset}
            disabled={batchPresetRunning}
          >
            {batchPresetRunning ? <CircularProgress size={20} /> : t('list.batchPreset.confirm')}
          </Button>
        </DialogActions>
      </Dialog>

      {/* 删除确认对话框 */}
      <Dialog
        open={!!deleteTarget}
        onClose={() => !deleteMutation.isPending && setDeleteTarget(null)}
      >
        <DialogTitle>{t('deleteDialog.title')}</DialogTitle>
        <DialogContent>
          <DialogContentText>
            {t('deleteDialog.content', { name: deleteTarget?.name })}
          </DialogContentText>
        </DialogContent>
        <DialogActions sx={{ px: 3, pb: 2 }}>
          <Button onClick={() => setDeleteTarget(null)} disabled={deleteMutation.isPending}>
            {t('deleteDialog.cancel')}
          </Button>
          <Button
            variant="contained"
            color="error"
            onClick={() => deleteTarget && deleteMutation.mutate(deleteTarget.id)}
            disabled={deleteMutation.isPending}
          >
            {deleteMutation.isPending ? <CircularProgress size={20} /> : t('deleteDialog.delete')}
          </Button>
        </DialogActions>
      </Dialog>

      {/* 批量操作确认对话框 */}
      <Dialog
        open={!!batchConfirmOp}
        onClose={() => !batchRunning && setBatchConfirmOp(null)}
      >
        <DialogTitle>{t('list.batchConfirm.title')}</DialogTitle>
        <DialogContent>
          <DialogContentText>
            {batchConfirmOp && t('list.batchConfirm.content', {
              count: selectedIds.size,
              op: opLabels[batchConfirmOp],
            })}
          </DialogContentText>
        </DialogContent>
        <DialogActions sx={{ px: 3, pb: 2 }}>
          <Button onClick={() => setBatchConfirmOp(null)} disabled={batchRunning}>
            {t('list.batchConfirm.cancel')}
          </Button>
          <Button
            variant="contained"
            onClick={handleBatchConfirm}
            disabled={batchRunning}
          >
            {batchRunning ? <CircularProgress size={20} /> : t('list.batchConfirm.confirm')}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  )
}
