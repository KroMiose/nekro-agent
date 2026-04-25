import { Box, Card, CardContent, Skeleton, Typography } from '@mui/material'
import type { ReactNode } from 'react'
import { STAT_CARD_VARIANTS } from '../../theme/variants'

export interface StatCardProps {
  label: string
  value: number | string
  icon: ReactNode
  color: string
  loading?: boolean
  valueColor?: string
  active?: boolean
  onClick?: () => void
}

export default function StatCard({
  label,
  value,
  icon,
  color,
  loading,
  valueColor,
  active = false,
  onClick,
}: StatCardProps) {
  return (
    <Card
      onClick={onClick}
      sx={{
        ...STAT_CARD_VARIANTS.container(color, active),
        flex: '1 1 0',
        minWidth: 140,
        cursor: onClick ? 'pointer' : 'default',
      }}
    >
      <CardContent sx={{ p: 2, '&:last-child': { pb: 2 } }}>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5 }}>
          <Box
            sx={STAT_CARD_VARIANTS.icon(color)}
          >
            {icon}
          </Box>
          <Box sx={{ minWidth: 0 }}>
            {loading ? (
              <Skeleton variant="text" width={28} sx={{ fontSize: '1.5rem', lineHeight: 1.1 }} />
            ) : (
              <Typography variant="h5" fontWeight={700} lineHeight={1.1} sx={{ color: valueColor }}>
                {value}
              </Typography>
            )}
            <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mt: 0.1 }}>
              {label}
            </Typography>
          </Box>
        </Box>
      </CardContent>
    </Card>
  )
}
