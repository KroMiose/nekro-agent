import { useState } from 'react'
import {
  Box,
  Button,
  Card,
  CardContent,
  CardActions,
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
  Stack,
  Divider,
  useTheme,
  alpha,
  Tooltip,
  IconButton,
  Skeleton,
} from '@mui/material'
import {
  Add as AddIcon,
  Delete as DeleteIcon,
  ArrowForward as ArrowForwardIcon,
  Workspaces as WorkspacesIcon,
  Memory as MemoryIcon,
  SettingsEthernet as PortIcon,
  Schedule as ScheduleIcon,
  CheckCircle as CheckCircleIcon,
  RemoveCircle as RemoveCircleIcon,
  ErrorOutline as ErrorOutlineIcon,
  Layers as LayersIcon,
  Casino as CasinoIcon,
} from '@mui/icons-material'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import {
  workspaceApi,
  WorkspaceSummary,
  CreateWorkspaceBody,
} from '../../services/api/workspace'
import { useNotification } from '../../hooks/useNotification'
import { CARD_VARIANTS, CHIP_VARIANTS, SCROLLBAR_VARIANTS } from '../../theme/variants'
import NameGeneratorDialog from '../../components/common/NameGeneratorDialog'
import { useTranslation } from 'react-i18next'

const defaultForm: CreateWorkspaceBody = {
  name: '',
  description: '',
  runtime_policy: 'agent',
}

function useStatusColor(status: WorkspaceSummary['status']) {
  const theme = useTheme()
  const map: Record<WorkspaceSummary['status'], string> = {
    active: theme.palette.success.main,
    stopped: theme.palette.text.secondary as string,
    failed: theme.palette.error.main,
    deleting: theme.palette.warning.main,
  }
  return map[status]
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

function StatusChip({ status }: { status: WorkspaceSummary['status'] }) {
  const { t } = useTranslation('workspace')
  const color = useStatusColor(status)
  return <Chip label={t(`status.${status}`)} size="small" sx={CHIP_VARIANTS.getCustomColorChip(color, true)} />
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
  onEnter,
  onDelete,
}: {
  ws: WorkspaceSummary
  onEnter: () => void
  onDelete: () => void
}) {
  const { t } = useTranslation('workspace')
  const statusColor = useStatusColor(ws.status)

  const imageLabel = ws.sandbox_image
    ? `${ws.sandbox_image}:${ws.sandbox_version || 'latest'}`
    : ws.sandbox_version
      ? `latest:${ws.sandbox_version}`
      : t('card.defaultImage')

  const containerShort = ws.container_name
    ? ws.container_name.replace(/^nekro-/, '')
    : null

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
        cursor: 'pointer',
        transition: 'all 0.2s ease',
        overflow: 'hidden',
        '&:hover': {
          transform: 'translateY(-2px)',
          boxShadow: `0 8px 24px ${alpha(statusColor, 0.15)}`,
        },
      }}
      onClick={onEnter}
    >
      {/* 状态色条 */}
      <Box sx={{ height: 3, bgcolor: statusColor, flexShrink: 0 }} />

      <CardContent sx={{ flexGrow: 1, p: 2, pb: 1 }}>
        {/* 工作区名称 + 状态点 */}
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
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

        {/* Status + Policy chips */}
        <Box sx={{ display: 'flex', gap: 0.75, mb: 1.5, flexWrap: 'wrap' }}>
          <StatusChip status={ws.status} />
          <PolicyChip policy={ws.runtime_policy} />
        </Box>

        {/* 描述 */}
        {ws.description ? (
          <Typography
            variant="body2"
            color="text.secondary"
            sx={{
              mb: 1.5,
              overflow: 'hidden',
              textOverflow: 'ellipsis',
              display: '-webkit-box',
              WebkitLineClamp: 2,
              WebkitBoxOrient: 'vertical',
              fontSize: '0.78rem',
              lineHeight: 1.55,
              minHeight: '2.4em',
            }}
          >
            {ws.description}
          </Typography>
        ) : (
          <Typography
            variant="body2"
            sx={{ mb: 1.5, fontSize: '0.78rem', color: 'text.disabled', fontStyle: 'italic', minHeight: '1.2em' }}
          >
            {t('card.noDescription')}
          </Typography>
        )}

        <Divider sx={{ mb: 1.25 }} />

        {/* 信息行 */}
        <Stack spacing={0.55}>
          {/* 镜像 */}
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.75 }}>
            <LayersIcon sx={{ fontSize: 13, color: 'text.disabled', flexShrink: 0 }} />
            <Typography variant="caption" color="text.secondary" sx={{ flexShrink: 0, minWidth: 28 }}>
              {t('card.image')}
            </Typography>
            <Tooltip title={imageLabel} placement="top-start">
              <Typography
                variant="caption"
                sx={{
                  fontFamily: 'monospace',
                  fontSize: '0.68rem',
                  overflow: 'hidden',
                  textOverflow: 'ellipsis',
                  whiteSpace: 'nowrap',
                  color: 'text.secondary',
                }}
              >
                {imageLabel}
              </Typography>
            </Tooltip>
          </Box>

          {/* 容器 + 端口 */}
          {(containerShort || ws.host_port) && (
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5 }}>
              {containerShort && (
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.75, flex: 1, minWidth: 0 }}>
                  <MemoryIcon sx={{ fontSize: 13, color: 'text.disabled', flexShrink: 0 }} />
                  <Tooltip title={ws.container_name ?? ''} placement="top-start">
                    <Typography
                      variant="caption"
                      sx={{
                        fontFamily: 'monospace',
                        fontSize: '0.68rem',
                        overflow: 'hidden',
                        textOverflow: 'ellipsis',
                        whiteSpace: 'nowrap',
                        color: 'text.secondary',
                      }}
                    >
                      {containerShort}
                    </Typography>
                  </Tooltip>
                </Box>
              )}
              {ws.host_port && (
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5, flexShrink: 0 }}>
                  <PortIcon sx={{ fontSize: 13, color: 'text.disabled' }} />
                  <Typography variant="caption" sx={{ fontFamily: 'monospace', fontSize: '0.68rem', color: 'text.secondary' }}>
                    :{ws.host_port}
                  </Typography>
                </Box>
              )}
            </Box>
          )}

          {/* 创建时间 */}
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.75 }}>
            <ScheduleIcon sx={{ fontSize: 13, color: 'text.disabled', flexShrink: 0 }} />
            <Typography variant="caption" color="text.secondary" sx={{ flexShrink: 0, minWidth: 28 }}>
              {t('card.createdAt')}
            </Typography>
            <Typography variant="caption" sx={{ fontSize: '0.68rem', color: 'text.secondary' }}>
              {createDate}
            </Typography>
          </Box>
        </Stack>
      </CardContent>

      <CardActions sx={{ px: 2, pb: 2, pt: 0.5, gap: 1 }} onClick={e => e.stopPropagation()}>
        <Button
          variant="contained"
          size="small"
          endIcon={<ArrowForwardIcon />}
          onClick={onEnter}
          sx={{ flexGrow: 1 }}
        >
          {t('card.enter')}
        </Button>
        <Button
          variant="outlined"
          size="small"
          color="error"
          startIcon={<DeleteIcon />}
          onClick={onDelete}
        >
          {t('card.delete')}
        </Button>
      </CardActions>
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

  const { data: workspaces = [], isLoading, error } = useQuery({
    queryKey: ['workspaces'],
    queryFn: workspaceApi.getList,
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

  const totalCount = workspaces.length
  const activeCount = workspaces.filter(w => w.status === 'active').length
  const stoppedCount = workspaces.filter(w => w.status === 'stopped').length
  const failedCount = workspaces.filter(w => w.status === 'failed' || w.status === 'deleting').length

  return (
    <Box sx={{ p: 3, height: '100%', overflow: 'auto', ...SCROLLBAR_VARIANTS.thin.styles }}>

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
            <Typography variant="caption" color="text.disabled" sx={{ flexShrink: 0 }}>
              {t('list.total', { count: workspaces.length })}
            </Typography>
          )}
        </Box>
      )}

      {/* 工作区列表 */}
      {isLoading ? (
        <Grid2 container spacing={2}>
          {[1, 2, 3].map(i => (
            <Grid2 size={{ xs: 12, sm: 6, md: 4 }} key={i}>
              <Skeleton variant="rounded" height={280} sx={{ borderRadius: 2 }} />
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
          {workspaces.map(ws => (
            <Grid2 size={{ xs: 12, sm: 6, md: 4 }} key={ws.id}>
              <WorkspaceCard
                ws={ws}
                onEnter={() => navigate(`/workspace/${ws.id}`)}
                onDelete={() => setDeleteTarget(ws)}
              />
            </Grid2>
          ))}
        </Grid2>
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
    </Box>
  )
}
