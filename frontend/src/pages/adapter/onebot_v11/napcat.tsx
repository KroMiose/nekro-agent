import { useState } from 'react'
import { Box, Alert, CircularProgress, Typography } from '@mui/material'
import { LoadingButton } from '@mui/lab'
import { useQuery } from '@tanstack/react-query'
import { oneBotV11Api } from '../../../services/api/adapters/onebot_v11'
import { ContentCopy as ContentCopyIcon } from '@mui/icons-material'
import { unifiedConfigApi } from '../../../services/api/unified-config'
import { useNotification } from '../../../hooks/useNotification'
import { CARD_VARIANTS } from '../../../theme/variants'

export default function OneBotV11NapCatPage() {
  const [iframeLoaded, setIframeLoaded] = useState(false)
  const notification = useNotification()

  // 查询
  const { data: status } = useQuery({
    queryKey: ['onebot-v11-container-status'],
    queryFn: () => oneBotV11Api.getContainerStatus(),
    refetchInterval: 5000,
  })

  const { data: napCatConfig } = useQuery({
    queryKey: ['config', 'NAPCAT_ACCESS_URL'],
    queryFn: async () => {
      const response = await unifiedConfigApi.getConfigItem('adapter_onebot_v11', 'NAPCAT_ACCESS_URL')
      return response.value as string
    },
  })

  const { data: onebotToken } = useQuery({
    queryKey: ['onebot-v11-onebot-token'],
    queryFn: () => oneBotV11Api.getOneBotToken(),
  })

  const handleCopyOnebotToken = async () => {
    if (onebotToken) {
      try {
        await navigator.clipboard.writeText(onebotToken)
        notification.success('访问密钥已复制到剪贴板')
      } catch (error) {
        console.error('复制失败:', error)
        notification.error('复制失败，请手动复制')
      }
    }
  }

  return (
    <Box sx={{ p: 2, height: '100%', display: 'flex', flexDirection: 'column' }}>
      {onebotToken && (
        <Alert
          severity="info"
          sx={{ mb: 2, ...CARD_VARIANTS.default.styles }}
          action={
            <LoadingButton
              size="small"
              startIcon={<ContentCopyIcon />}
              onClick={handleCopyOnebotToken}
            >
              复制
            </LoadingButton>
          }
        >
          OneBot 服务访问密钥: <strong>{onebotToken}</strong>
        </Alert>
      )}
      <Box
        sx={{
          position: 'relative',
          height: onebotToken ? 'calc(100vh - 300px)' : 'calc(100vh - 240px)',
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
            <Typography color="error">无法获取 NapCat 访问地址</Typography>
          ) : !status?.running ? (
            <Typography color="error">NapCat 服务未运行</Typography>
          ) : (
            <CircularProgress />
          )}
        </Box>
      </Box>
    </Box>
  )
}
