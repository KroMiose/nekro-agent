import React from 'react'
import { Card, CardContent, Typography, Box, CircularProgress, useMediaQuery, useTheme } from '@mui/material'
import { 
  GRADIENTS, 
  SHADOWS, 
  BORDERS, 
  BORDER_RADIUS,
  CARD_LAYOUT 
} from '../../../theme/constants'

interface StatCardProps {
  title: string
  value: number | string
  icon?: React.ReactNode
  color?: string
  loading?: boolean
}

export const StatCard: React.FC<StatCardProps> = ({
  title,
  value,
  icon,
  color = 'primary.main',
  loading = false
}) => {
  const theme = useTheme()
  const isMobile = useMediaQuery(theme.breakpoints.down('sm'))
  const isDark = theme.palette.mode === 'dark'

  return (
    <Card 
      className="w-full"
      sx={{
        borderRadius: BORDER_RADIUS.DEFAULT,
        transition: CARD_LAYOUT.TRANSITION,
        '&:hover': {
          boxShadow: isDark 
            ? SHADOWS.CARD.DARK.HOVER
            : SHADOWS.CARD.LIGHT.HOVER,
          transform: 'translateY(-2px)',
        },
        background: isDark 
          ? GRADIENTS.CARD.DARK
          : GRADIENTS.CARD.LIGHT,
        backdropFilter: CARD_LAYOUT.BACKDROP_FILTER,
        border: isDark 
          ? BORDERS.CARD.DARK
          : BORDERS.CARD.LIGHT,
      }}
    >
      <CardContent className={`flex items-center ${isMobile ? 'p-3' : 'p-4'}`}>
        {icon && (
          <Box
            className={`flex items-center justify-center rounded-full ${isMobile ? 'p-1.5 mr-2' : 'p-2 mr-3'}`}
            sx={{ 
              bgcolor: `${color}20`, 
              color,
              transition: 'all 0.3s ease',
              '&:hover': {
                transform: 'scale(1.05)',
              },
            }}
          >
            {icon}
          </Box>
        )}
        <Box className="flex-grow">
          <Typography 
            variant={isMobile ? "caption" : "body2"} 
            color="text.secondary" 
            gutterBottom
          >
            {title}
          </Typography>
          {loading ? (
            <CircularProgress size={isMobile ? 16 : 20} />
          ) : (
            <Typography 
              variant={isMobile ? "h6" : "h5"} 
              component="div" 
              fontWeight="bold"
              sx={{ 
                whiteSpace: 'nowrap', 
                overflow: 'hidden',
                textOverflow: 'ellipsis',
                color: theme.palette.text.primary,
              }}
            >
              {value}
            </Typography>
          )}
        </Box>
      </CardContent>
    </Card>
  )
} 