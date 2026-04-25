import AppsRoundedIcon from '@mui/icons-material/AppsRounded'
import CheckCircleRoundedIcon from '@mui/icons-material/CheckCircleRounded'
import ErrorRoundedIcon from '@mui/icons-material/ErrorRounded'
import PauseCircleRoundedIcon from '@mui/icons-material/PauseCircleRounded'
import { Box, useTheme } from '@mui/material'
import { useTranslation } from 'react-i18next'
import StatCard from '../../../components/common/StatCard'

export interface AdapterHubStatsData {
  total: number
  enabled: number
  failed: number
  disabled: number
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
