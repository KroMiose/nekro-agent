import type { ReactNode } from 'react'
import AppsRoundedIcon from '@mui/icons-material/AppsRounded'
import CheckCircleRoundedIcon from '@mui/icons-material/CheckCircleRounded'
import ErrorRoundedIcon from '@mui/icons-material/ErrorRounded'
import PauseCircleRoundedIcon from '@mui/icons-material/PauseCircleRounded'
import { Box, Paper, Typography, useTheme } from '@mui/material'
import { useTranslation } from 'react-i18next'

export interface AdapterHubStatsData {
  total: number
  enabled: number
  failed: number
  disabled: number
}

function StatCard({
  value,
  label,
  icon,
  color,
}: {
  value: number
  label: string
  icon: ReactNode
  color: string
}) {
  return (
    <Paper
      variant="outlined"
      sx={{
        px: 2,
        py: 1.5,
        display: 'flex',
        alignItems: 'center',
        gap: 1.5,
        borderRadius: 2,
        minWidth: 140,
        flex: '1 1 0',
        borderColor: 'divider',
        bgcolor: 'background.paper',
      }}
    >
      <Box
        sx={{
          width: 36,
          height: 36,
          borderRadius: 1.5,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          bgcolor: color,
          color: '#fff',
          flexShrink: 0,
        }}
      >
        {icon}
      </Box>
      <Box sx={{ minWidth: 0 }}>
        <Typography variant="h6" sx={{ fontWeight: 700, lineHeight: 1.2 }}>
          {value}
        </Typography>
        <Typography variant="caption" color="text.secondary">
          {label}
        </Typography>
      </Box>
    </Paper>
  )
}

export default function AdapterHubStats({ stats }: { stats: AdapterHubStatsData }) {
  const theme = useTheme()
  const { t } = useTranslation('adapter')

  return (
    <Box
      sx={{
        display: 'flex',
        gap: 2,
        mb: 0.5,
        flexWrap: 'wrap',
        flexShrink: 0,
      }}
    >
      <StatCard
        value={stats.total}
        label={t('hub.statsLabel.total')}
        icon={<AppsRoundedIcon fontSize="small" />}
        color={theme.palette.primary.main}
      />
      <StatCard
        value={stats.enabled}
        label={t('hub.statsLabel.enabled')}
        icon={<CheckCircleRoundedIcon fontSize="small" />}
        color={theme.palette.success.main}
      />
      <StatCard
        value={stats.failed}
        label={t('hub.statsLabel.failed')}
        icon={<ErrorRoundedIcon fontSize="small" />}
        color={theme.palette.error.main}
      />
      <StatCard
        value={stats.disabled}
        label={t('hub.statsLabel.disabled')}
        icon={<PauseCircleRoundedIcon fontSize="small" />}
        color={theme.palette.warning.main}
      />
    </Box>
  )
}
