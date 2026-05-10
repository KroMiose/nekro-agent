import { Alert, Box, Card, CardContent, Chip, Stack, Typography, useTheme } from '@mui/material'
import { ContentCopy as ContentCopyIcon, OpenInNew as OpenInNewIcon } from '@mui/icons-material'
import { QRCodeSVG } from 'qrcode.react'
import { useTranslation } from 'react-i18next'
import ActionButton from '../../../components/common/ActionButton'
import { useNotification } from '../../../hooks/useNotification'
import type { WechatOpenILinkLoginStatus } from '../../../services/api/adapters/wechat_openilink'
import { CARD_VARIANTS } from '../../../theme/variants'
import { copyText } from '../../../utils/clipboard'

interface OpenILinkLoginCardProps {
  status?: WechatOpenILinkLoginStatus
  isLoading: boolean
}

const getSeverity = (state?: string) => {
  if (state === 'logged_in') {
    return 'success'
  }
  if (state === 'error' || state === 'expired' || state === 'stopped' || state === 'unavailable') {
    return 'warning'
  }
  return 'info'
}

export default function OpenILinkLoginCard({ status, isLoading }: OpenILinkLoginCardProps) {
  const theme = useTheme()
  const { t } = useTranslation('adapter')
  const notification = useNotification()
  const loginUrl = status?.login_url
  const state = status?.state ?? 'idle'
  const stateText = t(`openilinkLogin.states.${state}`, { defaultValue: t('openilinkLogin.states.unknown') })

  const handleCopyLoginUrl = async () => {
    if (!loginUrl) {
      return
    }

    const success = await copyText(loginUrl)
    if (success) {
      notification.success(t('openilinkLogin.copySuccess'))
    } else {
      notification.error(t('openilinkLogin.copyFailed'))
    }
  }

  const handleOpenLoginUrl = () => {
    if (loginUrl) {
      window.open(loginUrl, '_blank', 'noopener,noreferrer')
    }
  }

  return (
    <Card sx={{ ...CARD_VARIANTS.default.styles, height: '100%' }}>
      <CardContent sx={{ p: { xs: 2, md: 3 }, height: '100%', boxSizing: 'border-box' }}>
        <Stack spacing={2.5} sx={{ height: '100%' }}>
          <Box sx={{ display: 'flex', justifyContent: 'space-between', gap: 2, alignItems: 'flex-start' }}>
            <Box>
              <Typography variant="h5" sx={{ fontWeight: 700, mb: 0.75 }}>
                {t('openilinkLogin.title')}
              </Typography>
              <Typography variant="body2" color="text.secondary">
                {t('openilinkLogin.description')}
              </Typography>
            </Box>
            <Chip label={isLoading ? t('openilinkLogin.loading') : stateText} color={getSeverity(state)} />
          </Box>

          <Alert severity={getSeverity(state)} sx={{ ...CARD_VARIANTS.default.styles }}>
            {status?.logged_in
              ? t('openilinkLogin.loggedInMessage', {
                  name: status.self_user_name || status.self_user_id || t('openilinkLogin.unknownAccount'),
                })
              : status?.error_message || t(`openilinkLogin.messages.${state}`, { defaultValue: t('openilinkLogin.messages.idle') })}
          </Alert>

          <Box
            sx={{
              flex: 1,
              minHeight: 280,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              border: '1px solid',
              borderColor: 'divider',
              borderRadius: 3,
              bgcolor: theme.palette.background.default,
              p: 3,
            }}
          >
            {loginUrl && !status?.logged_in ? (
              <Box
                sx={{
                  p: 2,
                  borderRadius: 2,
                  bgcolor: theme.palette.common.white,
                  color: theme.palette.common.black,
                  lineHeight: 0,
                }}
              >
                <QRCodeSVG value={loginUrl} size={220} level="M" includeMargin />
              </Box>
            ) : (
              <Typography variant="body2" color="text.secondary" textAlign="center">
                {status?.logged_in ? t('openilinkLogin.noQrLoggedIn') : t('openilinkLogin.waitingQr')}
              </Typography>
            )}
          </Box>

          {loginUrl ? (
            <Stack direction={{ xs: 'column', sm: 'row' }} spacing={1.5}>
              <ActionButton variant="contained" startIcon={<ContentCopyIcon />} onClick={handleCopyLoginUrl}>
                {t('openilinkLogin.copyLink')}
              </ActionButton>
              <ActionButton variant="outlined" startIcon={<OpenInNewIcon />} onClick={handleOpenLoginUrl}>
                {t('openilinkLogin.openLink')}
              </ActionButton>
            </Stack>
          ) : null}
        </Stack>
      </CardContent>
    </Card>
  )
}
