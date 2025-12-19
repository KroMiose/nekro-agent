import React, { useMemo } from 'react'
import {
  Card,
  CardContent,
  Typography,
  Grid,
  CircularProgress,
  Box,
  useTheme,
  useMediaQuery,
} from '@mui/material'
import { PieChart, Pie, ResponsiveContainer, Cell, Legend, Tooltip } from 'recharts'
import { DistributionItem } from '../../../services/api/dashboard'
import { CARD_VARIANTS, BORDER_RADIUS } from '../../../theme/variants'
import { UI_STYLES } from '../../../theme/themeConfig'
import { getMessageTypeColor, getStopTypeColorValue, getStopTypeTranslatedText } from '../../../theme/utils'
import { useTranslation } from 'react-i18next'

interface DistributionsCardProps {
  stopTypeData?: DistributionItem[]
  messageTypeData?: DistributionItem[]
  loading?: boolean
}

interface CustomTooltipProps {
  active?: boolean
  payload?: Array<{
    name: string
    value: number
    payload: {
      name: string
      value: number
      color: string
      dataTotal: number
    }
  }>
}

// 计算数据集的总值
const calculateTotal = (data: DistributionItem[] = []) => {
  return data.reduce((sum, item) => sum + item.value, 0)
}

// 自定义提示框组件
const CustomTooltip: React.FC<CustomTooltipProps> = ({ active, payload }) => {
  const theme = useTheme()
  const { t } = useTranslation('dashboard')

  if (active && payload && payload.length > 0) {
    const data = payload[0]
    const value = data.value

    // 获取对应数据集的总值
    let totalValue = 0
    if (data && data.payload && data.payload.dataTotal) {
      totalValue = data.payload.dataTotal
    }

    // 计算百分比，确保分母不为0
    const percentage = totalValue > 0 ? (value / totalValue) * 100 : 0

    return (
      <Box
        className="p-2 rounded-md"
        sx={{
          bgcolor: theme.palette.background.paper,
          border: `1px solid ${theme.palette.divider}`,
          boxShadow: theme.shadows[2],
          borderRadius: BORDER_RADIUS.SMALL,
        }}
      >
        <Typography variant="body2" color="text.primary" fontWeight="bold">
          {data.name}
        </Typography>
        <Box className="flex justify-between gap-4 mt-1">
          <Typography variant="body2" color="text.secondary">
            {t('tooltip.count')}: {value}
          </Typography>
          <Typography variant="body2" color="text.secondary">
            {t('tooltip.ratio')}: {percentage.toFixed(1)}%
          </Typography>
        </Box>
      </Box>
    )
  }
  return null
}

export const DistributionsCard: React.FC<DistributionsCardProps> = ({
  stopTypeData = [],
  messageTypeData = [],
  loading = false,
}) => {
  const theme = useTheme()
  const isMobile = useMediaQuery(theme.breakpoints.down('sm'))
  const { t } = useTranslation('dashboard')

  // 翻译停止类型名称
  const translateStopType = useMemo(() => {
    return (stopType: number): string => {
      return getStopTypeTranslatedText(stopType, t)
    }
  }, [t])

  // 翻译消息类型名称
  const translateMessageType = useMemo(() => {
    const messageTypeKeyMap: Record<string, string> = {
      群聊消息: 'messageType.group',
      私聊消息: 'messageType.private',
    }
    return (msgType: string): string => {
      const key = messageTypeKeyMap[msgType]
      return key ? t(key, { ns: 'common' }) : t('messageType.unknown', { ns: 'common' })
    }
  }, [t])

  // 计算总计
  const stopTypeTotal = useMemo(() => calculateTotal(stopTypeData), [stopTypeData])
  const messageTypeTotal = useMemo(() => calculateTotal(messageTypeData), [messageTypeData])

  // 格式化停止类型数据
  const formattedStopTypeData = useMemo(() => {
    return stopTypeData.map((item: DistributionItem) => ({
      name: translateStopType(Number(item.label)),
      value: item.value,
      color: getStopTypeColorValue(Number(item.label)),
      dataTotal: stopTypeTotal,
    }))
  }, [stopTypeData, stopTypeTotal, translateStopType])

  // 格式化消息类型数据 - 使用消息类型颜色常量
  const formattedMessageTypeData = useMemo(() => {
    return messageTypeData.map((item: DistributionItem) => {
      const color = getMessageTypeColor(item.label)
      return {
        name: translateMessageType(item.label),
        value: item.value,
        color: color,
        dataTotal: messageTypeTotal,
      }
    })
  }, [messageTypeData, messageTypeTotal, translateMessageType])

  return (
    <Card className="w-full h-full" sx={CARD_VARIANTS.default.styles}>
      <CardContent>
        <Typography variant="h6" gutterBottom color="text.primary">
          {t('charts.distributionStats')}
        </Typography>

        {loading ? (
          <Box
            className="flex justify-center items-center"
            sx={{ height: UI_STYLES.CARD_LAYOUT.LOADING_HEIGHT }}
          >
            <CircularProgress />
          </Box>
        ) : formattedStopTypeData.length === 0 && formattedMessageTypeData.length === 0 ? (
          <Box
            className="flex justify-center items-center"
            sx={{ height: UI_STYLES.CARD_LAYOUT.LOADING_HEIGHT }}
          >
            <Typography variant="body2" color="text.secondary">
              {t('charts.noData')}
            </Typography>
          </Box>
        ) : (
          <Grid container spacing={2}>
            {formattedStopTypeData.length > 0 && (
              <Grid item xs={12} md={formattedMessageTypeData.length > 0 ? 6 : 12}>
                <Typography
                  variant="subtitle2"
                  textAlign="center"
                  marginBottom={1}
                  color="text.secondary"
                >
                  {t('charts.stopTypeDistribution')}
                </Typography>
                <Box
                  height={
                    isMobile
                      ? UI_STYLES.CARD_LAYOUT.CHART_HEIGHT.MOBILE
                      : UI_STYLES.CARD_LAYOUT.CHART_HEIGHT.DESKTOP
                  }
                >
                  <ResponsiveContainer width="100%" height="100%">
                    <PieChart>
                      <Pie
                        data={formattedStopTypeData}
                        cx="50%"
                        cy="50%"
                        outerRadius={isMobile ? 60 : 80}
                        innerRadius={isMobile ? 40 : 50}
                        paddingAngle={3}
                        dataKey="value"
                        labelLine={false}
                        isAnimationActive={false}
                      >
                        {formattedStopTypeData.map((entry, index) => (
                          <Cell key={`cell-${index}`} fill={entry.color} />
                        ))}
                      </Pie>
                      <Tooltip content={<CustomTooltip />} />
                      <Legend
                        iconType="circle"
                        iconSize={8}
                        layout="vertical"
                        verticalAlign="middle"
                        align="right"
                        wrapperStyle={{ fontSize: isMobile ? 10 : 12 }}
                        formatter={value => {
                          return <span style={{ color: theme.palette.text.primary }}>{value}</span>
                        }}
                      />
                    </PieChart>
                  </ResponsiveContainer>
                </Box>
              </Grid>
            )}
            {formattedMessageTypeData.length > 0 && (
              <Grid item xs={12} md={formattedStopTypeData.length > 0 ? 6 : 12}>
                <Typography
                  variant="subtitle2"
                  textAlign="center"
                  marginBottom={1}
                  color="text.secondary"
                >
                  {t('charts.messageTypeDistribution')}
                </Typography>
                <Box
                  height={
                    isMobile
                      ? UI_STYLES.CARD_LAYOUT.CHART_HEIGHT.MOBILE
                      : UI_STYLES.CARD_LAYOUT.CHART_HEIGHT.DESKTOP
                  }
                >
                  <ResponsiveContainer width="100%" height="100%">
                    <PieChart>
                      <Pie
                        data={formattedMessageTypeData}
                        cx="50%"
                        cy="50%"
                        outerRadius={isMobile ? 60 : 80}
                        innerRadius={isMobile ? 40 : 50}
                        paddingAngle={3}
                        dataKey="value"
                        labelLine={false}
                        isAnimationActive={false}
                      >
                        {formattedMessageTypeData.map((entry, index) => (
                          <Cell key={`cell-${index}`} fill={entry.color} />
                        ))}
                      </Pie>
                      <Tooltip content={<CustomTooltip />} />
                      <Legend
                        iconType="circle"
                        iconSize={8}
                        layout="vertical"
                        verticalAlign="middle"
                        align="right"
                        wrapperStyle={{ fontSize: isMobile ? 10 : 12 }}
                        formatter={value => {
                          return <span style={{ color: theme.palette.text.primary }}>{value}</span>
                        }}
                      />
                    </PieChart>
                  </ResponsiveContainer>
                </Box>
              </Grid>
            )}
          </Grid>
        )}
      </CardContent>
    </Card>
  )
}
