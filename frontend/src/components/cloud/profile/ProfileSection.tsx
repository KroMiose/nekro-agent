import type { ReactNode } from 'react'
import { Box, Chip, Divider, Typography } from '@mui/material'
import { CARD_VARIANTS } from '../../../theme/variants'

interface ProfileSectionProps {
  title: string
  count?: number
  description?: string
  action?: ReactNode
  children: ReactNode
}

export default function ProfileSection({
  title,
  count,
  description,
  action,
  children,
}: ProfileSectionProps) {
  return (
    <Box
      sx={{
        ...CARD_VARIANTS.default.styles,
        p: { xs: 2, md: 2.5 },
      }}
    >
      <Box
        sx={{
          display: 'flex',
          alignItems: { xs: 'flex-start', sm: 'center' },
          justifyContent: 'space-between',
          gap: 2,
          flexWrap: 'wrap',
          mb: 2,
        }}
      >
        <Box sx={{ minWidth: 0, display: 'flex', alignItems: 'center', gap: 1.5 }}>
          <Typography variant="h6" sx={{ fontWeight: 700 }}>
            {title}
          </Typography>
          {typeof count === 'number' && (
            <Chip
              label={count}
              size="small"
              sx={{
                height: 22,
                fontSize: '0.75rem',
                fontWeight: 600,
                bgcolor: 'action.selected',
                color: 'text.secondary',
              }}
            />
          )}
          {description ? (
            <Typography variant="body2" color="text.secondary">
              {description}
            </Typography>
          ) : null}
        </Box>
        {action}
      </Box>
      <Divider sx={{ mb: 2.5 }} />
      {children}
    </Box>
  )
}
