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
import {
  getStopTypeText,
  stopTypeColorValues,
  LEGACY_COLORS,
  GRADIENTS,
  SHADOWS,
  getMessageTypeColor,
  BORDERS,
  BORDER_RADIUS,
  CARD_LAYOUT,
} from '../../../theme/constants'

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
            数量: {value}
          </Typography>
          <Typography variant="body2" color="text.secondary">
            占比: {percentage.toFixed(1)}%
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
  const isDark = theme.palette.mode === 'dark'
  const isMobile = useMediaQuery(theme.breakpoints.down('sm'))

  // 计算总计
  const stopTypeTotal = useMemo(() => calculateTotal(stopTypeData), [stopTypeData])
  const messageTypeTotal = useMemo(() => calculateTotal(messageTypeData), [messageTypeData])

  // 格式化停止类型数据
  const formattedStopTypeData = useMemo(() => {
    return stopTypeData.map((item: DistributionItem) => ({
      name: getStopTypeText(Number(item.label)),
      value: item.value,
      color:
        stopTypeColorValues[Number(item.label) as keyof typeof stopTypeColorValues] ||
        LEGACY_COLORS.DEFAULT,
      dataTotal: stopTypeTotal, // 添加数据集总值
    }))
  }, [stopTypeData, stopTypeTotal])

  // 格式化消息类型数据 - 使用消息类型颜色常量
  const formattedMessageTypeData = useMemo(() => {
    return messageTypeData.map((item: DistributionItem) => {
      // 使用constants中定义的getMessageTypeColor函数获取颜色
      const color = getMessageTypeColor(item.label)

      return {
        name: item.label,
        value: item.value,
        color: color,
        dataTotal: messageTypeTotal, // 添加数据集总值
      }
    })
  }, [messageTypeData, messageTypeTotal])

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
          分布统计
        </Typography>

        {loading ? (
          <Box className="flex justify-center items-center" sx={{ height: CARD_LAYOUT.LOADING_HEIGHT }}>
            <CircularProgress />
          </Box>
        ) : formattedStopTypeData.length === 0 && formattedMessageTypeData.length === 0 ? (
          <Box className="flex justify-center items-center" sx={{ height: CARD_LAYOUT.LOADING_HEIGHT }}>
            <Typography variant="body2" color="text.secondary">
              暂无数据
            </Typography>
          </Box>
        ) :
          <Grid container spacing={2}>
            {formattedStopTypeData.length > 0 && (
              <Grid item xs={12} md={formattedMessageTypeData.length > 0 ? 6 : 12}>
                <Typography
                  variant="subtitle2"
                  textAlign="center"
                  marginBottom={1}
                  color="text.secondary"
                >
                  执行类型分布
                </Typography>
                <Box height={isMobile ? CARD_LAYOUT.CHART_HEIGHT.MOBILE : CARD_LAYOUT.CHART_HEIGHT.DESKTOP}>
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
                  消息类型分布
                </Typography>
                <Box height={isMobile ? CARD_LAYOUT.CHART_HEIGHT.MOBILE : CARD_LAYOUT.CHART_HEIGHT.DESKTOP}>
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
        }
      </CardContent>
    </Card>
  )
}
