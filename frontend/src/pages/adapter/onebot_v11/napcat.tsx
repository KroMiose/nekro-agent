import { useState } from 'react'
import { Box, Alert, CircularProgress, Typography, Stack, Button } from '@mui/material'
import { LoadingButton } from '@mui/lab'
import { useQuery } from '@tanstack/react-query'
import { oneBotV11Api } from '../../../services/api/adapters/onebot_v11'
import { ContentCopy as ContentCopyIcon, OpenInNew as OpenInNewIcon } from '@mui/icons-material'
import { unifiedConfigApi } from '../../../services/api/unified-config'
import { useNotification } from '../../../hooks/useNotification'
import { CARD_VARIANTS } from '../../../theme/variants'
import { useTranslation } from 'react-i18next'
import { copyText } from '../../../utils/clipboard'

export default function OneBotV11NapCatPage() {
  const [iframeLoaded, setIframeLoaded] = useState(false)
  const notification = useNotification()
  const { t } = useTranslation('adapter')

  // 查询
  const { data: status } = useQuery({
    queryKey: ['onebot-v11-container-status'],
    queryFn: () => oneBotV11Api.getContainerStatus(),
    refetchInterval: 5000,
  })

  const { data: napCatConfig } = useQuery({
    queryKey: ['config', 'NAPCAT_ACCESS_URL'],
    queryFn: async () => {
      const response = await unifiedConfigApi.getConfigItem(
        'adapter_onebot_v11',
        'NAPCAT_ACCESS_URL'
      )
      return response.value as string
    },
  })

  const { data: onebotToken } = useQuery({
    queryKey: ['onebot-v11-onebot-token'],
    queryFn: () => oneBotV11Api.getOneBotToken(),
  })

  const { data: napcatToken } = useQuery({
    queryKey: ['onebot-v11-napcat-token'],
    queryFn: () => oneBotV11Api.getNapcatToken(),
    refetchInterval: 10000, // 每10秒刷新一次
  })

  const handleCopyOnebotToken = async () => {
    if (onebotToken) {
      const success = await copyText(onebotToken)
      if (success) {
        notification.success(t('napcat.accessKeyCopied'))
      } else {
        notification.error(t('napcat.copyFailed'))
      }
    }
  }

  const handleCopyNapcatToken = async () => {
    if (napcatToken) {
      const success = await copyText(napcatToken)
      if (success) {
        notification.success(t('napcat.tokenCopied'))
      } else {
        notification.error(t('napcat.copyFailed'))
      }
    }
  }

  const handleOpenNapcat = () => {
    if (napCatConfig) {
      window.open(napCatConfig, '_blank', 'noopener,noreferrer')
    }
  }

  return (
    <Box sx={{ p: 2, height: '100%', display: 'flex', flexDirection: 'column' }}>
      {(onebotToken || napcatToken) && (
        <Stack
          direction={{ xs: 'column', md: 'row' }}
          spacing={2}
          sx={{ mb: 2 }}
          alignItems="stretch"
        >
          {onebotToken && (
            <Alert
              severity="info"
              sx={{
                flex: 1,
                ...CARD_VARIANTS.default.styles,
                display: 'flex',
                alignItems: 'center',
              }}
              action={
                <LoadingButton
                  size="small"
                  startIcon={<ContentCopyIcon />}
                  onClick={handleCopyOnebotToken}
                >
                  {t('napcat.copy')}
                </LoadingButton>
              }
            >
              {t('napcat.onebotAccessKey')}: <strong>{onebotToken}</strong>
            </Alert>
          )}
          {napcatToken && (
            <Alert
              severity="success"
              sx={{
                flex: 1,
                ...CARD_VARIANTS.default.styles,
                display: 'flex',
                alignItems: 'center',
              }}
              action={
                <LoadingButton
                  size="small"
                  startIcon={<ContentCopyIcon />}
                  onClick={handleCopyNapcatToken}
                >
                  {t('napcat.copy')}
                </LoadingButton>
              }
            >
              {t('napcat.napcatToken')}: <strong>{napcatToken}</strong>
            </Alert>
          )}
          {napCatConfig && (
            <Button
              variant="contained"
              startIcon={<OpenInNewIcon />}
              onClick={handleOpenNapcat}
              sx={{
                whiteSpace: 'nowrap',
                alignSelf: 'center',
                height: 'fit-content',
              }}
            >
              {t('napcat.goToNapcat')}
            </Button>
          )}
        </Stack>
      )}
      <Box
        sx={{
          position: 'relative',
          height: onebotToken || napcatToken ? 'calc(100vh - 300px)' : 'calc(100vh - 240px)',
          flex: 1,
          '& iframe': {
            width: '100%',
            height: '100%',
            border: 'none',
            opacity: iframeLoaded ? 1 : 0,
            transition: 'opacity 0.3s',
          },
        }}
      >
        {napCatConfig && <iframe src={napCatConfig} onLoad={() => setIframeLoaded(true)} />}
        <Box
          sx={{
            position: 'absolute',
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            bgcolor: theme => theme.palette.background.paper,
            transition: 'opacity 0.3s',
            opacity: iframeLoaded && napCatConfig ? 0 : 1,
            pointerEvents: iframeLoaded && napCatConfig ? 'none' : 'auto',
          }}
        >
          {!napCatConfig ? (
            <Typography color="error">{t('napcat.cannotGetAddress')}</Typography>
          ) : !status?.running ? (
            <Typography color="error">{t('napcat.serviceNotRunning')}</Typography>
          ) : (
            <CircularProgress />
          )}
        </Box>
      </Box>
    </Box>
  )
}
