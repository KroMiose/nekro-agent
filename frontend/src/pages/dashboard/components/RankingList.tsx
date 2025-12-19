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
import { UI_STYLES, BORDER_RADIUS, getCurrentThemeMode } from '../../../theme/themeConfig'
import { CARD_VARIANTS } from '../../../theme/variants'
import { useTranslation } from 'react-i18next'

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
  const themeMode = getCurrentThemeMode()
  const isMobile = useMediaQuery(theme.breakpoints.down('sm'))
  const { t } = useTranslation('dashboard')

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

  // 排名样式定义
  const rankingStyles = {
    AVATAR_OPACITY: {
      light: 0.1,
      dark: 0.2,
    },
    HOVER_BG: {
      light: (color: string) => alpha(color, 0.05),
      dark: (color: string) => alpha(color, 0.12),
    },
    NORMAL_BG: {
      light: alpha(theme.palette.grey[500], 0.1),
      dark: alpha(theme.palette.grey[700], 0.2),
    },
    TEXT_COLOR: {
      light: theme.palette.primary.main,
      dark: theme.palette.primary.light,
    },
  }

  // 滚动条样式定义
  const scrollbar = {
    WIDTH: '6px',
    TRACK: alpha(theme.palette.divider, 0.1),
    THUMB: alpha(theme.palette.primary.main, 0.2),
    THUMB_HOVER: alpha(theme.palette.primary.main, 0.3),
  }

  return (
    <Card className="w-full h-full" sx={CARD_VARIANTS.default.styles}>
      <CardContent>
        <Typography variant="h6" gutterBottom color="text.primary">
          {title}
        </Typography>

        {loading ? (
          <Box
            className="flex justify-center items-center"
            sx={{ height: UI_STYLES.CARD_LAYOUT.LOADING_HEIGHT }}
          >
            <CircularProgress />
          </Box>
        ) : data.length === 0 ? (
          <Box
            className="flex justify-center items-center"
            sx={{ height: UI_STYLES.CARD_LAYOUT.LOADING_HEIGHT }}
          >
            <Typography variant="body2" color="text.secondary">
              {t('charts.noData')}
            </Typography>
          </Box>
        ) : (
          <Box
            sx={{
              height: isMobile
                ? UI_STYLES.CARD_LAYOUT.CHART_HEIGHT.MOBILE
                : UI_STYLES.CARD_LAYOUT.CHART_HEIGHT.DESKTOP,
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
                      index < 3
                        ? alpha(getAvatarBg(index), rankingStyles.AVATAR_OPACITY[themeMode])
                        : 'transparent',
                    transition: 'all 0.2s ease',
                    '&:hover': {
                      bgcolor: rankingStyles.HOVER_BG[themeMode](theme.palette.primary.main),
                      transform: 'translateX(4px)',
                    },
                  }}
                >
                  <Box
                    className="flex items-center justify-center w-8 h-8 rounded-full mr-3"
                    sx={{
                      bgcolor: index < 3 ? getAvatarBg(index) : rankingStyles.NORMAL_BG[themeMode],
                      color: index < 3 ? '#fff' : rankingStyles.TEXT_COLOR[themeMode],
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
                        {type === 'users'
                          ? `${t('ranking.messageCount')}: ${item.value}`
                          : `${item.value} ${t('ranking.messages')}`}
                      </Typography>
                    }
                  />
                  <Box
                    className="ml-auto"
                    sx={{
                      fontWeight: 'bold',
                      color: rankingStyles.TEXT_COLOR[themeMode],
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
