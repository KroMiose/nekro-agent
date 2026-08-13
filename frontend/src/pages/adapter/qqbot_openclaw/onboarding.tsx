import {
  Alert,
  Box,
  Button,
  Chip,
  Divider,
  LinearProgress,
  Paper,
  Stack,
  Typography,
} from '@mui/material'
import {
  CheckCircle as CheckCircleIcon,
  DeleteSweep as DeleteSweepIcon,
  Key as KeyIcon,
  OpenInNew as OpenInNewIcon,
  QrCode2 as QrCodeIcon,
  Refresh as RefreshIcon,
  RestartAlt as RestartAltIcon,
  Settings as SettingsIcon,
} from '@mui/icons-material'
import { QRCodeSVG } from 'qrcode.react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useTranslation } from 'react-i18next'
import type { ReactNode } from 'react'
import { qqbotOpenClawApi } from '../../../services/api/adapters/qqbot_openclaw'
import { useNotification } from '../../../hooks/useNotification'

const OPENCLAW_ONBOARDING_URL = 'https://q.qq.com/qqbot/openclaw/index.html'

function useQQBotActionMutation(action: () => Promise<{ success: boolean; message: string }>) {
  const { t } = useTranslation('adapter')
  const notification = useNotification()
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: action,
    onSuccess: result => {
      if (result.success) {
        notification.success(result.message)
      } else {
        notification.error(result.message)
      }
      queryClient.invalidateQueries({ queryKey: ['qqbot-openclaw-status'] })
    },
    onError: error => {
      notification.error(error instanceof Error ? error.message : t('qqbotOpenClaw.actionFailed'))
    },
  })
}

export default function QQBotOpenClawOnboardingPage() {
  const { t } = useTranslation('adapter')

  const { data: status, isLoading, refetch } = useQuery({
    queryKey: ['qqbot-openclaw-status'],
    queryFn: () => qqbotOpenClawApi.getStatus(),
    refetchInterval: 5000,
  })

  const restartMutation = useQQBotActionMutation(qqbotOpenClawApi.restartGateway)
  const tokenMutation = useQQBotActionMutation(qqbotOpenClawApi.testToken)
  const clearRefMutation = useQQBotActionMutation(qqbotOpenClawApi.clearRefIndex)
  const clearSessionMutation = useQQBotActionMutation(qqbotOpenClawApi.clearSession)

  const onboardingUrl = status?.onboarding_url || OPENCLAW_ONBOARDING_URL
  const progress = status?.connected ? 100 : status?.running ? 66 : status?.configured ? 34 : 0

  return (
    <Box sx={{ p: { xs: 1, sm: 2 }, height: '100%', boxSizing: 'border-box', overflow: 'auto' }}>
      <Stack spacing={2}>
        <Paper variant="outlined" sx={{ p: { xs: 2, md: 2.5 }, borderRadius: 2 }}>
          <Stack spacing={2.5}>
            <Stack direction={{ xs: 'column', lg: 'row' }} spacing={2.5} alignItems={{ xs: 'stretch', lg: 'flex-start' }}>
              <Box sx={{ flex: 1, minWidth: 0 }}>
                <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap sx={{ mb: 1.5 }}>
                  <StateChip active={Boolean(status?.configured)} label={status?.configured ? t('qqbotOpenClaw.configured') : t('qqbotOpenClaw.notConfigured')} />
                  <StateChip active={Boolean(status?.running)} label={status?.running ? t('qqbotOpenClaw.running') : t('qqbotOpenClaw.stopped')} />
                  <StateChip active={Boolean(status?.connected)} label={status?.connected ? t('qqbotOpenClaw.connected') : t('qqbotOpenClaw.disconnected')} />
                </Stack>
                <Typography variant="h6" sx={{ mb: 0.75, fontWeight: 700 }}>
                  {t('qqbotOpenClaw.title')}
                </Typography>
                <Typography variant="body2" color="text.secondary" sx={{ maxWidth: 820 }}>
                  {t('qqbotOpenClaw.description')}
                </Typography>
                <LinearProgress variant="determinate" value={progress} sx={{ mt: 2, maxWidth: 720, height: 6, borderRadius: 1 }} />

                <Box
                  sx={{
                    display: 'grid',
                    gridTemplateColumns: { xs: '1fr', md: 'repeat(3, minmax(0, 1fr))' },
                    gap: 1.5,
                    mt: 2,
                  }}
                >
                  <StepItem index="1" icon={<QrCodeIcon fontSize="small" />} title={t('qqbotOpenClaw.stepScanTitle')} body={t('qqbotOpenClaw.stepScanBody')} />
                  <StepItem index="2" icon={<KeyIcon fontSize="small" />} title={t('qqbotOpenClaw.stepCredentialTitle')} body={t('qqbotOpenClaw.stepCredentialBody')} />
                  <StepItem index="3" icon={<RestartAltIcon fontSize="small" />} title={t('qqbotOpenClaw.stepConnectTitle')} body={t('qqbotOpenClaw.stepConnectBody')} />
                </Box>
              </Box>

              <Box
                sx={{
                  width: { xs: '100%', lg: 260 },
                  flexShrink: 0,
                  border: theme => `1px solid ${theme.palette.divider}`,
                  borderRadius: 2,
                  p: 2,
                  bgcolor: theme => theme.palette.action.hover,
                }}
              >
                <Stack spacing={1.5} alignItems="center">
                  <Typography variant="subtitle2" sx={{ alignSelf: 'flex-start' }}>
                    {t('qqbotOpenClaw.scanEntry')}
                  </Typography>
                  <Box sx={{ bgcolor: '#fff', p: 1.25, borderRadius: 1 }}>
                    <QRCodeSVG value={onboardingUrl} size={164} level="M" includeMargin />
                  </Box>
                  <Button fullWidth size="small" variant="contained" endIcon={<OpenInNewIcon />} href={onboardingUrl} target="_blank" rel="noreferrer">
                    {t('qqbotOpenClaw.openConsole')}
                  </Button>
                </Stack>
              </Box>
            </Stack>

            {!status?.configured && !isLoading && (
              <Alert severity="warning" icon={<SettingsIcon />}>
                {t('qqbotOpenClaw.configureHint')}
              </Alert>
            )}
            {status?.last_error && <Alert severity="error">{status.last_error}</Alert>}
          </Stack>
        </Paper>

        <Paper variant="outlined" sx={{ p: 2, borderRadius: 2 }}>
          <Stack direction={{ xs: 'column', md: 'row' }} spacing={1.5} alignItems={{ xs: 'stretch', md: 'center' }} justifyContent="space-between">
            <Box>
              <Typography variant="subtitle1" sx={{ fontWeight: 700 }}>
                {t('qqbotOpenClaw.maintenance')}
              </Typography>
              <Typography variant="body2" color="text.secondary">
                {t('qqbotOpenClaw.maintenanceHint')}
              </Typography>
            </Box>
            <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
              <Button variant="outlined" startIcon={<RefreshIcon />} onClick={() => refetch()} disabled={isLoading}>
                {t('qqbotOpenClaw.refresh')}
              </Button>
              <Button variant="outlined" startIcon={<KeyIcon />} onClick={() => tokenMutation.mutate()} disabled={tokenMutation.isPending}>
                {t('qqbotOpenClaw.testToken')}
              </Button>
              <Button variant="contained" startIcon={<RestartAltIcon />} onClick={() => restartMutation.mutate()} disabled={restartMutation.isPending}>
                {t('qqbotOpenClaw.restartGateway')}
              </Button>
              <Button variant="outlined" color="warning" startIcon={<DeleteSweepIcon />} onClick={() => clearSessionMutation.mutate()} disabled={clearSessionMutation.isPending}>
                {t('qqbotOpenClaw.clearSession')}
              </Button>
              <Button variant="outlined" color="warning" startIcon={<DeleteSweepIcon />} onClick={() => clearRefMutation.mutate()} disabled={clearRefMutation.isPending}>
                {t('qqbotOpenClaw.clearRefs')}
              </Button>
            </Stack>
          </Stack>
        </Paper>

        <Paper variant="outlined" sx={{ p: 2, borderRadius: 2 }}>
          <Typography variant="subtitle1" sx={{ fontWeight: 700 }}>
            {t('qqbotOpenClaw.details')}
          </Typography>
          <Divider sx={{ my: 1.5 }} />
          <Box
            sx={{
              display: 'grid',
              gridTemplateColumns: { xs: '1fr', sm: 'repeat(2, minmax(0, 1fr))', xl: 'repeat(4, minmax(0, 1fr))' },
              gap: 1.25,
            }}
          >
            <Detail label={t('qqbotOpenClaw.appId')} value={status?.app_id || '-'} />
            <Detail label={t('qqbotOpenClaw.selfUserId')} value={status?.self_user_id || '-'} />
            <Detail label={t('qqbotOpenClaw.sessionId')} value={status?.session_id || '-'} />
            <Detail label={t('qqbotOpenClaw.lastSeq')} value={status?.last_seq?.toString() || '-'} />
            <Detail label={t('qqbotOpenClaw.refEntries')} value={status?.ref_index_entries?.toString() || '0'} />
          </Box>
        </Paper>
      </Stack>
    </Box>
  )
}

function StateChip({ active, label }: { active: boolean; label: string }) {
  return (
    <Chip
      size="small"
      color={active ? 'success' : 'default'}
      icon={active ? <CheckCircleIcon /> : undefined}
      label={label}
      sx={{ borderRadius: 1 }}
    />
  )
}

function StepItem({ index, icon, title, body }: { index: string; icon: ReactNode; title: string; body: string }) {
  return (
    <Box sx={{ border: theme => `1px solid ${theme.palette.divider}`, borderRadius: 2, p: 1.5, minWidth: 0 }}>
      <Stack direction="row" spacing={1} alignItems="center" sx={{ mb: 0.75 }}>
        <Chip size="small" label={index} sx={{ width: 26, height: 26, borderRadius: '50%', '& .MuiChip-label': { px: 0 } }} />
        {icon}
        <Typography variant="subtitle2" noWrap>
          {title}
        </Typography>
      </Stack>
      <Typography variant="body2" color="text.secondary">
        {body}
      </Typography>
    </Box>
  )
}

function Detail({ label, value }: { label: string; value: string }) {
  return (
    <Box sx={{ minWidth: 0 }}>
      <Typography variant="caption" color="text.secondary">
        {label}
      </Typography>
      <Typography variant="body2" sx={{ wordBreak: 'break-all', mt: 0.25 }}>
        {value}
      </Typography>
    </Box>
  )
}
