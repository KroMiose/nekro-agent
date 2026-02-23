import React, { useState } from 'react'
import {
  Box,
  Button,
  Card,
  CardContent,
  Typography,
  Chip,
  TextField,
  CircularProgress,
  Stack,
  Divider,
  IconButton,
  Tooltip,
  Autocomplete,
  Skeleton,
  alpha,
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
} from '@mui/icons-material'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import {
  workspaceApi,
  WorkspaceDetail,
  SandboxStatus,
  commApi,
} from '../../../services/api/workspace'
import { ccModelPresetApi } from '../../../services/api/cc-model-preset'
import { chatChannelApi } from '../../../services/api/chat-channel'
import { useNotification } from '../../../hooks/useNotification'
import { CARD_VARIANTS, CHIP_VARIANTS } from '../../../theme/variants'
import { useTheme } from '@mui/material/styles'
import { useTranslation } from 'react-i18next'

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
    <Box sx={{ display: 'flex', gap: 1, alignItems: 'flex-start' }}>
      <Typography
        variant="body2"
        color="text.secondary"
        sx={{ minWidth: 84, flexShrink: 0, pt: '1px' }}
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
          }}
        >
          {value ?? '—'}
        </Typography>
      )}
    </Box>
  )
}

function OverviewStatCard({
  icon,
  label,
  value,
  color,
  loading,
  onClick,
  suffix,
}: {
  icon: React.ReactNode
  label: string
  value?: string | number
  color: string
  loading?: boolean
  onClick?: () => void
  suffix?: string
}) {
  return (
    <Card
      sx={{
        ...CARD_VARIANTS.default.styles,
        flex: 1,
        cursor: onClick ? 'pointer' : undefined,
        transition: 'all 0.18s',
        '&:hover': onClick
          ? { transform: 'translateY(-1px)', boxShadow: `0 4px 16px ${alpha(color, 0.18)}` }
          : undefined,
      }}
      onClick={onClick}
    >
      <CardContent sx={{ p: 2, '&:last-child': { pb: 2 } }}>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5 }}>
          <Box
            sx={{
              color,
              bgcolor: alpha(color, 0.12),
              borderRadius: 2,
              p: 1,
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
              <Skeleton variant="text" width={32} height={28} />
            ) : (
              <Typography variant="h6" fontWeight={700} lineHeight={1.2}>
                {value ?? '—'}
                {suffix && (
                  <Typography
                    component="span"
                    variant="caption"
                    color="text.secondary"
                    sx={{ ml: 0.4, fontWeight: 400 }}
                  >
                    {suffix}
                  </Typography>
                )}
              </Typography>
            )}
            <Typography variant="caption" color="text.secondary" sx={{ display: 'block' }}>
              {label}
            </Typography>
          </Box>
          {onClick && (
            <ArrowForwardIcon
              sx={{ fontSize: 16, color: 'text.disabled', ml: 'auto', flexShrink: 0 }}
            />
          )}
        </Box>
      </CardContent>
    </Card>
  )
}

export default function OverviewTab({
  workspace,
  sandboxStatus,
  onNavigateToSandbox,
  onNavigateToConfig,
  onNavigateToExtensions,
  onNavigateToComm,
}: {
  workspace: WorkspaceDetail
  sandboxStatus: SandboxStatus | null
  onNavigateToSandbox: () => void
  onNavigateToConfig: () => void
  onNavigateToExtensions: () => void
  onNavigateToComm?: () => void
}) {
  const theme = useTheme()
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const notification = useNotification()
  const { t } = useTranslation('workspace')

  const selectedSkills: string[] = (workspace.metadata.skills as string[] | undefined) ?? []
  const mcpConfig =
    (workspace.metadata.mcp_config as { mcpServers?: Record<string, unknown> } | undefined) ?? {}
  const mcpServersCount = Object.keys(mcpConfig.mcpServers ?? {}).length

  // 沙盒通讯记录总数
  const { data: commStats } = useQuery({
    queryKey: ['workspace-comm-count', workspace.id],
    queryFn: () => commApi.getHistory(workspace.id, 1),
    staleTime: 30000,
  })
  const commCount = commStats?.total ?? 0

  // ── CC 模型预设 ──
  const { data: allPresets = [] } = useQuery({
    queryKey: ['cc-model-presets'],
    queryFn: () => ccModelPresetApi.getList(),
  })
  const currentPreset = workspace.cc_model_preset_id != null
    ? allPresets.find(p => p.id === workspace.cc_model_preset_id)
    : allPresets.find(p => p.is_default)

  // ── 频道绑定 ──
  const { data: channelList } = useQuery({
    queryKey: ['chat-channels-all'],
    queryFn: () => chatChannelApi.getList({ page: 1, page_size: 100 }),
  })
  const allChannels = channelList?.items ?? []

  const { data: boundChannels = [], isLoading: channelsLoading } = useQuery({
    queryKey: ['workspace-channels', workspace.id],
    queryFn: () => workspaceApi.getBoundChannels(workspace.id),
  })

  const [selectedChannel, setSelectedChannel] = useState<{
    chat_key: string
    channel_name: string | null
  } | null>(null)

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

  const autocompleteOptions = allChannels.map(ch => ({
    chat_key: ch.chat_key,
    channel_name: ch.channel_name,
  }))

  const alreadyBound = selectedChannel
    ? boundChannels.some(b => b.chat_key === selectedChannel.chat_key)
    : false

  const containerName = sandboxStatus?.container_name ?? workspace.container_name
  const hostPort = sandboxStatus?.host_port ?? workspace.host_port

  return (
    <Stack spacing={2}>
      {/* ── 统计快览 ── */}
      <Box sx={{ display: 'flex', gap: 2, flexWrap: 'wrap' }}>
        <OverviewStatCard
          icon={<HubIcon sx={{ fontSize: 20 }} />}
          label={t('detail.overview.statCards.channels')}
          value={channelsLoading ? undefined : boundChannels.length}
          suffix={t('detail.overview.suffixes.count')}
          color={theme.palette.primary.main}
          loading={channelsLoading}
        />
        <OverviewStatCard
          icon={<ExtensionIcon sx={{ fontSize: 20 }} />}
          label={t('detail.overview.statCards.skills')}
          value={selectedSkills.length}
          suffix={t('detail.overview.suffixes.count')}
          color={theme.palette.success.main}
          onClick={onNavigateToExtensions}
        />
        <OverviewStatCard
          icon={<McpIcon sx={{ fontSize: 20 }} />}
          label={t('detail.overview.statCards.mcp')}
          value={mcpServersCount}
          suffix={t('detail.overview.suffixes.count')}
          color={theme.palette.info?.main ?? theme.palette.primary.light}
          onClick={onNavigateToExtensions}
        />
        <OverviewStatCard
          icon={<ForumIcon sx={{ fontSize: 20 }} />}
          label={t('detail.overview.statCards.comm')}
          value={commCount}
          suffix={t('detail.overview.suffixes.messages')}
          color={theme.palette.secondary.main}
          onClick={onNavigateToComm}
        />
      </Box>

      {/* ── 主信息区（两列） ── */}
      <Box sx={{ display: 'flex', gap: 2, alignItems: 'flex-start' }}>
        {/* 左：工作区基本信息 */}
        <Card sx={{ ...CARD_VARIANTS.default.styles, flex: 1 }}>
          <CardContent>
            <Box sx={{ mb: 1.5 }}>
              <Typography variant="subtitle1" fontWeight={700} lineHeight={1.25}>
                {workspace.name}
              </Typography>
              {workspace.description ? (
                <Typography
                  variant="body2"
                  color="text.secondary"
                  sx={{ mt: 0.5, lineHeight: 1.55 }}
                >
                  {workspace.description}
                </Typography>
              ) : (
                <Typography
                  variant="body2"
                  color="text.disabled"
                  sx={{ mt: 0.5, fontStyle: 'italic' }}
                >
                  {t('detail.overview.noDescription')}
                </Typography>
              )}
            </Box>
            <Divider sx={{ mb: 1.5 }} />
            <Stack spacing={0.85}>
              <InfoRow label={t('detail.overview.infoRows.id')} value={String(workspace.id)} mono />
              <InfoRow label={t('detail.overview.infoRows.policy')}>
                <Chip
                  label={workspace.runtime_policy === 'agent'
                    ? t('policy.agent')
                    : workspace.runtime_policy === 'relaxed'
                      ? t('policy.relaxed')
                      : workspace.runtime_policy === 'strict'
                        ? t('policy.strict')
                        : workspace.runtime_policy}
                  size="small"
                  sx={CHIP_VARIANTS.base(true)}
                />
              </InfoRow>
              <InfoRow
                label={t('detail.overview.infoRows.image')}
                value={`${workspace.sandbox_image || t('detail.overview.defaultImage')}:${workspace.sandbox_version || 'latest'}`}
                mono
              />
              <InfoRow label={t('detail.overview.infoRows.createdAt')} value={new Date(workspace.create_time).toLocaleString()} />
              <InfoRow label={t('detail.overview.infoRows.updatedAt')} value={new Date(workspace.update_time).toLocaleString()} />
            </Stack>
          </CardContent>
        </Card>

        {/* 右：沙盒运行状态 */}
        <Card sx={{ ...CARD_VARIANTS.default.styles, flex: 1 }}>
          <CardContent>
            <Box sx={{ display: 'flex', alignItems: 'center', mb: 1.5, gap: 1 }}>
              <Typography variant="subtitle2" fontWeight={600} sx={{ flexGrow: 1 }}>
                {t('detail.overview.sections.sandboxStatus')}
              </Typography>
              <Button
                size="small"
                variant="outlined"
                endIcon={<ArrowForwardIcon sx={{ fontSize: 14 }} />}
                onClick={onNavigateToSandbox}
                sx={{ minWidth: 0, px: 1.2, fontSize: '0.75rem' }}
              >
                {t('detail.overview.manage')}
              </Button>
            </Box>
            <Divider sx={{ mb: 1.5 }} />
            <Stack spacing={0.85}>
              <InfoRow label={t('detail.overview.infoRows.containerName')} value={containerName ?? '—'} mono />
              <InfoRow label={t('detail.overview.infoRows.hostPort')} value={hostPort ? String(hostPort) : '—'} mono />
              <InfoRow label={t('detail.overview.infoRows.sessionId')} value={sandboxStatus?.session_id ?? '—'} mono />
              <InfoRow label={t('detail.overview.infoRows.modelGroup')}>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5, minWidth: 0 }}>
                  <Typography
                    variant="body2"
                    sx={{
                      overflow: 'hidden',
                      textOverflow: 'ellipsis',
                      whiteSpace: 'nowrap',
                      fontSize: '0.82rem',
                    }}
                  >
                    {currentPreset ? currentPreset.name : allPresets.length === 0 ? t('detail.overview.loading') : t('detail.overview.notConfigured')}
                  </Typography>
                  {currentPreset?.is_default && (
                    <Typography variant="caption" color="primary" sx={{ flexShrink: 0 }}>
                      {t('detail.overview.defaultTag')}
                    </Typography>
                  )}
                  <Tooltip title={t('detail.overview.tooltips.switchConfig')}>
                    <IconButton size="small" onClick={onNavigateToConfig} sx={{ ml: 0.25 }}>
                      <TuneIcon sx={{ fontSize: 14 }} />
                    </IconButton>
                  </Tooltip>
                  <Tooltip title={t('detail.overview.tooltips.managePresets')}>
                    <IconButton size="small" onClick={() => navigate('/workspace/cc-models')}>
                      <OpenInNewIcon sx={{ fontSize: 14 }} />
                    </IconButton>
                  </Tooltip>
                </Box>
              </InfoRow>
              {workspace.last_heartbeat && (
                <InfoRow label={t('detail.overview.infoRows.lastHeartbeat')}>
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                    <HeartbeatIcon sx={{ fontSize: 14, color: 'text.disabled' }} />
                    <Typography variant="body2" sx={{ fontSize: '0.82rem' }}>
                      {new Date(workspace.last_heartbeat).toLocaleString()}
                    </Typography>
                  </Box>
                </InfoRow>
              )}
            </Stack>
            {workspace.last_error && (
              <Box
                component="div"
                sx={{
                  mt: 1.5,
                  py: 0.5,
                  px: 1.5,
                  borderRadius: 1,
                  border: '1px solid',
                  borderColor: 'error.main',
                  bgcolor: (theme) => alpha(theme.palette.error.main, 0.08),
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
        <CardContent>
          <Typography
            variant="subtitle2"
            sx={{
              fontWeight: 600,
              mb: 1.5,
              color: 'text.secondary',
              textTransform: 'uppercase',
              fontSize: '0.7rem',
              letterSpacing: 1,
            }}
          >
            {t('detail.overview.channels.title')}
          </Typography>

          <Box sx={{ display: 'flex', gap: 1, mb: 1.5 }}>
            <Autocomplete
              fullWidth
              options={autocompleteOptions}
              value={selectedChannel}
              onChange={(_, val) => setSelectedChannel(val)}
              getOptionLabel={opt =>
                opt.channel_name ? `${opt.channel_name} (${opt.chat_key})` : opt.chat_key
              }
              isOptionEqualToValue={(opt, val) => opt.chat_key === val.chat_key}
              getOptionDisabled={opt => boundChannels.some(b => b.chat_key === opt.chat_key)}
              renderInput={params => (
                <TextField
                  {...params}
                  size="small"
                  placeholder={t('detail.overview.channels.searchPlaceholder')}
                  autoComplete="off"
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
            <Button
              variant="outlined"
              size="small"
              disabled={!selectedChannel || alreadyBound || bindMutation.isPending}
              onClick={() => selectedChannel && bindMutation.mutate(selectedChannel.chat_key)}
              sx={{ minWidth: 64, flexShrink: 0 }}
            >
              {bindMutation.isPending ? (
                <CircularProgress size={14} />
              ) : alreadyBound ? (
                t('detail.overview.channels.bound')
              ) : (
                t('detail.overview.channels.bind')
              )}
            </Button>
          </Box>

          <Divider sx={{ mb: 1.5 }} />

          {channelsLoading ? (
            <Box sx={{ display: 'flex', justifyContent: 'center', py: 2 }}>
              <CircularProgress size={20} />
            </Box>
          ) : boundChannels.length === 0 ? (
            <Typography variant="body2" color="text.secondary" sx={{ py: 1 }}>
              {t('detail.overview.channels.noChannels')}
            </Typography>
          ) : (
            <Stack spacing={0.5}>
              {boundChannels.map(ch => {
                const info = allChannels.find(c => c.chat_key === ch.chat_key)
                return (
                  <Box
                    key={ch.chat_key}
                    sx={{
                      display: 'flex',
                      alignItems: 'center',
                      px: 1.5,
                      py: 0.75,
                      borderRadius: 1,
                      border: '1px solid',
                      borderColor: 'divider',
                      gap: 1,
                    }}
                  >
                    <Box sx={{ flexGrow: 1, minWidth: 0 }}>
                      <Tooltip title={ch.chat_key} placement="top" arrow>
                        <Typography
                          variant="body2"
                          sx={{
                            fontWeight: 500,
                            lineHeight: 1.3,
                            display: 'inline',
                            textDecoration: 'underline',
                            textDecorationStyle: 'dotted',
                            cursor: 'help',
                          }}
                        >
                          {info?.channel_name ?? ch.chat_key}
                        </Typography>
                      </Tooltip>
                    </Box>
                    {info?.chat_type && (
                      <Box sx={{ flexShrink: 0 }}>
                        <Chip
                          label={info.chat_type}
                          size="small"
                          sx={CHIP_VARIANTS.base(true)}
                        />
                      </Box>
                    )}
                    {info?.is_active === false && (
                      <Box sx={{ flexShrink: 0 }}>
                        <Chip
                          label={t('detail.overview.channels.disabled')}
                          size="small"
                          color="warning"
                          sx={CHIP_VARIANTS.base(true)}
                        />
                      </Box>
                    )}
                    <Tooltip title={t('detail.overview.channels.unbindTooltip')}>
                      <IconButton
                        size="small"
                        color="error"
                        disabled={unbindMutation.isPending}
                        onClick={() => unbindMutation.mutate(ch.chat_key)}
                      >
                        <LinkOffIcon fontSize="small" />
                      </IconButton>
                    </Tooltip>
                  </Box>
                )
              })}
            </Stack>
          )}
        </CardContent>
      </Card>
    </Stack>
  )
}
