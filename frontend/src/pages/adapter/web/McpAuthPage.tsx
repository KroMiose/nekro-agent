import { useEffect, useMemo, useState } from 'react'
import {
  Alert,
  Box,
  Card,
  Chip,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  Divider,
  FormControlLabel,
  Stack,
  Switch,
  TextField,
  Typography,
} from '@mui/material'
import { LoadingButton } from '@mui/lab'
import {
  AutoAwesome as AutoAwesomeIcon,
  ContentCopy as ContentCopyIcon,
  DeleteOutline as DeleteOutlineIcon,
  Key as KeyIcon,
  Save as SaveIcon,
} from '@mui/icons-material'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useTranslation } from 'react-i18next'
import ActionButton from '../../../components/common/ActionButton'
import IconActionButton from '../../../components/common/IconActionButton'
import { useNotification } from '../../../hooks/useNotification'
import { webAdapterApi } from '../../../services/api/adapters/web'
import { CARD_VARIANTS } from '../../../theme/variants'
import { copyText } from '../../../utils/clipboard'

const QUERY_KEY = ['adapter-web-mcp-auth']

export default function WebMcpAuthPage() {
  const { t, i18n } = useTranslation('adapter')
  const queryClient = useQueryClient()
  const notification = useNotification()
  const [enabled, setEnabled] = useState(false)
  const [manualToken, setManualToken] = useState('')
  const [generatedToken, setGeneratedToken] = useState('')
  const [clearDialogOpen, setClearDialogOpen] = useState(false)

  const { data, isLoading } = useQuery({
    queryKey: QUERY_KEY,
    queryFn: webAdapterApi.getMcpAuth,
  })

  useEffect(() => {
    if (data) {
      setEnabled(data.external.enabled)
    }
  }, [data])

  const updatedAt = useMemo(() => {
    const raw = data?.external.updated_at
    if (!raw) {
      return t('webMcpAuth.neverUpdated')
    }
    return new Intl.DateTimeFormat(i18n.language, {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
    }).format(new Date(raw))
  }, [data?.external.updated_at, i18n.language, t])

  const saveMutation = useMutation({
    mutationFn: () => webAdapterApi.updateExternalMcpAuth({
      enabled,
      token: manualToken.trim() || undefined,
    }),
    onSuccess: async response => {
      setGeneratedToken('')
      setManualToken('')
      setEnabled(response.external.enabled)
      await queryClient.invalidateQueries({ queryKey: QUERY_KEY })
      notification.success(t('webMcpAuth.notifications.saveSuccess'))
    },
    onError: error => {
      notification.error(error instanceof Error ? error.message : t('webMcpAuth.notifications.saveFailed'))
    },
  })

  const generateMutation = useMutation({
    mutationFn: webAdapterApi.generateExternalMcpAuth,
    onSuccess: async response => {
      setGeneratedToken(response.token)
      setManualToken('')
      setEnabled(response.external.enabled)
      await queryClient.invalidateQueries({ queryKey: QUERY_KEY })
      notification.success(t('webMcpAuth.notifications.generateSuccess'))
    },
    onError: error => {
      notification.error(error instanceof Error ? error.message : t('webMcpAuth.notifications.generateFailed'))
    },
  })

  const clearMutation = useMutation({
    mutationFn: webAdapterApi.clearExternalMcpAuth,
    onSuccess: async response => {
      setGeneratedToken('')
      setManualToken('')
      setEnabled(response.external.enabled)
      setClearDialogOpen(false)
      await queryClient.invalidateQueries({ queryKey: QUERY_KEY })
      notification.success(t('webMcpAuth.notifications.clearSuccess'))
    },
    onError: error => {
      notification.error(error instanceof Error ? error.message : t('webMcpAuth.notifications.clearFailed'))
    },
  })

  const handleCopy = async (value: string) => {
    const success = await copyText(value)
    if (success) {
      notification.success(t('webMcpAuth.notifications.copySuccess'))
    } else {
      notification.error(t('webMcpAuth.notifications.copyFailed'))
    }
  }

  return (
    <Box sx={{ p: 2, height: '100%', boxSizing: 'border-box', overflow: 'auto' }}>
      <Stack spacing={2}>
        <Card sx={{ ...CARD_VARIANTS.default.styles, p: { xs: 2, md: 2.5 } }}>
          <Stack spacing={2}>
            <Stack direction={{ xs: 'column', md: 'row' }} spacing={2} alignItems={{ xs: 'stretch', md: 'center' }}>
              <Box sx={{ flex: 1, minWidth: 0 }}>
                <Typography variant="h6" sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                  <KeyIcon fontSize="small" />
                  {t('webMcpAuth.title')}
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  {t('webMcpAuth.externalToken')}
                </Typography>
              </Box>
              <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
                <Chip
                  color={data?.external.enabled ? 'success' : 'default'}
                  label={data?.external.enabled ? t('webMcpAuth.enabled') : t('webMcpAuth.disabled')}
                  size="small"
                />
                <Chip
                  color={data?.external.configured ? 'info' : 'default'}
                  label={data?.external.configured ? t('webMcpAuth.configured') : t('webMcpAuth.notConfigured')}
                  size="small"
                  variant="outlined"
                />
              </Stack>
            </Stack>

            <Divider />

            <Stack spacing={1}>
              <Typography variant="caption" color="text.secondary">
                {t('webMcpAuth.mcpUrl')}
              </Typography>
              <TextField
                value={data?.mcp_url ?? ''}
                size="small"
                fullWidth
                disabled={isLoading}
                InputProps={{
                  readOnly: true,
                  endAdornment: data?.mcp_url ? (
                    <IconActionButton
                      size="small"
                      aria-label={t('webMcpAuth.copy')}
                      onClick={() => handleCopy(data.mcp_url)}
                    >
                      <ContentCopyIcon fontSize="small" />
                    </IconActionButton>
                  ) : null,
                }}
              />
            </Stack>

            <Stack direction={{ xs: 'column', sm: 'row' }} spacing={1.5}>
              <Box sx={{ flex: 1 }}>
                <Typography variant="caption" color="text.secondary">
                  {t('webMcpAuth.tokenPreview')}
                </Typography>
                <Typography variant="body2" sx={{ mt: 0.5, fontFamily: 'monospace' }}>
                  {data?.external.token_preview ?? '-'}
                </Typography>
              </Box>
              <Box sx={{ flex: 1 }}>
                <Typography variant="caption" color="text.secondary">
                  {t('webMcpAuth.updatedAt')}
                </Typography>
                <Typography variant="body2" sx={{ mt: 0.5 }}>
                  {updatedAt}
                </Typography>
              </Box>
            </Stack>
          </Stack>
        </Card>

        <Card sx={{ ...CARD_VARIANTS.default.styles, p: { xs: 2, md: 2.5 } }}>
          <Stack spacing={2}>
            <FormControlLabel
              control={
                <Switch
                  checked={enabled}
                  onChange={event => setEnabled(event.target.checked)}
                  disabled={saveMutation.isPending || generateMutation.isPending || clearMutation.isPending}
                />
              }
              label={t('webMcpAuth.enabled')}
            />

            <TextField
              label={t('webMcpAuth.manualToken')}
              placeholder={t('webMcpAuth.manualTokenPlaceholder')}
              value={manualToken}
              type="password"
              fullWidth
              onChange={event => setManualToken(event.target.value)}
              inputProps={{ maxLength: 512 }}
            />

            <Stack direction={{ xs: 'column', sm: 'row' }} spacing={1.5}>
              <LoadingButton
                loading={saveMutation.isPending}
                loadingPosition="start"
                startIcon={<SaveIcon />}
                onClick={() => saveMutation.mutate()}
                variant="contained"
              >
                {t('webMcpAuth.save')}
              </LoadingButton>
              <LoadingButton
                loading={generateMutation.isPending}
                loadingPosition="start"
                startIcon={<AutoAwesomeIcon />}
                onClick={() => generateMutation.mutate()}
                variant="outlined"
              >
                {t('webMcpAuth.generate')}
              </LoadingButton>
              <ActionButton
                tone="danger"
                startIcon={<DeleteOutlineIcon />}
                onClick={() => setClearDialogOpen(true)}
                disabled={!data?.external.configured || clearMutation.isPending}
              >
                {t('webMcpAuth.clear')}
              </ActionButton>
            </Stack>
          </Stack>
        </Card>

        {generatedToken && (
          <Alert
            severity="success"
            sx={{ ...CARD_VARIANTS.default.styles, alignItems: 'center' }}
            action={
              <IconActionButton
                size="small"
                aria-label={t('webMcpAuth.copy')}
                onClick={() => handleCopy(generatedToken)}
              >
                <ContentCopyIcon fontSize="small" />
              </IconActionButton>
            }
          >
            <Typography variant="subtitle2" sx={{ mb: 1 }}>
              {t('webMcpAuth.generatedTitle')}
            </Typography>
            <Typography variant="body2" sx={{ fontFamily: 'monospace', wordBreak: 'break-all' }}>
              {generatedToken}
            </Typography>
            <Typography variant="caption" color="text.secondary">
              {t('webMcpAuth.generatedHint')}
            </Typography>
          </Alert>
        )}
      </Stack>

      <Dialog open={clearDialogOpen} onClose={() => setClearDialogOpen(false)} maxWidth="xs" fullWidth>
        <DialogTitle>{t('webMcpAuth.clearDialogTitle')}</DialogTitle>
        <DialogContent>
          <Typography variant="body2" color="text.secondary">
            {t('webMcpAuth.clearDialogContent')}
          </Typography>
        </DialogContent>
        <DialogActions>
          <ActionButton tone="ghost" onClick={() => setClearDialogOpen(false)}>
            {t('webMcpAuth.cancel')}
          </ActionButton>
          <LoadingButton
            color="error"
            loading={clearMutation.isPending}
            onClick={() => clearMutation.mutate()}
            startIcon={<DeleteOutlineIcon />}
          >
            {t('webMcpAuth.clear')}
          </LoadingButton>
        </DialogActions>
      </Dialog>
    </Box>
  )
}
