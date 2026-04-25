import React, { useState, useRef, useEffect } from 'react'
import {
  Alert,
  Box,
  Card,
  CardContent,
  Typography,
  Chip,
  TextField,
  CircularProgress,
  Stack,
  Divider,
  Tooltip,
  Autocomplete,
  Skeleton,
  alpha,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
} from '@mui/material'
import {
  ArrowForward as ArrowForwardIcon,
  Tune as TuneIcon,
  OpenInNew as OpenInNewIcon,
  LinkOff as LinkOffIcon,
  Hub as HubIcon,
  Extension as ExtensionIcon,
  SettingsEthernet as McpIcon,
  AccessTime as HeartbeatIcon,
  Forum as ForumIcon,
  Storage as StorageIcon,
  Memory as MemoryIcon,
  CloudDownload as CloudDownloadIcon,
  Psychology as PsychologyIcon,
  InfoOutlined as InfoOutlineIcon,
  Star as StarIcon,
  StarBorder as StarBorderIcon,
} from '@mui/icons-material'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import {
  workspaceApi,
  WorkspaceDetail,
  SandboxStatus,
  commApi,
  ImagePullMessage,
  WorkspaceOverviewStats,
  BoundChannel,
} from '../../../services/api/workspace'
import { ccModelPresetApi } from '../../../services/api/cc-model-preset'
import { pluginsApi } from '../../../services/api/plugins'
import { useNotification } from '../../../hooks/useNotification'
import { CARD_VARIANTS, CHIP_VARIANTS } from '../../../theme/variants'
import { useTheme } from '@mui/material/styles'
import { useTranslation } from 'react-i18next'
import { pluginsManagementPath } from '../../../router/routes'
import ActionButton from '../../../components/common/ActionButton'
import IconActionButton from '../../../components/common/IconActionButton'
import { useChannelDirectoryContext } from '../../../contexts/ChannelDirectoryContext'

type ChannelOption = {
  chat_key: string
  channel_name: string | null
}

// ─────────────────────────────────────────────────────────────
// CapabilityCard: 能力速览卡（带副标题）
// ─────────────────────────────────────────────────────────────

function CapabilityCard({
  icon,
  label,
  value,
  subtitle,
  color,
  loading,
  onClick,
}: {
  icon: React.ReactNode
  label: string
  value?: string | number
  subtitle?: string
  color: string
  loading?: boolean
  onClick?: () => void
}) {
  const theme = useTheme()
  return (
    <Card
      sx={{
        ...CARD_VARIANTS.default.styles,
        minWidth: 0,
        height: '100%',
        cursor: onClick ? 'pointer' : 'default',
        transition: 'transform 0.15s ease, box-shadow 0.15s ease',
        '&:hover': onClick
          ? {
              transform: 'translateY(-2px)',
              boxShadow: `0 6px 20px ${alpha(color, 0.18)}`,
            }
          : undefined,
      }}
      onClick={onClick}
    >
      <CardContent sx={{ p: { xs: 1.25, sm: 2 }, '&:last-child': { pb: { xs: 1.25, sm: 2 } } }}>
        <Box sx={{ display: 'flex', alignItems: 'flex-start', gap: { xs: 1, sm: 1.5 }, minWidth: 0 }}>
          <Box
            sx={{
              color,
              bgcolor: alpha(color, 0.12),
              borderRadius: 1.5,
              p: { xs: 0.75, sm: 1 },
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              flexShrink: 0,
              mt: 0.25,
            }}
          >
            {icon}
          </Box>
          <Box sx={{ minWidth: 0, flex: 1 }}>
            {loading ? (
              <Skeleton variant="text" width={32} height={28} />
            ) : (
              <Typography variant="h6" fontWeight={700} lineHeight={1.2}>
                {value ?? '—'}
              </Typography>
            )}
            <Typography variant="caption" color="text.secondary" sx={{ display: 'block', lineHeight: 1.35 }}>
              {label}
            </Typography>
            {subtitle && !loading && (
              <Typography
                variant="caption"
                sx={{
                  display: '-webkit-box',
                  color: alpha(theme.palette.text.secondary as string, 0.7),
                  fontSize: '0.68rem',
                  lineHeight: 1.35,
                  mt: 0.2,
                  overflow: 'hidden',
                  WebkitLineClamp: 2,
                  WebkitBoxOrient: 'vertical',
                  wordBreak: 'break-word',
                }}
              >
                {subtitle}
              </Typography>
            )}
          </Box>
          {onClick && (
            <ArrowForwardIcon sx={{ fontSize: 14, color: 'text.disabled', flexShrink: 0, mt: 0.5 }} />
          )}
        </Box>
      </CardContent>
    </Card>
  )
}

// ─────────────────────────────────────────────────────────────
// InfoRow
// ─────────────────────────────────────────────────────────────

function InfoRow({
  label,
  value,
  mono,
  children,
}: {
  label: string
  value?: string
  mono?: boolean
  children?: React.ReactNode
}) {
  return (
    <Box sx={{ display: 'flex', flexDirection: { xs: 'column', sm: 'row' }, gap: { xs: 0.25, sm: 1 }, alignItems: 'flex-start', minWidth: 0 }}>
      <Typography
        variant="body2"
        color="text.secondary"
        sx={{ minWidth: { xs: 0, sm: 80 }, flexShrink: 0, pt: '1px', fontSize: { xs: '0.78rem', sm: '0.875rem' } }}
      >
        {label}
      </Typography>
      {children ?? (
        <Typography
          variant="body2"
          sx={{
            fontFamily: mono ? 'monospace' : undefined,
            wordBreak: 'break-all',
            fontSize: mono ? '0.8rem' : undefined,
            minWidth: 0,
          }}
        >
          {value ?? '—'}
        </Typography>
      )}
    </Box>
  )
}

// ─────────────────────────────────────────────────────────────
// SectionHeader
// ─────────────────────────────────────────────────────────────

function SectionHeader({
  title,
  action,
}: {
  title: string
  action?: React.ReactNode
}) {
  return (
    <Box sx={{ display: 'flex', alignItems: 'center', mb: 1.5 }}>
      <Typography
        variant="caption"
        sx={{
          fontWeight: 700,
          color: 'text.secondary',
          textTransform: 'uppercase',
          fontSize: '0.68rem',
          letterSpacing: 0.8,
          flexGrow: 1,
        }}
      >
        {title}
      </Typography>
      {action}
    </Box>
  )
}

// ─────────────────────────────────────────────────────────────
// OverviewTab
// ─────────────────────────────────────────────────────────────

export default function OverviewTab({
  workspace,
  sandboxStatus,
  ccWorking,
  ccCurrentTool,
  onNavigateToSandbox,
  onNavigateToConfig,
  onNavigateToExtensions,
  onNavigateToComm,
  onNavigateToMcp,
  onNavigateToResources,
  onNavigateToMemory,
  onNavigateToPrompt,
}: {
  workspace: WorkspaceDetail
  sandboxStatus: SandboxStatus | null
  ccWorking?: boolean
  ccCurrentTool?: string | null
  onNavigateToSandbox: () => void
  onNavigateToConfig: () => void
  onNavigateToExtensions: () => void
  onNavigateToComm?: () => void
  onNavigateToMcp?: () => void
  onNavigateToResources?: () => void
  onNavigateToMemory?: () => void
  onNavigateToPrompt?: () => void
}) {
  const theme = useTheme()
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const notification = useNotification()
  const { t } = useTranslation('workspace')
  const { channels: allChannels, channelMap, isLoading: channelsDirectoryLoading } = useChannelDirectoryContext()

  // ── 镜像状态检查 ──
  const [pullDialogOpen, setPullDialogOpen] = useState(false)
  const [pullConfirmOpen, setPullConfirmOpen] = useState(false)
  const imageCheckQuery = useQuery({
    queryKey: ['sandbox-image-check', workspace.id],
    queryFn: () => workspaceApi.checkSandboxImage(workspace.id),
    staleTime: 60000,
  })

  // ── CC 模型预设 ──
  const { data: allPresets = [] } = useQuery({
    queryKey: ['cc-model-presets'],
    queryFn: () => ccModelPresetApi.getList(),
  })
  const currentPreset = workspace.cc_model_preset_id != null
    ? allPresets.find(p => p.id === workspace.cc_model_preset_id)
    : allPresets.find(p => p.is_default)

  // ── cc_workspace 插件 ──
  const pluginsQuery = useQuery({
    queryKey: ['plugins'],
    queryFn: () => pluginsApi.getPlugins(),
  })
  const ccWorkspacePlugin = (pluginsQuery.data ?? []).find(
    plugin =>
      plugin.id === 'cc_workspace' ||
      plugin.id.endsWith('.cc_workspace') ||
      plugin.moduleName === 'cc_workspace',
  )
  const ccWorkspacePluginUnavailable = ccWorkspacePlugin ? !ccWorkspacePlugin.enabled : false

  // ── 绑定频道 ──
  const { data: boundChannels = [], isLoading: channelsLoading } = useQuery({
    queryKey: ['workspace-channels', workspace.id],
    queryFn: () => workspaceApi.getBoundChannels(workspace.id),
  })
  const [selectedChannel, setSelectedChannel] = useState<ChannelOption | null>(null)
  const [editingDesc, setEditingDesc] = useState<Record<string, string>>({})
  const [editingKey, setEditingKey] = useState<string | null>(null)
  const { data: commStats } = useQuery({
    queryKey: ['workspace-comm-count', workspace.id],
    queryFn: () => commApi.getHistory(workspace.id, 1),
    staleTime: 30000,
  })

  // ── 概览统计聚合 ──
  const { data: overviewStats, isLoading: statsLoading } = useQuery<WorkspaceOverviewStats>({
    queryKey: ['workspace-overview-stats', workspace.id],
    queryFn: () => workspaceApi.getOverviewStats(workspace.id),
    staleTime: 30000,
  })

  // 镜像未拉取警告
  const imageNotReady = imageCheckQuery.data?.exists === false

  // 主频道信息
  const primaryChannel = boundChannels.find(ch => ch.is_primary) ?? boundChannels[0] ?? null
  const autocompleteOptions = allChannels.map(ch => ({
    chat_key: ch.chat_key,
    channel_name: ch.channel_name,
  }))
  const alreadyBound = selectedChannel
    ? boundChannels.some(item => item.chat_key === selectedChannel.chat_key)
    : false

  // 技能统计
  const skillCount = workspace.skill_count ?? 0
  const dynamicSkillCount = overviewStats?.dynamic_skill_count ?? 0
  const commCount = commStats?.total ?? 0

  // 记忆统计
  const memoryTotal = overviewStats
    ? overviewStats.memory_paragraph_count + overviewStats.memory_entity_count + overviewStats.memory_relation_count
    : 0

  const containerName = sandboxStatus?.container_name ?? workspace.container_name
  const hostPort = sandboxStatus?.host_port ?? workspace.host_port
  const versionInfo = [sandboxStatus?.cc_version ? `${sandboxStatus.cc_version} (Sandbox)` : null, sandboxStatus?.claude_code_version ? `${sandboxStatus.claude_code_version} (Claude Code)` : null]
    .filter((value): value is string => value !== null)
    .join(' | ')
  const knownStatuses = ['active', 'stopped', 'failed', 'deleting'] as const
  const workspaceStatusLabel = knownStatuses.includes(workspace.status as (typeof knownStatuses)[number])
    ? t(`status.${workspace.status}`)
    : workspace.status

  // 沙盒状态颜色
  const statusColor =
    workspace.status === 'active'
      ? theme.palette.success.main
      : workspace.status === 'failed'
        ? theme.palette.error.main
        : theme.palette.text.secondary as string

  // 运行策略标签
  const policyLabel =
    workspace.runtime_policy === 'agent'
      ? t('policy.agent')
      : workspace.runtime_policy === 'relaxed'
        ? t('policy.relaxed')
        : workspace.runtime_policy === 'strict'
          ? t('policy.strict')
          : workspace.runtime_policy

  const bindMutation = useMutation({
    mutationFn: (chatKey: string) => workspaceApi.bindChannel(workspace.id, chatKey),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['workspace-channels', workspace.id] })
      notification.success(t('detail.overview.channels.bindSuccess'))
      setSelectedChannel(null)
    },
    onError: (err: Error) => notification.error(t('detail.overview.channels.bindFailed', { message: err.message })),
  })

  const unbindMutation = useMutation({
    mutationFn: (chatKey: string) => workspaceApi.unbindChannel(workspace.id, chatKey),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['workspace-channels', workspace.id] })
      notification.success(t('detail.overview.channels.unbindSuccess'))
    },
    onError: (err: Error) => notification.error(t('detail.overview.channels.unbindFailed', { message: err.message })),
  })

  const annotationMutation = useMutation({
    mutationFn: (body: { chat_key: string; description: string; is_primary: boolean }) =>
      workspaceApi.updateChannelAnnotation(workspace.id, body),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['workspace-channels', workspace.id] })
    },
    onError: (err: Error) => notification.error(t('detail.overview.channels.annotationFailed', { message: err.message })),
  })

  const handleDescBlur = (channel: BoundChannel) => {
    const newDesc = editingDesc[channel.chat_key] ?? channel.description
    if (newDesc !== channel.description) {
      annotationMutation.mutate({
        chat_key: channel.chat_key,
        description: newDesc,
        is_primary: channel.is_primary,
      })
    }
    setEditingKey(null)
  }

  const handleSetPrimary = (channel: BoundChannel) => {
    if (channel.is_primary) return
    annotationMutation.mutate({
      chat_key: channel.chat_key,
      description: channel.description,
      is_primary: true,
    })
  }

  return (
    <Stack spacing={2}>
      {/* ── 顶部告警条 ── */}
      {ccWorkspacePluginUnavailable && (
        <Alert
          severity="warning"
          action={
            <ActionButton
              tone="secondary"
              size="small"
              onClick={() => navigate(pluginsManagementPath('cc_workspace'))}
            >
              {t('detail.overview.ccPluginAlert.action')}
            </ActionButton>
          }
        >
          {t('detail.overview.ccPluginAlert.message')}
        </Alert>
      )}
      {imageNotReady && (
        <Alert
          severity="info"
          action={
            <ActionButton
              tone="secondary"
              size="small"
              startIcon={<CloudDownloadIcon sx={{ fontSize: 14 }} />}
              onClick={() => setPullConfirmOpen(true)}
            >
              {t('detail.errors.image.pullDialog.pullBtn')}
            </ActionButton>
          }
        >
          {t('detail.errors.image.notPulled')}：{imageCheckQuery.data?.image ?? ''}
        </Alert>
      )}
      {!overviewStats?.memory_enabled && !statsLoading && (
        <Alert severity="info" icon={<MemoryIcon fontSize="small" />}>
          {t('detail.overview.memoryNotEnabled')}
        </Alert>
      )}

      {/* 拉取确认对话框 */}
      <Dialog open={pullConfirmOpen} onClose={() => setPullConfirmOpen(false)} maxWidth="xs" fullWidth>
        <DialogTitle sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <CloudDownloadIcon fontSize="small" />
          {t('detail.errors.image.pullDialog.confirmTitle')}
        </DialogTitle>
        <DialogContent>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
            {t('detail.errors.image.pullDialog.confirmHint')}
          </Typography>
          <Typography
            variant="body2"
            sx={{ fontFamily: 'monospace', bgcolor: 'action.hover', px: 1.5, py: 1, borderRadius: 1 }}
          >
            {imageCheckQuery.data?.image ?? ''}
          </Typography>
        </DialogContent>
        <DialogActions>
          <ActionButton tone="secondary" size="small" onClick={() => setPullConfirmOpen(false)}>
            {t('detail.errors.image.pullDialog.cancel')}
          </ActionButton>
          <ActionButton
            tone="primary"
            size="small"
            startIcon={<CloudDownloadIcon />}
            onClick={() => {
              setPullConfirmOpen(false)
              setPullDialogOpen(true)
            }}
          >
            {t('detail.errors.image.pullDialog.pullBtn')}
          </ActionButton>
        </DialogActions>
      </Dialog>

      {/* 拉取进度对话框 */}
      <ImagePullDialog
        open={pullDialogOpen}
        onClose={() => {
          setPullDialogOpen(false)
          void imageCheckQuery.refetch()
        }}
        workspaceId={workspace.id}
        image={imageCheckQuery.data?.image ?? ''}
      />

      {/* ── 能力速览卡 ── */}
      <Box
        sx={{
          display: 'grid',
          gridTemplateColumns: {
            xs: 'repeat(2, minmax(0, 1fr))',
            sm: 'repeat(3, minmax(0, 1fr))',
            lg: 'repeat(6, minmax(0, 1fr))',
          },
          gap: { xs: 1, sm: 1.5 },
        }}
      >
        <CapabilityCard
          icon={<HubIcon sx={{ fontSize: 20 }} />}
          label={t('detail.overview.statCards.channels')}
          value={channelsLoading ? undefined : boundChannels.length}
          subtitle={primaryChannel ? channelMap.get(primaryChannel.chat_key)?.channel_name ?? primaryChannel.chat_key : undefined}
          color={theme.palette.primary.main}
          loading={channelsLoading}
          onClick={onNavigateToConfig}
        />
        <CapabilityCard
          icon={<ExtensionIcon sx={{ fontSize: 20 }} />}
          label={t('detail.overview.statCards.skills')}
          value={skillCount}
          subtitle={dynamicSkillCount > 0 ? t('detail.overview.dynamicSkillSuffix', { count: dynamicSkillCount }) : undefined}
          color={theme.palette.success.main}
          loading={statsLoading && skillCount === 0}
          onClick={onNavigateToExtensions}
        />
        <CapabilityCard
          icon={<StorageIcon sx={{ fontSize: 20 }} />}
          label={t('detail.overview.statCards.resources')}
          value={statsLoading ? undefined : (overviewStats?.resource_binding_count ?? 0)}
          color={theme.palette.warning.main}
          loading={statsLoading}
          onClick={onNavigateToResources}
        />
        <CapabilityCard
          icon={<PsychologyIcon sx={{ fontSize: 20 }} />}
          label={t('detail.overview.statCards.memory')}
          value={statsLoading ? undefined : memoryTotal}
          subtitle={
            overviewStats && overviewStats.memory_reinforcement_7d > 0
              ? t('detail.overview.reinforcement7dSuffix', { count: overviewStats.memory_reinforcement_7d })
              : undefined
          }
          color={theme.palette.secondary.main}
          loading={statsLoading}
          onClick={onNavigateToMemory}
        />
        <CapabilityCard
          icon={<ForumIcon sx={{ fontSize: 20 }} />}
          label={t('detail.overview.statCards.comm')}
          value={commCount}
          subtitle={ccWorking ? (ccCurrentTool || t('detail.overview.commStatus.active')) : t('detail.overview.commStatus.idle')}
          color={theme.palette.info.main}
          onClick={onNavigateToComm}
        />
        <CapabilityCard
          icon={<McpIcon sx={{ fontSize: 20 }} />}
          label={t('detail.overview.statCards.mcp')}
          value={workspace.mcp_count}
          color={theme.palette.info.main}
          onClick={onNavigateToMcp}
        />
      </Box>

      {/* ── 双列：工作区身份 + CC 运行状态 ── */}
      <Box
        sx={{
          display: 'grid',
          gridTemplateColumns: { xs: '1fr', lg: 'repeat(2, minmax(0, 1fr))' },
          gap: { xs: 1.5, sm: 2 },
          alignItems: 'stretch',
        }}
      >
        {/* 左：工作区身份 */}
        <Card sx={{ ...CARD_VARIANTS.default.styles, minWidth: 0 }}>
          <CardContent sx={{ p: { xs: 2, sm: 3 } }}>
            <Box sx={{ mb: 1.5 }}>
              <Typography variant="subtitle1" fontWeight={700} lineHeight={1.25}>
                {workspace.name}
              </Typography>
              {workspace.description ? (
                <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5, lineHeight: 1.55, wordBreak: 'break-word' }}>
                  {workspace.description}
                </Typography>
              ) : (
                <Typography variant="body2" color="text.disabled" sx={{ mt: 0.5, fontStyle: 'italic' }}>
                  {t('detail.overview.noDescription')}
                </Typography>
              )}
            </Box>
            <Divider sx={{ mb: 1.5 }} />
            <Stack spacing={0.85}>
              <InfoRow label={t('detail.overview.infoRows.id')} value={String(workspace.id)} mono />
              <InfoRow label={t('detail.overview.infoRows.policy')}>
                <Chip
                  label={policyLabel}
                  size="small"
                  sx={CHIP_VARIANTS.base(true)}
                />
              </InfoRow>
              <InfoRow label={t('detail.overview.infoRows.image')}>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, flexWrap: 'wrap', minWidth: 0 }}>
                  <Typography variant="body2" sx={{ fontFamily: 'monospace', fontSize: '0.8rem', wordBreak: 'break-all' }}>
                    {imageCheckQuery.data?.image ?? `${workspace.sandbox_image || t('detail.overview.defaultImage')}:${workspace.sandbox_version || 'latest'}`}
                  </Typography>
                  {imageCheckQuery.isLoading ? (
                    <CircularProgress size={12} />
                  ) : imageCheckQuery.data?.exists === false ? (
                    <Chip
                      label={t('detail.errors.image.notPulled')}
                      size="small"
                      icon={<CloudDownloadIcon />}
                      onClick={() => setPullConfirmOpen(true)}
                      sx={{ cursor: 'pointer', ...CHIP_VARIANTS.getCustomColorChip(theme.palette.warning.main, true) as object }}
                    />
                  ) : imageCheckQuery.data?.exists === true ? (
                    <Chip
                      label={t('detail.errors.image.ready')}
                      size="small"
                      sx={CHIP_VARIANTS.getCustomColorChip(theme.palette.success.main, true) as object}
                    />
                  ) : null}
                </Box>
              </InfoRow>
              <InfoRow label={t('detail.overview.infoRows.createdAt')} value={new Date(workspace.create_time).toLocaleString()} />
              <InfoRow label={t('detail.overview.infoRows.updatedAt')} value={new Date(workspace.update_time).toLocaleString()} />
            </Stack>
          </CardContent>
        </Card>

        {/* 右：沙盒运行摘要 */}
        <Card sx={{ ...CARD_VARIANTS.default.styles, minWidth: 0 }}>
          <CardContent sx={{ p: { xs: 2, sm: 3 } }}>
            <Box sx={{ display: 'flex', alignItems: 'center', mb: 1.5, gap: 1, flexWrap: 'wrap' }}>
              <Typography variant="subtitle2" fontWeight={600} sx={{ flexGrow: 1 }}>
                {t('detail.overview.sections.sandboxStatus')}
              </Typography>
              <ActionButton
                tone="secondary"
                size="small"
                endIcon={<ArrowForwardIcon sx={{ fontSize: 14 }} />}
                onClick={onNavigateToSandbox}
                sx={{ minWidth: 0, px: 1.2, fontSize: '0.75rem', width: { xs: '100%', sm: 'auto' } }}
              >
                {t('detail.overview.manage')}
              </ActionButton>
            </Box>
            <Divider sx={{ mb: 1.5 }} />
            <Stack spacing={0.85}>
              <InfoRow label={t('detail.overview.infoRows.sandboxStatus')}>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, minWidth: 0, flexWrap: 'wrap' }}>
                  <Chip
                    label={workspaceStatusLabel}
                    size="small"
                    sx={CHIP_VARIANTS.getCustomColorChip(statusColor, true) as object}
                  />
                  <Typography
                    variant="body2"
                    sx={{ fontFamily: 'monospace', fontSize: '0.8rem', wordBreak: 'break-all', minWidth: 0 }}
                  >
                    {containerName ?? '—'}
                  </Typography>
                </Box>
              </InfoRow>
              <InfoRow label={t('detail.overview.infoRows.hostPort')} value={hostPort ? String(hostPort) : '—'} mono />
              <InfoRow label={t('detail.overview.infoRows.sessionId')} value={sandboxStatus?.session_id ?? '—'} mono />
              <InfoRow label={t('detail.overview.infoRows.versionInfo')} value={versionInfo || '—'} mono />
              <InfoRow label={t('detail.overview.infoRows.modelGroup')}>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5, minWidth: 0, width: '100%' }}>
                  <Typography
                    variant="body2"
                    sx={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', fontSize: '0.82rem', minWidth: 0 }}
                  >
                    {currentPreset ? currentPreset.name : allPresets.length === 0 ? t('detail.overview.loading') : t('detail.overview.notConfigured')}
                  </Typography>
                  {currentPreset?.is_default && (
                    <Typography variant="caption" color="primary" sx={{ flexShrink: 0 }}>
                      {t('detail.overview.defaultTag')}
                    </Typography>
                  )}
                  <Tooltip title={t('detail.overview.tooltips.switchConfig')}>
                    <IconActionButton size="small" onClick={onNavigateToConfig} sx={{ ml: 0.25 }}>
                      <TuneIcon sx={{ fontSize: 14 }} />
                    </IconActionButton>
                  </Tooltip>
                  <Tooltip title={t('detail.overview.tooltips.managePresets')}>
                    <IconActionButton size="small" onClick={() => navigate('/settings/models?tab=cc')}>
                      <OpenInNewIcon sx={{ fontSize: 14 }} />
                    </IconActionButton>
                  </Tooltip>
                </Box>
              </InfoRow>
              {workspace.last_heartbeat && (
                <InfoRow label={t('detail.overview.infoRows.lastHeartbeat')}>
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5, minWidth: 0 }}>
                    <HeartbeatIcon sx={{ fontSize: 14, color: 'text.disabled' }} />
                    <Typography variant="body2" sx={{ fontSize: '0.82rem', wordBreak: 'break-word' }}>
                      {new Date(workspace.last_heartbeat).toLocaleString()}
                    </Typography>
                  </Box>
                </InfoRow>
              )}
            </Stack>
            {workspace.last_error && (
              <Box
                sx={{
                  mt: 1.5,
                  py: 0.5,
                  px: 1.5,
                  borderRadius: 1,
                  border: '1px solid',
                  borderColor: 'error.main',
                  bgcolor: alpha(theme.palette.error.main, 0.08),
                }}
              >
                <Typography variant="caption" sx={{ wordBreak: 'break-all', color: 'error.main' }}>
                  {workspace.last_error}
                </Typography>
              </Box>
            )}
          </CardContent>
        </Card>
      </Box>

      {/* ── 频道绑定 ── */}
      <Card sx={CARD_VARIANTS.default.styles}>
        <CardContent sx={{ p: { xs: 2, sm: 3 } }}>
          <SectionHeader title={t('detail.overview.channels.title')} />

          <Box sx={{ display: 'flex', flexDirection: { xs: 'column', sm: 'row' }, gap: 1, mb: 1.5 }}>
            <Autocomplete
              fullWidth
              options={autocompleteOptions}
              value={selectedChannel}
              onChange={(_, val) => setSelectedChannel(val)}
              getOptionLabel={opt => (
                opt.channel_name ? `${opt.channel_name} (${opt.chat_key})` : opt.chat_key
              )}
              isOptionEqualToValue={(opt, val) => opt.chat_key === val.chat_key}
              getOptionDisabled={opt => boundChannels.some(item => item.chat_key === opt.chat_key)}
              renderInput={params => (
                <TextField
                  {...params}
                  size="small"
                  placeholder={t('detail.overview.channels.searchPlaceholder')}
                  autoComplete="off"
                  InputProps={{
                    ...params.InputProps,
                    endAdornment: (
                      <>
                        {channelsDirectoryLoading ? <CircularProgress color="inherit" size={16} /> : null}
                        {params.InputProps.endAdornment}
                      </>
                    ),
                  }}
                />
              )}
              renderOption={(props, opt) => (
                <Box component="li" {...props} key={opt.chat_key}>
                  <Box>
                    {opt.channel_name && (
                      <Typography variant="body2" sx={{ fontWeight: 500 }}>
                        {opt.channel_name}
                      </Typography>
                    )}
                    <Typography
                      variant="caption"
                      color="text.secondary"
                      sx={{ fontFamily: 'monospace' }}
                    >
                      {opt.chat_key}
                    </Typography>
                  </Box>
                </Box>
              )}
              noOptionsText={t('detail.overview.channels.noOptions')}
            />
            <ActionButton
              tone="secondary"
              size="small"
              disabled={!selectedChannel || alreadyBound || bindMutation.isPending}
              onClick={() => selectedChannel && bindMutation.mutate(selectedChannel.chat_key)}
              sx={{ minWidth: 64, flexShrink: 0, width: { xs: '100%', sm: 'auto' } }}
            >
              {bindMutation.isPending ? (
                <CircularProgress size={14} />
              ) : alreadyBound ? (
                t('detail.overview.channels.bound')
              ) : (
                t('detail.overview.channels.bind')
              )}
            </ActionButton>
          </Box>

          <Divider sx={{ mb: 1.5 }} />

          {channelsLoading ? (
            <Box sx={{ display: 'flex', justifyContent: 'center', py: 1.5 }}>
              <CircularProgress size={18} />
            </Box>
          ) : boundChannels.length === 0 ? (
            <Typography variant="body2" color="text.secondary" sx={{ py: 1 }}>
              {t('detail.overview.channels.noChannels')}
            </Typography>
          ) : (
            <Stack spacing={0.75}>
              {boundChannels.map(channel => {
                const info = channelMap.get(channel.chat_key)
                const isOnlyChannel = boundChannels.length === 1
                const currentDesc = editingKey === channel.chat_key
                  ? (editingDesc[channel.chat_key] ?? channel.description)
                  : channel.description
                return (
                  <Box
                    key={channel.chat_key}
                    sx={{
                      display: 'flex',
                      flexDirection: 'column',
                      px: 1.5,
                      py: 1,
                      borderRadius: 1,
                      border: '1px solid',
                      borderColor: channel.is_primary ? 'primary.main' : 'divider',
                      bgcolor: channel.is_primary ? alpha(theme.palette.primary.main, 0.04) : undefined,
                      gap: 0.5,
                      transition: 'border-color 0.2s',
                    }}
                  >
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                      <Tooltip title={channel.chat_key} placement="top" arrow>
                        <Typography
                          variant="body2"
                          sx={{
                            fontWeight: 600,
                            lineHeight: 1.3,
                            textDecoration: 'underline',
                            textDecorationStyle: 'dotted',
                            cursor: 'help',
                            flexShrink: 0,
                          }}
                        >
                          {info?.channel_name ?? channel.chat_key}
                        </Typography>
                      </Tooltip>
                      {channel.is_primary && (
                        <Chip
                          label={t('detail.overview.channels.primaryTag')}
                          size="small"
                          color="primary"
                          sx={{ ...CHIP_VARIANTS.base(true), height: 18, fontSize: '0.68rem' }}
                        />
                      )}
                      {info?.chat_type && (
                        <Chip
                          label={info.chat_type}
                          size="small"
                          sx={{ ...CHIP_VARIANTS.base(true), height: 18, fontSize: '0.68rem' }}
                        />
                      )}
                      {info?.is_active === false && (
                        <Chip
                          label={t('detail.overview.channels.disabled')}
                          size="small"
                          color="warning"
                          sx={{ ...CHIP_VARIANTS.base(true), height: 18, fontSize: '0.68rem' }}
                        />
                      )}
                      <Box sx={{ flexGrow: 1 }} />
                      <Tooltip
                        title={
                          isOnlyChannel
                            ? t('detail.overview.channels.primaryAutoTooltip')
                            : channel.is_primary
                              ? t('detail.overview.channels.isPrimaryTooltip')
                              : t('detail.overview.channels.setPrimaryTooltip')
                          }
                      >
                        <span>
                          <IconActionButton
                            size="small"
                            tone={channel.is_primary ? 'primary' : 'subtle'}
                            disabled={isOnlyChannel || channel.is_primary || annotationMutation.isPending}
                            onClick={() => handleSetPrimary(channel)}
                            sx={{ p: 0.5 }}
                            title={
                              isOnlyChannel
                                ? t('detail.overview.channels.primaryAutoTooltip')
                                : channel.is_primary
                                  ? t('detail.overview.channels.isPrimaryTooltip')
                                  : t('detail.overview.channels.setPrimaryTooltip')
                            }
                          >
                            {channel.is_primary || isOnlyChannel ? (
                              <StarIcon sx={{ fontSize: 16 }} />
                            ) : (
                              <StarBorderIcon sx={{ fontSize: 16 }} />
                            )}
                          </IconActionButton>
                        </span>
                      </Tooltip>
                      <Tooltip title={t('detail.overview.channels.unbindTooltip')}>
                        <IconActionButton
                          tone="danger"
                          size="small"
                          disabled={unbindMutation.isPending}
                          onClick={() => unbindMutation.mutate(channel.chat_key)}
                          sx={{ p: 0.5 }}
                        >
                          <LinkOffIcon sx={{ fontSize: 16 }} />
                        </IconActionButton>
                      </Tooltip>
                    </Box>
                    <TextField
                      size="small"
                      variant="standard"
                      fullWidth
                      placeholder={t('detail.overview.channels.descPlaceholder')}
                      value={currentDesc}
                      onFocus={() => {
                        setEditingKey(channel.chat_key)
                        setEditingDesc(prev => ({ ...prev, [channel.chat_key]: channel.description }))
                      }}
                      onChange={event => setEditingDesc(prev => ({ ...prev, [channel.chat_key]: event.target.value }))}
                      onBlur={() => handleDescBlur(channel)}
                      onKeyDown={event => {
                        if (event.key === 'Enter') (event.target as HTMLInputElement).blur()
                        if (event.key === 'Escape') {
                          setEditingDesc(prev => ({ ...prev, [channel.chat_key]: channel.description }))
                          setEditingKey(null)
                        }
                      }}
                      slotProps={{
                        input: {
                          sx: {
                            fontSize: '0.78rem',
                            color: 'text.secondary',
                            '&:before': { borderBottomStyle: 'dashed' },
                          },
                        },
                      }}
                    />
                  </Box>
                )
              })}
            </Stack>
          )}
        </CardContent>
      </Card>

      {/* ── 协作现状摘要 ── */}
      <Card sx={CARD_VARIANTS.default.styles}>
        <CardContent sx={{ p: { xs: 2, sm: 3 } }}>
          <SectionHeader
            title={t('detail.overview.sections.naContext')}
            action={
              <ActionButton
                tone="secondary"
                size="small"
                endIcon={<ArrowForwardIcon sx={{ fontSize: 14 }} />}
                onClick={onNavigateToPrompt}
                sx={{ minWidth: 0, px: 1.2, fontSize: '0.75rem' }}
              >
                {t('detail.overview.viewEdit')}
              </ActionButton>
            }
          />
          {statsLoading ? (
            <Box sx={{ display: 'flex', gap: 1, alignItems: 'center' }}>
              <CircularProgress size={14} />
              <Typography variant="body2" color="text.secondary">{t('detail.overview.loading')}</Typography>
            </Box>
          ) : overviewStats?.na_context_preview ? (
            <Box>
              <Typography
                variant="body2"
                sx={{
                  whiteSpace: 'pre-line',
                  color: 'text.secondary',
                  lineHeight: 1.65,
                  fontSize: '0.82rem',
                  wordBreak: 'break-word',
                }}
              >
                {overviewStats.na_context_preview}
                {overviewStats.na_context_preview.length >= 150 && (
                  <Typography
                    component="span"
                    variant="caption"
                    sx={{ color: 'text.disabled', ml: 0.5, cursor: 'pointer' }}
                    onClick={onNavigateToPrompt}
                  >
                    …
                  </Typography>
                )}
              </Typography>
              {overviewStats.na_context_updated_at && (
                <Typography variant="caption" color="text.disabled" sx={{ display: 'block', mt: 0.75 }}>
                  <InfoOutlineIcon sx={{ fontSize: 11, mr: 0.4, verticalAlign: 'middle' }} />
                  {t('detail.overview.contextUpdated', { time: overviewStats.na_context_updated_at })}
                </Typography>
              )}
            </Box>
          ) : (
            <Typography variant="body2" color="text.disabled" sx={{ fontStyle: 'italic' }}>
              {t('detail.overview.noContext')}
            </Typography>
          )}
        </CardContent>
      </Card>
    </Stack>
  )
}


// ─────────────────────────────────────────────────────────────
// ImagePullDialog: SSE 流式镜像拉取对话框
// ─────────────────────────────────────────────────────────────

interface GlobalLine {
  text: string
}

const _DONE_STATUS = new Set(['Pull complete', 'Already exists', 'Download complete'])

function ImagePullDialog({
  open,
  onClose,
  workspaceId,
  image,
}: {
  open: boolean
  onClose: () => void
  workspaceId: number
  image: string
}) {
  const { t } = useTranslation('workspace')
  const theme = useTheme()

  const getLayerColor = (status: string): string => {
    if (_DONE_STATUS.has(status)) return theme.palette.success.main
    if (status.startsWith('Extracting')) return theme.palette.warning.main
    if (status.startsWith('Downloading')) return theme.palette.primary.main
    if (status.startsWith('Pulling')) return theme.palette.text.disabled as string
    return theme.palette.text.secondary as string
  }

  const [layers, setLayers] = useState<Map<string, string>>(new Map())
  const [globalLines, setGlobalLines] = useState<GlobalLine[]>([])
  const [pullStatus, setPullStatus] = useState<'idle' | 'pulling' | 'done' | 'error'>('idle')
  const [errorMsg, setErrorMsg] = useState('')
  const scrollRef = useRef<HTMLDivElement>(null)
  const cancelRef = useRef<(() => void) | null>(null)

  const startPull = () => {
    setLayers(new Map())
    setGlobalLines([])
    setErrorMsg('')
    setPullStatus('pulling')

    const cancel = workspaceApi.streamPullSandboxImage(
      workspaceId,
      (msg: ImagePullMessage) => {
        if (msg.type === 'progress') {
          if (msg.layer) {
            setLayers(prev => new Map(prev).set(msg.layer, msg.status))
          } else if (msg.status) {
            setGlobalLines(prev => [...prev, { text: msg.status }])
          }
        } else if (msg.type === 'done') {
          setPullStatus('done')
        } else if (msg.type === 'error') {
          setErrorMsg(msg.data)
          setPullStatus('error')
        }
      },
      () => {
        setPullStatus('error')
        setErrorMsg(t('detail.errors.image.pullDialog.failed'))
      },
    )
    cancelRef.current = cancel
  }

  useEffect(() => {
    if (!open) return
    startPull()
    return () => {
      cancelRef.current?.()
      cancelRef.current = null
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open, workspaceId])

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight
    }
  }, [layers, globalLines])

  const handleClose = () => {
    cancelRef.current?.()
    cancelRef.current = null
    onClose()
  }

  const handleRetry = () => {
    cancelRef.current?.()
    startPull()
  }

  const layerEntries = Array.from(layers.entries())
  const doneCount = layerEntries.filter(([, s]) => _DONE_STATUS.has(s)).length
  const totalCount = layerEntries.length

  return (
    <Dialog open={open} onClose={pullStatus === 'pulling' ? undefined : handleClose} maxWidth="md" fullWidth>
      <DialogTitle sx={{ display: 'flex', alignItems: 'center', gap: 1, pb: 1 }}>
        <CloudDownloadIcon fontSize="small" />
        {t('detail.errors.image.pullDialog.title')}
      </DialogTitle>
      <DialogContent sx={{ pt: 0 }}>
        <Typography variant="body2" color="text.secondary" sx={{ mb: 1.5, fontFamily: 'monospace', fontSize: '0.8rem' }}>
          {image}
        </Typography>

        <Box
          ref={scrollRef}
          sx={{
            bgcolor: 'action.hover',
            border: '1px solid',
            borderColor: 'divider',
            borderRadius: 1,
            p: 1.5,
            height: 'min(480px, 60vh)',
            overflowY: 'auto',
            fontFamily: 'monospace',
            fontSize: '0.75rem',
            lineHeight: 1.6,
          }}
        >
          {layers.size === 0 && globalLines.length === 0 && pullStatus === 'pulling' ? (
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, color: 'text.disabled' }}>
              <CircularProgress size={12} color="primary" />
              <span>{t('detail.errors.image.pullDialog.pulling')}</span>
            </Box>
          ) : (
            <>
              {layerEntries.map(([id, layerStatus]) => (
                <Box key={id} sx={{ display: 'flex', gap: 1.5, mb: 0.25 }}>
                  <Box component="span" sx={{ color: 'text.disabled', minWidth: 80, flexShrink: 0 }}>
                    {id.slice(0, 12)}
                  </Box>
                  <Box component="span" sx={{ color: getLayerColor(layerStatus) }}>
                    {layerStatus}
                  </Box>
                </Box>
              ))}
              {globalLines.map((line, i) => (
                <Box key={i} sx={{ color: 'text.secondary', mt: 0.5 }}>
                  {line.text}
                </Box>
              ))}
            </>
          )}
        </Box>

        {totalCount > 0 && pullStatus === 'pulling' && (
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mt: 1 }}>
            <CircularProgress
              variant="determinate"
              value={totalCount > 0 ? (doneCount / totalCount) * 100 : 0}
              size={16}
              color="success"
            />
            <Typography variant="caption" color="text.secondary">
              {doneCount} / {totalCount} layers
            </Typography>
          </Box>
        )}

        {pullStatus === 'done' && (
          <Typography variant="body2" color="success.main" sx={{ mt: 1, display: 'flex', alignItems: 'center', gap: 0.5 }}>
            ✓ {t('detail.errors.image.pullDialog.success')}
          </Typography>
        )}
        {pullStatus === 'error' && (
          <Typography variant="body2" color="error.main" sx={{ mt: 1 }}>
            ✗ {errorMsg || t('detail.errors.image.pullDialog.failed')}
          </Typography>
        )}
      </DialogContent>
      <DialogActions>
        {pullStatus === 'error' && (
          <ActionButton tone="secondary" onClick={handleRetry} size="small">
            {t('detail.errors.image.pullDialog.retry')}
          </ActionButton>
        )}
        <ActionButton tone="secondary" onClick={handleClose} disabled={pullStatus === 'pulling'} size="small">
          {t('detail.errors.image.pullDialog.close')}
        </ActionButton>
      </DialogActions>
    </Dialog>
  )
}
