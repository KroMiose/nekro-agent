import React from 'react'
import {
  Card,
  CardContent,
  Typography,
  List,
  ListItem,
  ListItemAvatar,
  ListItemText,
  Avatar,
  Box,
  CircularProgress,
  useTheme,
  alpha,
  useMediaQuery,
} from '@mui/material'
import { RankingItem } from '../../../services/api/dashboard'
import { 
  GRADIENTS, 
  SHADOWS, 
  BORDERS, 
  BORDER_RADIUS, 
  SCROLLBARS,
  CARD_LAYOUT
} from '../../../theme/constants'

interface RankingListProps {
  title: string
  data?: RankingItem[]
  loading?: boolean
  type: 'users' | 'messages'
}

export const RankingList: React.FC<RankingListProps> = ({
  title,
  data = [],
  loading = false,
  type,
}) => {
  const theme = useTheme()
  const isDark = theme.palette.mode === 'dark'
  const isMobile = useMediaQuery(theme.breakpoints.down('sm'))

  // 生成头像背景颜色
  const getAvatarBg = (index: number) => {
    const colors = [
      theme.palette.primary.main,
      theme.palette.secondary.main,
      theme.palette.error.main,
      theme.palette.warning.main,
      theme.palette.info.main,
      theme.palette.success.main,
    ]
    return colors[index % colors.length]
  }

  // 获取排名标记
  const getRankBadge = (index: number) => {
    if (index === 0) return '🥇'
    if (index === 1) return '🥈'
    if (index === 2) return '🥉'
    return `${index + 1}`
  }

  // 获取当前主题的滚动条样式
  const scrollbar = isDark ? SCROLLBARS.DEFAULT.DARK : SCROLLBARS.DEFAULT.LIGHT

  return (
    <Card 
      className="w-full h-full"
      sx={{
        transition: CARD_LAYOUT.TRANSITION,
        '&:hover': {
          boxShadow: isDark ? SHADOWS.CARD.DARK.HOVER : SHADOWS.CARD.LIGHT.HOVER,
        },
        background: isDark ? GRADIENTS.CARD.DARK : GRADIENTS.CARD.LIGHT,
        backdropFilter: CARD_LAYOUT.BACKDROP_FILTER,
        border: isDark ? BORDERS.CARD.DARK : BORDERS.CARD.LIGHT,
        borderRadius: BORDER_RADIUS.DEFAULT,
      }}
    >
      <CardContent>
        <Typography variant="h6" gutterBottom color="text.primary">
          {title}
        </Typography>

        {loading ? (
          <Box className="flex justify-center items-center" sx={{ height: CARD_LAYOUT.LOADING_HEIGHT }}>
            <CircularProgress />
          </Box>
        ) : data.length === 0 ? (
          <Box className="flex justify-center items-center" sx={{ height: CARD_LAYOUT.LOADING_HEIGHT }}>
            <Typography variant="body2" color="text.secondary">
              暂无数据
            </Typography>
          </Box>
        ) : (
          <Box 
            sx={{ 
              height: isMobile ? CARD_LAYOUT.CHART_HEIGHT.MOBILE : CARD_LAYOUT.CHART_HEIGHT.DESKTOP,
              overflow: 'auto',
              '&::-webkit-scrollbar': {
                width: scrollbar.WIDTH,
              },
              '&::-webkit-scrollbar-track': {
                background: scrollbar.TRACK,
                borderRadius: BORDER_RADIUS.SMALL,
              },
              '&::-webkit-scrollbar-thumb': {
                background: scrollbar.THUMB,
                borderRadius: BORDER_RADIUS.SMALL,
                '&:hover': {
                  background: scrollbar.THUMB_HOVER,
                },
              },
              pr: 1,
            }}
          >
            <List disablePadding>
              {data.map((item, index) => (
                <ListItem
                  key={item.id}
                  sx={{
                    py: 1.5,
                    borderRadius: 1,
                    mb: 1,
                    bgcolor:
                      index < 3 ? alpha(getAvatarBg(index), isDark ? 0.15 : 0.1) : 'transparent',
                    transition: 'all 0.2s ease',
                    '&:hover': {
                      bgcolor: isDark
                        ? alpha(theme.palette.primary.main, 0.1)
                        : alpha(theme.palette.primary.main, 0.05),
                      transform: 'translateX(4px)',
                    },
                  }}
                >
                  <Box
                    className="flex items-center justify-center w-8 h-8 rounded-full mr-3"
                    sx={{
                      bgcolor:
                        index < 3
                          ? getAvatarBg(index)
                          : isDark
                            ? 'rgba(255,255,255,0.1)'
                            : 'rgba(0,0,0,0.1)',
                      color: index < 3 ? '#fff' : theme.palette.text.primary,
                      fontWeight: 'bold',
                      fontSize: index < 3 ? '1.2rem' : '0.9rem',
                    }}
                  >
                    {getRankBadge(index)}
                  </Box>
                  <ListItemAvatar>
                    <Avatar
                      src={item.avatar}
                      alt={item.name}
                      sx={{
                        bgcolor: item.avatar ? 'transparent' : getAvatarBg(index),
                        border: `1px solid ${alpha(theme.palette.divider, 0.1)}`,
                      }}
                    >
                      {!item.avatar && item.name.charAt(0).toUpperCase()}
                    </Avatar>
                  </ListItemAvatar>
                  <ListItemText
                    primary={
                      <Typography variant="body1" color="text.primary" fontWeight="medium">
                        {item.name}
                      </Typography>
                    }
                    secondary={
                      <Typography variant="body2" color="text.secondary">
                        {type === 'users' ? `消息数: ${item.value}` : `${item.value} 条`}
                      </Typography>
                    }
                  />
                  <Box
                    className="ml-auto"
                    sx={{
                      fontWeight: 'bold',
                      color:
                        theme.palette.mode === 'dark'
                          ? theme.palette.primary.light
                          : theme.palette.primary.main,
                    }}
                  >
                    {item.value}
                  </Box>
                </ListItem>
              ))}
            </List>
          </Box>
        )}
      </CardContent>
    </Card>
  )
}
