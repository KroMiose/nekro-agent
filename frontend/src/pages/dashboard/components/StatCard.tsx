import React from 'react'
import {
  Card,
  CardContent,
  Typography,
  Box,
  CircularProgress,
  useMediaQuery,
  useTheme,
} from '@mui/material'
import { UI_STYLES, BORDER_RADIUS, getAlphaColor } from '../../../theme/themeApi'
import { LAYOUT } from '../../../theme/variants'

interface StatCardProps {
  title: string
  value: number | string
  icon?: React.ReactNode
  color?: 'primary' | 'secondary' | 'success' | 'error' | 'warning' | 'info' | string
  loading?: boolean
  type?: 'default' | 'success' | 'error' | 'warning' | 'info'
}

export const StatCard: React.FC<StatCardProps> = ({
  title,
  value,
  icon,
  color = 'primary',
  loading = false,
  type = 'default',
}) => {
  const theme = useTheme()
  const isMobile = useMediaQuery(theme.breakpoints.down('sm'))

  // 获取颜色值
  const getCardColor = () => {
    // 使用预定义的颜色
    switch (color) {
      case 'primary':
        return theme.palette.primary.main
      case 'secondary':
        return theme.palette.secondary.main
      case 'success':
        return theme.palette.success.main
      case 'error':
        return theme.palette.error.main
      case 'warning':
        return theme.palette.warning.main
      case 'info':
        return theme.palette.info.main
      default:
        // 如果是自定义颜色代码，直接返回
        return color.startsWith('#') ? color : theme.palette.primary.main
    }
  }

  // 获取实际颜色
  const actualColor = getCardColor()

  // 使用不同类型的渐变背景
  const getCardBackground = () => {
    switch (type) {
      case 'success':
        return UI_STYLES.GRADIENTS.CARD.SUCCESS
      case 'error':
        return UI_STYLES.GRADIENTS.CARD.ERROR
      case 'warning':
        return UI_STYLES.GRADIENTS.CARD.WARNING
      case 'info':
        return UI_STYLES.GRADIENTS.CARD.INFO
      default:
        return UI_STYLES.GRADIENTS.CARD.STATISTIC
    }
  }

  return (
    <Card
      className="w-full"
      sx={{
        borderRadius: BORDER_RADIUS.DEFAULT,
        transition: LAYOUT.TRANSITION.DEFAULT,
        '&:hover': {
          boxShadow: UI_STYLES.SHADOWS.CARD.HOVER,
        },
        background: getCardBackground(),
        backgroundColor:
          theme.palette.mode === 'dark' ? 'rgba(32, 32, 32, 0.9)' : 'rgba(255, 255, 255, 0.9)',
        backdropFilter: 'blur(8px)',
        WebkitBackdropFilter: 'blur(8px)',
        border: UI_STYLES.BORDERS.CARD.DEFAULT,
        position: 'relative',
        overflow: 'hidden',
        '&:after': {
          content: '""',
          position: 'absolute',
          top: 0,
          right: 0,
          width: '25%',
          height: '100%',
          background: `linear-gradient(90deg, transparent, ${getAlphaColor(theme.palette.mode === 'dark' ? '#fff' : theme.palette.primary.light, 0.04)})`,
          filter: 'blur(5px)',
          zIndex: 0,
        },
      }}
    >
      <CardContent
        className={`flex items-center ${isMobile ? 'p-3' : 'p-4'}`}
        sx={{ position: 'relative', zIndex: 1 }}
      >
        {icon && (
          <Box
            className={`flex items-center justify-center rounded-full ${isMobile ? 'p-1.5 mr-2' : 'p-2 mr-3'}`}
            sx={{
              bgcolor: getAlphaColor(actualColor, 0.15),
              color: actualColor,
              boxShadow: `0 2px 8px ${getAlphaColor(actualColor, 0.1)}`,
              transition: 'all 0.3s ease',
              '&:hover': {
                transform: 'scale(1.05) rotate(5deg)',
                boxShadow: `0 3px 10px ${getAlphaColor(actualColor, 0.15)}`,
              },
            }}
          >
            {icon}
          </Box>
        )}
        <Box className="flex-grow">
          <Typography
            variant={isMobile ? 'caption' : 'body2'}
            color="text.secondary"
            gutterBottom
            sx={{
              fontWeight: 500,
              opacity: 0.9,
              textShadow: theme.palette.mode === 'dark' ? '0 1px 2px rgba(0,0,0,0.2)' : 'none',
            }}
          >
            {title}
          </Typography>
          {loading ? (
            <CircularProgress size={isMobile ? 16 : 20} />
          ) : (
            <Typography
              variant={isMobile ? 'h6' : 'h5'}
              component="div"
              fontWeight="bold"
              sx={{
                whiteSpace: 'nowrap',
                overflow: 'hidden',
                textOverflow: 'ellipsis',
                color: theme.palette.text.primary,
                textShadow:
                  theme.palette.mode === 'dark'
                    ? '0 1px 3px rgba(0,0,0,0.3)'
                    : '0 1px 1px rgba(0,0,0,0.05)',
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
