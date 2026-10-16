import { useTranslation } from 'react-i18next'
import { useNavigate, useRouteError } from 'react-router-dom'
import { Box, Button, Paper, Stack, Typography } from '@mui/material'
import RefreshOutlinedIcon from '@mui/icons-material/RefreshOutlined'
import ReportProblemOutlinedIcon from '@mui/icons-material/ReportProblemOutlined'

/**
 * 路由渲染失败的兜底页面。
 * 只负责提示与恢复，不做任何鉴权跳转——登录态失效由 axios 拦截器处理。
 */
export default function RouteErrorPage() {
  const { t } = useTranslation('errors')
  const navigate = useNavigate()
  const error = useRouteError()
  const detail = error instanceof Error ? error.message : ''

  return (
    <Box
      sx={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        width: '100%',
        height: '100%',
        minHeight: 320,
        p: 2
      }}
    >
      <Paper variant="outlined" sx={{ p: 3, maxWidth: 520, textAlign: 'center' }}>
        <Stack spacing={2} alignItems="center">
          <ReportProblemOutlinedIcon color="warning" sx={{ fontSize: 40 }} />
          <Box>
            <Typography variant="h6">{t('routeLoadFailedTitle')}</Typography>
            <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
              {t('routeLoadFailedDescription')}
            </Typography>
          </Box>
          {detail && (
            <Typography
              variant="caption"
              component="p"
              color="text.secondary"
              sx={{ wordBreak: 'break-all', fontFamily: 'monospace' }}
            >
              {detail}
            </Typography>
          )}
          <Stack direction="row" spacing={1}>
            <Button variant="contained" startIcon={<RefreshOutlinedIcon />} onClick={() => window.location.reload()}>
              {t('routeLoadFailedRetry')}
            </Button>
            <Button variant="outlined" onClick={() => navigate('/dashboard')}>
              {t('routeLoadFailedBackToDashboard')}
            </Button>
          </Stack>
        </Stack>
      </Paper>
    </Box>
  )
}
