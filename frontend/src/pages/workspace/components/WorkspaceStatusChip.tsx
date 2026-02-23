import { Box, Chip, alpha } from '@mui/material'
import { useTheme } from '@mui/material/styles'
import { useTranslation } from 'react-i18next'
import { CHIP_VARIANTS } from '../../../theme/variants'

export default function WorkspaceStatusChip({ status }: { status: string }) {
  const theme = useTheme()
  const { t } = useTranslation('workspace')
  const statusConfig: Record<string, { label: string; color: string }> = {
    active: { label: t('statusChip.active'), color: theme.palette.success.main },
    stopped: { label: t('status.stopped'), color: theme.palette.text.secondary as string },
    failed: { label: t('status.failed'), color: theme.palette.error.main },
    deleting: { label: t('status.deleting'), color: theme.palette.warning.main },
  }
  const config = statusConfig[status] ?? { label: status, color: theme.palette.text.secondary as string }
  const isActive = status === 'active'
  return (
    <Chip
      label={
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.75 }}>
          {config.label}
          <Box
            sx={{
              width: 7,
              height: 7,
              borderRadius: '50%',
              bgcolor: config.color,
              flexShrink: 0,
              ...(isActive ? {
                animation: 'wscPulseDot 2s ease-in-out infinite',
                '@keyframes wscPulseDot': {
                  '0%, 100%': { opacity: 1, transform: 'scale(1)' },
                  '50%': { opacity: 0.45, transform: 'scale(0.7)' },
                },
              } : {}),
            }}
          />
        </Box>
      }
      size="small"
      sx={{
        ...CHIP_VARIANTS.base(true),
        borderColor: alpha(config.color, 0.35),
        '& .MuiChip-label': { px: 1.25 },
      }}
    />
  )
}
