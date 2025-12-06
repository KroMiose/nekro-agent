import { useState } from 'react'
<<<<<<< HEAD
=======
<<<<<<< HEAD
=======
<<<<<<< HEAD
>>>>>>> a776096 (增加PYPI源自定义和代理功能)
>>>>>>> e26199f (增加PYPI源自定义和代理功能)
import { Box, Alert, CircularProgress, Typography, Stack, Button } from '@mui/material'
import { LoadingButton } from '@mui/lab'
import { useQuery } from '@tanstack/react-query'
import { oneBotV11Api } from '../../../services/api/adapters/onebot_v11'
import { ContentCopy as ContentCopyIcon, OpenInNew as OpenInNewIcon } from '@mui/icons-material'
<<<<<<< HEAD
=======
<<<<<<< HEAD
=======
=======
import { Box, Alert, CircularProgress, Typography } from '@mui/material'
import { LoadingButton } from '@mui/lab'
import { useQuery } from '@tanstack/react-query'
import { oneBotV11Api } from '../../../services/api/adapters/onebot_v11'
import { ContentCopy as ContentCopyIcon } from '@mui/icons-material'
>>>>>>> 6cf9d37 (增加PYPI源自定义和代理功能)
>>>>>>> a776096 (增加PYPI源自定义和代理功能)
>>>>>>> e26199f (增加PYPI源自定义和代理功能)
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

<<<<<<< HEAD
=======
<<<<<<< HEAD
=======
<<<<<<< HEAD
>>>>>>> a776096 (增加PYPI源自定义和代理功能)
>>>>>>> e26199f (增加PYPI源自定义和代理功能)
  const { data: napcatToken } = useQuery({
    queryKey: ['onebot-v11-napcat-token'],
    queryFn: () => oneBotV11Api.getNapcatToken(),
    refetchInterval: 10000, // 每10秒刷新一次
  })

<<<<<<< HEAD
=======
<<<<<<< HEAD
=======
=======
>>>>>>> 6cf9d37 (增加PYPI源自定义和代理功能)
>>>>>>> a776096 (增加PYPI源自定义和代理功能)
>>>>>>> e26199f (增加PYPI源自定义和代理功能)
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

<<<<<<< HEAD
=======
<<<<<<< HEAD
=======
<<<<<<< HEAD
>>>>>>> a776096 (增加PYPI源自定义和代理功能)
>>>>>>> e26199f (增加PYPI源自定义和代理功能)
  const handleCopyNapcatToken = async () => {
    if (napcatToken) {
      try {
        await navigator.clipboard.writeText(napcatToken)
        notification.success('NapCat WebUI Token 已复制到剪贴板')
      } catch (error) {
        console.error('复制失败:', error)
        notification.error('复制失败，请手动复制')
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
                  复制
                </LoadingButton>
              }
            >
              OneBot 服务访问密钥: <strong>{onebotToken}</strong>
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
                  复制
                </LoadingButton>
              }
            >
              NapCat 登录 Token: <strong>{napcatToken}</strong>
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
              前往 NapCat
            </Button>
          )}
        </Stack>
<<<<<<< HEAD
=======
<<<<<<< HEAD
=======
=======
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
>>>>>>> 6cf9d37 (增加PYPI源自定义和代理功能)
>>>>>>> a776096 (增加PYPI源自定义和代理功能)
>>>>>>> e26199f (增加PYPI源自定义和代理功能)
      )}
      <Box
        sx={{
          position: 'relative',
<<<<<<< HEAD
          height:
            onebotToken || napcatToken ? 'calc(100vh - 300px)' : 'calc(100vh - 240px)',
=======
<<<<<<< HEAD
          height:
            onebotToken || napcatToken ? 'calc(100vh - 300px)' : 'calc(100vh - 240px)',
=======
<<<<<<< HEAD
          height:
            onebotToken || napcatToken ? 'calc(100vh - 300px)' : 'calc(100vh - 240px)',
=======
          height: onebotToken ? 'calc(100vh - 300px)' : 'calc(100vh - 240px)',
>>>>>>> 6cf9d37 (增加PYPI源自定义和代理功能)
>>>>>>> a776096 (增加PYPI源自定义和代理功能)
>>>>>>> e26199f (增加PYPI源自定义和代理功能)
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
