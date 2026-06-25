import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import {
  Alert,
  Box,
  Checkbox,
  Chip,
  CircularProgress,
  Divider,
  FormControlLabel,
  LinearProgress,
  Paper,
  Stack,
  Switch,
  TextField,
  Tooltip,
  Typography,
  alpha,
  useTheme,
} from '@mui/material'
import {
  CancelOutlined as CancelIcon,
  BackupOutlined as BackupIcon,
  CheckCircleOutline as SuccessIcon,
  CloudDoneOutlined as ConnectedIcon,
  CloudOffOutlined as DisconnectedIcon,
  ContentCopyOutlined as CopyIcon,
  ErrorOutline as ErrorIcon,
  PauseOutlined as PauseIcon,
  PlayArrowOutlined as PlayIcon,
  RefreshOutlined as RefreshIcon,
  RestartAltOutlined as RollbackIcon,
  RestoreOutlined as RestoreIcon,
  ScienceOutlined as PreviewIcon,
  SystemUpdateAltOutlined as UpdateIcon,
  WarningAmberOutlined as WarningIcon,
} from '@mui/icons-material'
import { useTranslation } from 'react-i18next'
import ActionButton from '../../../components/common/ActionButton'
import IconActionButton from '../../../components/common/IconActionButton'
import NekroDialog from '../../../components/common/NekroDialog'
import { useNotification } from '../../../hooks/useNotification'
import { CARD_VARIANTS, SCROLLBAR_VARIANTS } from '../../../theme/variants'
import { ApiError } from '../../../services/api/axios'
import {
  deploymentApi,
  type DeploymentAgentVersion,
  type DeploymentBackupSummary,
  type DeploymentCapabilities,
  type DeploymentInstance,
  type DeploymentJobType,
  type DeploymentJobStatus,
  type DeploymentUpdateRequest,
} from '../../../services/api/deployment'
import { useDeploymentJob } from './useDeploymentJob'

type UpdateChannel = DeploymentUpdateRequest['channel']

interface PendingAction {
  type: DeploymentJobType
  channel?: UpdateChannel
  backup?: boolean
  restorePrePreview?: boolean
  backupId?: string
  backupName?: string
  titleKey: string
  messageKey: string
  messageValues?: Record<string, string>
  confirmTone?: 'primary' | 'danger'
}

const STATUS_COLOR: Record<
  DeploymentJobStatus,
  'default' | 'info' | 'success' | 'error' | 'warning'
> = {
  queued: 'info',
  running: 'info',
  succeeded: 'success',
  failed: 'error',
  cancel_requested: 'warning',
  cancelled: 'default',
}

const createRequestId = (): string => crypto.randomUUID()

const formatBackupSize = (sizeBytes: number): string => {
  if (!Number.isFinite(sizeBytes) || sizeBytes < 0) return '-'
  if (sizeBytes < 1024) return `${sizeBytes} B`
  if (sizeBytes < 1024 * 1024) return `${(sizeBytes / 1024).toFixed(1)} KB`
  if (sizeBytes < 1024 * 1024 * 1024) return `${(sizeBytes / 1024 / 1024).toFixed(1)} MB`
  return `${(sizeBytes / 1024 / 1024 / 1024).toFixed(1)} GB`
}

const getBackupDisplayName = (backup: DeploymentBackupSummary, unnamedLabel: string): string => {
  const name = backup.name?.trim()
  if (name) return name

  if (/^.+_backup_\d{8}_\d{6}\.tar\.gz$/.test(backup.filename)) {
    return unnamedLabel
  }

  const namedMatch = backup.filename.match(/^.+_backup_(.+)_\d{8}_\d{6}\.tar\.gz$/)
  if (namedMatch?.[1]) return namedMatch[1]

  return backup.filename
}

const StatusField = ({ label, value }: { label: string; value: React.ReactNode }) => (
  <Box sx={{ minWidth: 0 }}>
    <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mb: 0.5 }}>
      {label}
    </Typography>
    <Box sx={{ minHeight: 28, display: 'flex', alignItems: 'center', minWidth: 0 }}>{value}</Box>
  </Box>
)

export default function DeploymentPage() {
  const { t } = useTranslation('deployment')
  const theme = useTheme()
  const notification = useNotification()
  const [capabilities, setCapabilities] = useState<DeploymentCapabilities | null>(null)
  const [instance, setInstance] = useState<DeploymentInstance | null>(null)
  const [agentVersion, setAgentVersion] = useState<DeploymentAgentVersion | null>(null)
  const [overviewLoading, setOverviewLoading] = useState(false)
  const [overviewError, setOverviewError] = useState<string | null>(null)
  const [backup, setBackup] = useState(true)
  const [updateSandbox, setUpdateSandbox] = useState(true)
  const [updateCcSandbox, setUpdateCcSandbox] = useState(false)
  const [backupName, setBackupName] = useState('')
  const [backups, setBackups] = useState<DeploymentBackupSummary[]>([])
  const [backupsLoading, setBackupsLoading] = useState(false)
  const [backupsError, setBackupsError] = useState<string | null>(null)
  const [pendingAction, setPendingAction] = useState<PendingAction | null>(null)
  const [submitting, setSubmitting] = useState(false)
  const [autoScroll, setAutoScroll] = useState(true)
  const logContainerRef = useRef<HTMLDivElement | null>(null)
  const refreshedJobRef = useRef<string | null>(null)

  const {
    activeTask,
    job,
    logs,
    connectionState,
    trackingError,
    isCancelling,
    startTracking,
    cancelActiveJob,
    dismissCompletedJob,
  } = useDeploymentJob(true, capabilities?.supports.log_stream === true)

  const resolveErrorMessage = useCallback(
    (error: unknown) => {
      if (error instanceof ApiError) {
        return t(`errors.${error.type}`, { defaultValue: error.message })
      }
      return t('errors.unknown')
    },
    [t]
  )

  const loadOverview = useCallback(async () => {
    setOverviewLoading(true)
    setOverviewError(null)
    try {
      const nextCapabilities = await deploymentApi.getCapabilities()
      setCapabilities(nextCapabilities)
      const nextAgentVersion = await deploymentApi.getAgentVersion()
      setAgentVersion(nextAgentVersion)
      if (nextCapabilities.enabled) {
        const nextInstance = await deploymentApi.getInstance()
        setInstance(nextInstance)
      } else {
        setInstance(null)
      }
    } catch (error) {
      setOverviewError(resolveErrorMessage(error))
    } finally {
      setOverviewLoading(false)
    }
  }, [resolveErrorMessage])

  const loadBackups = useCallback(async () => {
    setBackupsLoading(true)
    setBackupsError(null)
    try {
      const response = await deploymentApi.listBackups()
      setBackups(response.backups)
    } catch (error) {
      setBackupsError(resolveErrorMessage(error))
    } finally {
      setBackupsLoading(false)
    }
  }, [resolveErrorMessage])

  useEffect(() => {
    void loadOverview()
  }, [loadOverview])

  useEffect(() => {
    if (capabilities?.enabled === true && capabilities.supports.backup === true) {
      void loadBackups()
    }
  }, [capabilities?.enabled, capabilities?.supports.backup, loadBackups])

  useEffect(() => {
    if (capabilities && capabilities.supports.backup === false) {
      setBackup(false)
    }
  }, [capabilities])

  useEffect(() => {
    if (!autoScroll || !logContainerRef.current) return
    logContainerRef.current.scrollTop = logContainerRef.current.scrollHeight
  }, [autoScroll, logs])

  useEffect(() => {
    if (!job || job.status !== 'succeeded' || refreshedJobRef.current === job.job_id) return
    refreshedJobRef.current = job.job_id
    void loadOverview()
    if (job.type === 'backup' || job.type === 'restore') {
      void loadBackups()
    }
  }, [job, loadBackups, loadOverview])

  const isTaskActive = activeTask !== null
  const canUpdate = capabilities?.enabled === true && capabilities.supports.update === true
  const showStableUpdate = agentVersion?.update_available === true
  const supportsPreview = capabilities?.enabled === true && capabilities.supports.preview === true
  const showPreviewUpdate = capabilities?.enabled !== true || supportsPreview
  const supportsRollback = capabilities?.enabled === true && capabilities.supports.rollback === true
  const isPreviewChannel = instance?.channel === 'preview'
  const isPreviewVersion = isPreviewChannel || agentVersion?.current_version === 'preview'
  const supportsRestore = capabilities?.supports.restore_pre_preview === true
  const supportsManualBackup = capabilities?.enabled === true && capabilities.supports.backup === true
  const supportsManualRestore = capabilities?.enabled === true && capabilities.supports.restore === true
  const supportsCancel = capabilities?.supports.cancel === true

  const submitDeploymentAction = useCallback(
    async (action: PendingAction) => {
      if (submitting || isTaskActive) return
      setSubmitting(true)
      const clientRequestId = createRequestId()
      try {
        const response =
          action.type === 'backup'
            ? await deploymentApi.createBackup({
                name: action.backupName || undefined,
                client_request_id: clientRequestId,
              })
            : action.type === 'restore'
              ? await deploymentApi.createRestore({
                  backup_id: action.backupId ?? '',
                  client_request_id: clientRequestId,
                })
              : await deploymentApi.createUpdate({
                  channel: action.channel ?? 'stable',
                  backup: action.backup ?? true,
                  update_sandbox: updateSandbox,
                  update_cc_sandbox: updateCcSandbox,
                  restore_pre_preview: action.restorePrePreview ?? false,
                  client_request_id: clientRequestId,
                })
        startTracking(response, clientRequestId)
        notification.success(t(`notifications.${action.type}JobCreated`))
      } catch (error) {
        notification.error(resolveErrorMessage(error), { autoHideDuration: 7000 })
      } finally {
        setSubmitting(false)
        setPendingAction(null)
      }
    },
    [
      isTaskActive,
      notification,
      resolveErrorMessage,
      startTracking,
      submitting,
      t,
      updateCcSandbox,
      updateSandbox,
    ]
  )

  const handleStableUpdate = () => {
    const action: PendingAction = {
      type: 'update',
      channel: 'stable',
      backup,
      restorePrePreview: false,
      titleKey: 'confirm.noBackupTitle',
      messageKey: 'confirm.noBackupMessage',
      confirmTone: 'danger',
    }
    if (backup) {
      void submitDeploymentAction(action)
    } else {
      setPendingAction(action)
    }
  }

  const handleCreateBackup = () => {
    setPendingAction({
      type: 'backup',
      backupName: backupName.trim(),
      titleKey: 'confirm.manualBackupTitle',
      messageKey: 'confirm.manualBackupMessage',
    })
  }

  const handleRestoreBackup = (selectedBackup: DeploymentBackupSummary) => {
    setPendingAction({
      type: 'restore',
      backupId: selectedBackup.backup_id,
      titleKey: 'confirm.manualRestoreTitle',
      messageKey: 'confirm.manualRestoreMessage',
      messageValues: { filename: selectedBackup.filename },
      confirmTone: 'danger',
    })
  }

  const handleCopyLogs = async () => {
    if (logs.length === 0) return
    const text = logs
      .map(entry => `${entry.ts ?? ''} [${entry.level}] ${entry.line}`.trim())
      .join('\n')
    try {
      await navigator.clipboard.writeText(text)
      notification.success(t('notifications.logsCopied'))
    } catch {
      notification.error(t('errors.copyFailed'))
    }
  }

  const handleCancel = async () => {
    try {
      await cancelActiveJob()
      notification.info(t('notifications.cancelRequested'))
    } catch (error) {
      notification.error(resolveErrorMessage(error))
    }
  }

  const progressValue = useMemo(() => {
    if (!job?.progress || !job.progress.total || job.progress.current === null) return undefined
    return Math.min(100, Math.max(0, (job.progress.current / job.progress.total) * 100))
  }, [job?.progress])

  const connectionLabel = t(`connection.${connectionState}`)
  const connectionColor =
    connectionState === 'live' ? 'success' : connectionState === 'idle' ? 'default' : 'warning'

  return (
    <Box
      sx={{
        height: '100%',
        overflow: 'auto',
        p: { xs: 1.5, md: 2 },
        ...SCROLLBAR_VARIANTS.thin.styles,
      }}
    >
      <Stack spacing={2} sx={{ maxWidth: 1280, mx: 'auto' }}>
        <Paper sx={{ ...CARD_VARIANTS.elevated.styles, p: { xs: 2, md: 2.5 } }}>
          <Stack
            direction={{ xs: 'column', sm: 'row' }}
            alignItems={{ xs: 'stretch', sm: 'center' }}
            justifyContent="space-between"
            gap={1.5}
            mb={2}
          >
            <Box>
              <Typography variant="h6">{t('status.title')}</Typography>
              <Typography variant="body2" color="text.secondary">
                {t('status.subtitle')}
              </Typography>
            </Box>
            <ActionButton
              tone="secondary"
              size="small"
              startIcon={overviewLoading ? <CircularProgress size={16} /> : <RefreshIcon />}
              onClick={() => void loadOverview()}
              disabled={overviewLoading}
              sx={{ flexShrink: 0 }}
            >
              {t('actions.refresh')}
            </ActionButton>
          </Stack>

          {overviewError && (
            <Alert severity="error" sx={{ mb: 2 }}>
              {overviewError}
            </Alert>
          )}
          {capabilities?.unavailable_reason && (
            <Alert severity="warning" icon={<WarningIcon />} sx={{ mb: 2 }}>
              <Typography variant="body2" fontWeight={600}>
                {t(`errors.${capabilities.unavailable_reason.code}`, {
                  defaultValue: capabilities.unavailable_reason.message,
                })}
              </Typography>
              <Typography variant="caption" color="text.secondary">
                {t('status.unavailableHint')}
              </Typography>
            </Alert>
          )}

          <Box
            sx={{
              display: 'grid',
              gridTemplateColumns: { xs: '1fr 1fr', md: 'repeat(4, minmax(0, 1fr))' },
              gap: { xs: 2, md: 2.5 },
            }}
          >
            <StatusField
              label={t('status.daemon')}
              value={
                <Chip
                  size="small"
                  icon={capabilities?.enabled ? <ConnectedIcon /> : <DisconnectedIcon />}
                  color={capabilities?.enabled ? 'success' : 'default'}
                  label={capabilities?.enabled ? t('common.available') : t('common.unavailable')}
                />
              }
            />
            <StatusField
              label={t('status.provider')}
              value={
                <Typography noWrap>{capabilities?.provider ?? t('common.unknown')}</Typography>
              }
            />
            <StatusField
              label={t('status.platform')}
              value={
                <Typography noWrap>{capabilities?.platform ?? t('common.unknown')}</Typography>
              }
            />
            <StatusField
              label={t('status.protocol')}
              value={
                <Typography noWrap>
                  {capabilities?.protocol_version ?? t('common.unknown')}
                </Typography>
              }
            />
            <StatusField
              label={t('status.channel')}
              value={<Chip size="small" label={instance?.channel ?? t('common.unknown')} />}
            />
            <StatusField
              label={t('status.image')}
              value={
                <Typography noWrap title={instance?.image ?? undefined}>
                  {instance?.image ?? t('common.unknown')}
                </Typography>
              }
            />
            <StatusField
              label={t('status.container')}
              value={<Typography>{instance?.container_status ?? t('common.unknown')}</Typography>}
            />
            <StatusField
              label={t('status.health')}
              value={<Typography>{instance?.app_health ?? t('common.unknown')}</Typography>}
            />
            <StatusField
              label={t('status.docker')}
              value={
                <Chip
                  size="small"
                  color={instance?.docker_ok ? 'success' : 'default'}
                  label={instance?.docker_ok ? t('common.ready') : t('common.unavailable')}
                />
              }
            />
            <StatusField
              label={t('status.compose')}
              value={
                <Chip
                  size="small"
                  color={instance?.compose_ok ? 'success' : 'default'}
                  label={instance?.compose_ok ? t('common.ready') : t('common.unavailable')}
                />
              }
            />
            <StatusField
              label={t('status.agentVersion')}
              value={
                <Typography noWrap>
                  {agentVersion?.current_version ?? t('common.unknown')}
                </Typography>
              }
            />
            <StatusField
              label={t('status.latestVersion')}
              value={
                agentVersion?.checked ? (
                  <Chip
                    size="small"
                    color={agentVersion.update_available ? 'warning' : 'success'}
                    label={
                      agentVersion.update_available
                        ? t('status.updateAvailable', { version: agentVersion.latest_version })
                        : t('status.alreadyLatest')
                    }
                  />
                ) : (
                  <Tooltip title={agentVersion?.error_message ?? ''}>
                    <Chip
                      size="small"
                      color={agentVersion?.error_code ? 'warning' : 'default'}
                      label={agentVersion?.error_code ? t('status.versionCheckFailed') : t('common.unknown')}
                    />
                  </Tooltip>
                )
              }
            />
          </Box>
        </Paper>

        <Paper sx={{ ...CARD_VARIANTS.elevated.styles, p: { xs: 2, md: 2.5 } }}>
          <Typography variant="h6">{t('operations.title')}</Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
            {t('operations.subtitle')}
          </Typography>

          <Stack direction={{ xs: 'column', md: 'row' }} gap={{ xs: 0, md: 2 }} mb={2}>
            <FormControlLabel
              control={
                <Checkbox checked={backup} onChange={event => setBackup(event.target.checked)} />
              }
              label={t('options.backup')}
              disabled={capabilities?.supports.backup === false || isTaskActive || submitting}
            />
            <FormControlLabel
              control={
                <Checkbox
                  checked={updateSandbox}
                  onChange={event => setUpdateSandbox(event.target.checked)}
                />
              }
              label={t('options.updateSandbox')}
              disabled={isTaskActive || submitting}
            />
            <FormControlLabel
              control={
                <Checkbox
                  checked={updateCcSandbox}
                  onChange={event => setUpdateCcSandbox(event.target.checked)}
                />
              }
              label={t('options.updateCcSandbox')}
              disabled={isTaskActive || submitting}
            />
          </Stack>

          <Stack direction={{ xs: 'column', sm: 'row' }} gap={1} flexWrap="wrap" useFlexGap>
            {showStableUpdate && (
              <ActionButton
                tone="primary"
                startIcon={
                  submitting ? <CircularProgress size={16} color="inherit" /> : <UpdateIcon />
                }
                onClick={handleStableUpdate}
                disabled={!canUpdate || isTaskActive || submitting}
              >
                {t('actions.updateStable')}
              </ActionButton>
            )}
            {showPreviewUpdate && (
              <ActionButton
                tone="secondary"
                startIcon={<PreviewIcon />}
                onClick={() =>
                  setPendingAction({
                    type: 'update',
                    channel: 'preview',
                    backup: true,
                    restorePrePreview: false,
                    titleKey: isPreviewVersion ? 'confirm.updatePreviewTitle' : 'confirm.previewTitle',
                    messageKey: isPreviewVersion
                      ? 'confirm.updatePreviewMessage'
                      : 'confirm.previewMessage',
                  })
                }
                disabled={!supportsPreview || isTaskActive || submitting}
              >
                {t(isPreviewVersion ? 'actions.updatePreview' : 'actions.switchPreview')}
              </ActionButton>
            )}
            {supportsRollback && isPreviewChannel && (
              <ActionButton
                tone="secondary"
                startIcon={<RollbackIcon />}
                onClick={() =>
                  setPendingAction({
                    type: 'update',
                    channel: 'rollback',
                    backup: false,
                    restorePrePreview: false,
                    titleKey: 'confirm.rollbackTitle',
                    messageKey: 'confirm.rollbackMessage',
                  })
                }
                disabled={isTaskActive || submitting}
              >
                {t('actions.rollbackStable')}
              </ActionButton>
            )}
            {supportsRollback && supportsRestore && isPreviewChannel && (
              <ActionButton
                tone="danger"
                startIcon={<RollbackIcon />}
                onClick={() =>
                  setPendingAction({
                    type: 'update',
                    channel: 'rollback',
                    backup: false,
                    restorePrePreview: true,
                    titleKey: 'confirm.restoreTitle',
                    messageKey: 'confirm.restoreMessage',
                    confirmTone: 'danger',
                  })
                }
                disabled={isTaskActive || submitting}
              >
                {t('actions.rollbackAndRestore')}
              </ActionButton>
            )}
          </Stack>

          <Divider sx={{ my: 2.5 }} />

          <Stack spacing={1.5}>
            <Stack
              direction={{ xs: 'column', sm: 'row' }}
              justifyContent="space-between"
              alignItems={{ xs: 'stretch', sm: 'center' }}
              gap={1}
            >
              <Box>
                <Typography variant="subtitle1" fontWeight={600}>
                  {t('backup.title')}
                </Typography>
                <Typography variant="caption" color="text.secondary">
                  {t('backup.subtitle')}
                </Typography>
              </Box>
              <ActionButton
                tone="ghost"
                size="small"
                startIcon={backupsLoading ? <CircularProgress size={16} /> : <RefreshIcon />}
                onClick={() => void loadBackups()}
                disabled={!supportsManualBackup || backupsLoading}
              >
                {t('actions.refreshBackups')}
              </ActionButton>
            </Stack>

            {backupsError && <Alert severity="warning">{backupsError}</Alert>}

            <Stack direction={{ xs: 'column', sm: 'row' }} gap={1} alignItems={{ sm: 'center' }}>
              <TextField
                size="small"
                value={backupName}
                onChange={event => setBackupName(event.target.value)}
                label={t('backup.nameLabel')}
                placeholder={t('backup.namePlaceholder')}
                disabled={!supportsManualBackup || isTaskActive || submitting}
                sx={{ minWidth: { sm: 260 }, flex: 1 }}
              />
              <ActionButton
                tone="secondary"
                startIcon={submitting ? <CircularProgress size={16} color="inherit" /> : <BackupIcon />}
                onClick={handleCreateBackup}
                disabled={!supportsManualBackup || isTaskActive || submitting}
              >
                {t('actions.createBackup')}
              </ActionButton>
            </Stack>

            <Stack spacing={1}>
              {backups.length === 0 ? (
                <Box
                  sx={{
                    minHeight: 72,
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    borderRadius: 1,
                    bgcolor: theme.palette.action.hover,
                  }}
                >
                  <Typography variant="body2" color="text.secondary">
                    {backupsLoading ? t('backup.loading') : t('backup.empty')}
                  </Typography>
                </Box>
              ) : (
                backups.map(item => (
                  <Box
                    key={item.backup_id}
                    sx={{
                      display: 'grid',
                      gridTemplateColumns: { xs: '1fr', md: 'minmax(0, 1fr) auto' },
                      gap: 1,
                      alignItems: 'center',
                      borderRadius: 1,
                      bgcolor: theme.palette.action.hover,
                      px: 1.5,
                      py: 1,
                    }}
                  >
                    <Box sx={{ minWidth: 0 }}>
                      <Typography noWrap title={item.filename} fontWeight={600}>
                        {t('backup.displayTitle', {
                          name: getBackupDisplayName(item, t('backup.unnamed')),
                          time: new Date(item.created_at).toLocaleString(),
                        })}
                      </Typography>
                      <Typography variant="caption" color="text.secondary" sx={{ display: 'block' }}>
                        {t('backup.meta', {
                          name: item.name || t('backup.unnamed'),
                          time: new Date(item.created_at).toLocaleString(),
                          size: formatBackupSize(item.size_bytes),
                        })}
                      </Typography>
                    </Box>
                    <ActionButton
                      tone="danger"
                      size="small"
                      startIcon={<RestoreIcon />}
                      onClick={() => handleRestoreBackup(item)}
                      disabled={!supportsManualRestore || isTaskActive || submitting}
                    >
                      {t('actions.restoreBackup')}
                    </ActionButton>
                  </Box>
                ))
              )}
            </Stack>
          </Stack>

          <Divider sx={{ my: 2.5 }} />

          <Box sx={{ minHeight: 172 }}>
            <Stack
              direction="row"
              justifyContent="space-between"
              alignItems="center"
              gap={1}
              mb={1.5}
            >
              <Box>
                <Typography variant="subtitle1" fontWeight={600}>
                  {t('job.title')}
                </Typography>
                <Typography variant="caption" color="text.secondary">
                  {job ? job.job_id : t('job.empty')}
                </Typography>
              </Box>
              <Stack direction="row" gap={1} alignItems="center">
                <Chip size="small" color={connectionColor} label={connectionLabel} />
                {job && (
                  <Chip
                    size="small"
                    color={STATUS_COLOR[job.status]}
                    label={t(`job.status.${job.status}`)}
                  />
                )}
              </Stack>
            </Stack>

            {connectionState === 'job_missing' && (
              <Alert severity="warning" sx={{ mb: 1.5 }}>
                {t('recovery.jobMissing')}
              </Alert>
            )}
            {connectionState === 'waiting_for_backend' && (
              <Alert severity="info" icon={<DisconnectedIcon />} sx={{ mb: 1.5 }}>
                {t('recovery.waiting')}
              </Alert>
            )}
            {trackingError && connectionState !== 'job_missing' && connectionState !== 'idle' && (
              <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mb: 1 }}>
                {t(`errors.${trackingError.code}`, { defaultValue: trackingError.message })}
              </Typography>
            )}

            {job ? (
              <Stack spacing={1.5}>
                <Box>
                  <Stack direction="row" justifyContent="space-between" mb={0.75}>
                    <Typography variant="body2">{t(`job.phase.${job.phase}`)}</Typography>
                    <Typography variant="body2" color="text.secondary">
                      {progressValue === undefined
                        ? t('job.progressPending')
                        : `${Math.round(progressValue)}%`}
                    </Typography>
                  </Stack>
                  <LinearProgress
                    variant={progressValue === undefined ? 'indeterminate' : 'determinate'}
                    value={progressValue}
                  />
                  <Typography
                    variant="caption"
                    color="text.secondary"
                    sx={{ display: 'block', mt: 0.75, minHeight: 20 }}
                  >
                    {job.progress?.label || t(`job.phaseDescription.${job.phase}`)}
                  </Typography>
                </Box>
                {job.error && (
                  <Alert severity="error" icon={<ErrorIcon />}>
                    <Typography variant="body2" fontWeight={600}>
                      {job.error.code}
                    </Typography>
                    <Typography variant="body2">{job.error.message}</Typography>
                  </Alert>
                )}
                {job.status === 'succeeded' && (
                  <Alert severity="success" icon={<SuccessIcon />}>
                    {t('job.succeededHint')}
                  </Alert>
                )}
                <Stack direction="row" justifyContent="flex-end" gap={1}>
                  {supportsCancel && isTaskActive && (
                    <ActionButton
                      tone="danger"
                      size="small"
                      startIcon={<CancelIcon />}
                      onClick={() => void handleCancel()}
                      disabled={isCancelling}
                    >
                      {t('actions.cancelJob')}
                    </ActionButton>
                  )}
                  {!isTaskActive && (
                    <ActionButton tone="ghost" size="small" onClick={dismissCompletedJob}>
                      {t('actions.clearResult')}
                    </ActionButton>
                  )}
                </Stack>
              </Stack>
            ) : (
              <Box
                sx={{
                  minHeight: 92,
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                }}
              >
                <Typography color="text.secondary">{t('job.noActiveTask')}</Typography>
              </Box>
            )}
          </Box>
        </Paper>

        <Paper sx={{ ...CARD_VARIANTS.elevated.styles, overflow: 'hidden' }}>
          <Stack
            direction={{ xs: 'column', sm: 'row' }}
            justifyContent="space-between"
            alignItems={{ xs: 'stretch', sm: 'center' }}
            gap={1}
            sx={{ px: { xs: 2, md: 2.5 }, py: 1.5 }}
          >
            <Box>
              <Typography variant="subtitle1" fontWeight={600}>
                {t('logs.title')}
              </Typography>
              <Typography variant="caption" color="text.secondary">
                {t('logs.lineCount', { count: logs.length })}
              </Typography>
            </Box>
            <Stack direction="row" alignItems="center" gap={0.5} justifyContent="flex-end">
              <FormControlLabel
                control={
                  <Switch
                    size="small"
                    checked={autoScroll}
                    onChange={event => setAutoScroll(event.target.checked)}
                  />
                }
                label={t('logs.autoScroll')}
                sx={{ mr: 0.5 }}
              />
              <Tooltip title={autoScroll ? t('logs.pause') : t('logs.resume')}>
                <span>
                  <IconActionButton
                    size="small"
                    onClick={() => setAutoScroll(value => !value)}
                    disabled={logs.length === 0}
                  >
                    {autoScroll ? <PauseIcon fontSize="small" /> : <PlayIcon fontSize="small" />}
                  </IconActionButton>
                </span>
              </Tooltip>
              <Tooltip title={t('logs.copy')}>
                <span>
                  <IconActionButton
                    size="small"
                    onClick={() => void handleCopyLogs()}
                    disabled={logs.length === 0}
                  >
                    <CopyIcon fontSize="small" />
                  </IconActionButton>
                </span>
              </Tooltip>
            </Stack>
          </Stack>
          <Divider />
          <Box
            ref={logContainerRef}
            sx={{
              height: { xs: 300, md: 360 },
              overflow: 'auto',
              p: 1.5,
              bgcolor: alpha(
                theme.palette.common.black,
                theme.palette.mode === 'dark' ? 0.24 : 0.04
              ),
              fontFamily: 'ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace',
              fontSize: '0.78rem',
              lineHeight: 1.65,
              ...SCROLLBAR_VARIANTS.thin.styles,
            }}
          >
            {logs.length === 0 ? (
              <Typography variant="body2" color="text.secondary" sx={{ fontFamily: 'inherit' }}>
                {t('logs.empty')}
              </Typography>
            ) : (
              logs.map(entry => (
                <Box key={entry.seq} sx={{ display: 'flex', gap: 1, minWidth: 0 }}>
                  <Box component="span" sx={{ color: 'text.secondary', flexShrink: 0 }}>
                    {entry.ts ? new Date(entry.ts).toLocaleTimeString() : `#${entry.seq}`}
                  </Box>
                  <Box
                    component="span"
                    sx={{
                      color:
                        entry.level === 'error'
                          ? 'error.main'
                          : entry.level === 'warning'
                            ? 'warning.main'
                            : 'text.primary',
                      whiteSpace: 'pre-wrap',
                      overflowWrap: 'anywhere',
                    }}
                  >
                    {entry.line}
                  </Box>
                </Box>
              ))
            )}
          </Box>
        </Paper>
      </Stack>

      <NekroDialog
        open={pendingAction !== null}
        onClose={() => !submitting && setPendingAction(null)}
        title={pendingAction ? t(pendingAction.titleKey) : ''}
        titleStartIcon={<WarningIcon color="warning" />}
        maxWidth="sm"
        actions={
          <>
            <ActionButton tone="ghost" onClick={() => setPendingAction(null)} disabled={submitting}>
              {t('actions.close')}
            </ActionButton>
            <ActionButton
              tone={pendingAction?.confirmTone ?? 'primary'}
              onClick={() => pendingAction && void submitDeploymentAction(pendingAction)}
              disabled={submitting}
              startIcon={submitting ? <CircularProgress size={16} color="inherit" /> : undefined}
            >
              {t('actions.confirm')}
            </ActionButton>
          </>
        }
      >
        <Stack spacing={1.5}>
          <Typography>
            {pendingAction ? t(pendingAction.messageKey, pendingAction.messageValues) : ''}
          </Typography>
          <Alert severity="warning">{t('confirm.restartWarning')}</Alert>
        </Stack>
      </NekroDialog>
    </Box>
  )
}
