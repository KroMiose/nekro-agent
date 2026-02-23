import { Box, Typography, CircularProgress, IconButton, Tooltip, alpha } from '@mui/material'
import { ArrowBack as ArrowBackIcon } from '@mui/icons-material'
import { useTheme } from '@mui/material/styles'
import { useTranslation } from 'react-i18next'
import { motion, AnimatePresence } from 'framer-motion'
import { WorkspaceDetail, SandboxStatus } from '../../../services/api/workspace'
import WorkspaceStatusChip from './WorkspaceStatusChip'

export default function WorkspaceHeader({
  workspace,
  sandboxStatus,
  ccWorking,
  ccCurrentTool,
  onBack,
  onNavigateToSandbox,
}: {
  workspace: WorkspaceDetail
  sandboxStatus: SandboxStatus | undefined
  ccWorking: boolean
  ccCurrentTool: string | null
  onBack: () => void
  onNavigateToSandbox: () => void
}) {
  const theme = useTheme()
  const { t } = useTranslation('workspace')
  const currentStatus = sandboxStatus?.status ?? workspace.status

  return (
    <Box
      sx={{
        px: 3,
        py: 1.5,
        display: 'flex',
        alignItems: 'center',
        gap: 1.5,
        flexShrink: 0,
        // 玻璃 paper 背景：比卡片更不透明，作为结构性导航条
        backgroundColor: theme.palette.mode === 'dark'
          ? 'rgba(47, 47, 47, 0.95)'
          : 'rgba(250, 250, 250, 0.97)',
        backdropFilter: 'blur(12px)',
        WebkitBackdropFilter: 'blur(12px)',
        borderBottom: '1px solid',
        borderColor: theme.palette.mode === 'dark'
          ? 'rgba(255, 255, 255, 0.09)'
          : 'rgba(0, 0, 0, 0.10)',
        boxShadow: theme.palette.mode === 'dark'
          ? '0 2px 12px rgba(0, 0, 0, 0.30)'
          : '0 1px 8px rgba(0, 0, 0, 0.06)',
      }}
    >
      <Tooltip title={t('detail.header.backTooltip')}>
        <IconButton size="small" onClick={onBack}>
          <ArrowBackIcon fontSize="small" />
        </IconButton>
      </Tooltip>

      <Typography variant="h6" sx={{ fontWeight: 600 }}>
        {workspace.name}
      </Typography>

      <Box sx={{ flexGrow: 1 }} />

      {/* CC 执行中指示器 */}
      <AnimatePresence>
        {ccWorking && (
          <motion.div
            key="cc-working"
            initial={{ opacity: 0, x: 12 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: 12 }}
            transition={{ duration: 0.25 }}
          >
            <Box
              sx={{
                display: 'flex',
                alignItems: 'center',
                gap: 0.75,
                px: 1.25,
                py: 0.4,
                borderRadius: 5,
                bgcolor: alpha(theme.palette.success.main, 0.1),
                border: `1px solid ${alpha(theme.palette.success.main, 0.3)}`,
              }}
            >
              <CircularProgress
                size={12}
                thickness={5}
                sx={{ color: 'success.main', flexShrink: 0 }}
              />
              <Typography
                variant="caption"
                sx={{ color: 'success.main', fontSize: '0.72rem', fontWeight: 600, whiteSpace: 'nowrap' }}
              >
                {ccCurrentTool ? `${ccCurrentTool}` : t('detail.header.ccWorking')}
              </Typography>
            </Box>
          </motion.div>
        )}
      </AnimatePresence>

      {/* 沙盒状态展示，点击跳转到沙盒容器 Tab */}
      <Tooltip title={t('detail.header.viewSandboxTooltip')} placement="left">
        <Box
          onClick={onNavigateToSandbox}
          sx={{ cursor: 'pointer', display: 'flex', alignItems: 'center' }}
        >
          <WorkspaceStatusChip status={currentStatus} />
        </Box>
      </Tooltip>
    </Box>
  )
}
