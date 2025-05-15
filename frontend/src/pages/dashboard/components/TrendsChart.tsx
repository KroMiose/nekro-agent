import React from 'react'
import {
  Card,
  CardContent,
  Typography,
  Box,
  CircularProgress,
  useTheme,
  alpha,
  Theme,
  useMediaQuery
} from '@mui/material'
import {
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  ReferenceLine,
  Area,
  ComposedChart
} from 'recharts'
import { format, parseISO, isToday, isThisWeek, isThisMonth } from 'date-fns'
import { TrendDataPoint } from '../../../services/api/dashboard'
import { UI_STYLES, BORDER_RADIUS, metricColors, metricNames } from '../../../theme/themeConfig'

interface TrendsChartProps {
  title: string
  data?: TrendDataPoint[]
  loading?: boolean
  metrics: string[]
  timeRange?: 'day' | 'week' | 'month'
}

// 自定义提示框组件接口
interface CustomTooltipProps {
  active?: boolean
  payload?: Array<{
    value: number
    name: string
    color: string
    dataKey: string
  }>
  label?: string
  theme: Theme
  timeRange?: 'day' | 'week' | 'month'
}

// 自定义提示框组件
const CustomTooltip: React.FC<CustomTooltipProps> = ({ active, payload, label, theme, timeRange = 'day' }) => {
  if (active && payload && payload.length) {
    // 根据时间范围选择合适的日期格式
    let dateFormat = 'HH:mm';
    if (timeRange === 'week') {
      dateFormat = 'MM-dd EEE';
    } else if (timeRange === 'month') {
      dateFormat = 'MM-dd';
    }

    return (
      <Box
        className="p-3 rounded-md shadow-lg"
        sx={{
          bgcolor: theme.palette.background.paper,
          border: `1px solid ${theme.palette.divider}`,
          transition: 'all 0.2s ease',
          animation: 'fadeIn 0.3s ease-in-out',
          '@keyframes fadeIn': {
            '0%': { opacity: 0, transform: 'translateY(10px)' },
            '100%': { opacity: 1, transform: 'translateY(0)' },
          },
        }}
      >
        <Typography variant="subtitle2" className="mb-1" color="text.primary">
          {format(parseISO(label || ''), dateFormat)}
        </Typography>
        {payload.map((entry, index) => (
          <Box key={`item-${index}`} className="flex items-center gap-2 my-1">
            <Box
              component="span"
              className="w-3 h-3 rounded-full"
              sx={{ backgroundColor: entry.color }}
            />
            <Typography variant="body2" color="text.primary">
              {entry.name}: {entry.dataKey === 'success_rate' ? `${entry.value}%` : entry.value}
            </Typography>
          </Box>
        ))}
      </Box>
    )
  }
  return null
}

export const TrendsChart: React.FC<TrendsChartProps> = ({
  title,
  data = [],
  loading = false,
  metrics,
  timeRange = 'day',
}) => {
  const theme = useTheme()
  const isMobile = useMediaQuery(theme.breakpoints.down('sm'))

  // 根据时间范围选择合适的日期格式
  const getDateFormat = () => {
    switch (timeRange) {
      case 'week':
        return 'MM-dd';
      case 'month':
        return 'MM-dd';
      default:
        return 'HH:mm';
    }
  }

  // 格式化时间戳
  const formatTimestamp = (timestamp: string) => {
    try {
      const date = parseISO(timestamp)
      return format(date, getDateFormat())
    } catch {
      return timestamp
    }
  }

  // 格式化工具提示值
  const formatTooltipValue = (value: number, name: string) => {
    if (name === 'success_rate') {
      return `${value}%`
    }
    return value
  }

  // 查找当前时间最接近的数据点
  const findCurrentTimeIndex = () => {
    if (!data || data.length === 0) return null

    const now = new Date()

    // 检查数据是否包含当前时间范围的数据
    const isCurrentTimeRange = data.some(point => {
      try {
        const date = parseISO(point.timestamp as string)
        if (timeRange === 'day') return isToday(date)
        if (timeRange === 'week') return isThisWeek(date)
        if (timeRange === 'month') return isThisMonth(date)
        return false
      } catch {
        return false
      }
    })

    if (!isCurrentTimeRange) return null

    // 找到最接近当前时间的数据点
    let closestIndex = 0
    let minDiff = Infinity

    data.forEach((point, index) => {
      try {
        const pointTime = parseISO(point.timestamp as string)
        const diff = Math.abs(now.getTime() - pointTime.getTime())
        if (diff < minDiff) {
          minDiff = diff
          closestIndex = index
        }
      } catch {
        // 忽略无效的时间戳
      }
    })

    return closestIndex
  }

  // 获取当前时间的参考线位置
  const currentTimeIndex = findCurrentTimeIndex()
  const currentTimePoint = currentTimeIndex !== null ? data[currentTimeIndex]?.timestamp : null

  // 使用metricColors
  const metricColorMap = metricColors;

  return (
    <Card
      className="w-full h-full"
      sx={{
        transition: UI_STYLES.CARD_LAYOUT.TRANSITION,
        '&:hover': {
          boxShadow: UI_STYLES.SHADOWS.CARD.HOVER,
        },
        background: UI_STYLES.GRADIENTS.CARD.DEFAULT,
        backdropFilter: UI_STYLES.CARD_LAYOUT.BACKDROP_FILTER,
        border: UI_STYLES.BORDERS.CARD.DEFAULT,
        borderRadius: BORDER_RADIUS.DEFAULT,
      }}
    >
      <CardContent className="h-full">
        <Typography variant="h6" gutterBottom color="text.primary">
          {title}
        </Typography>

        {loading ? (
          <Box className="flex items-center justify-center h-[300px]">
            <CircularProgress />
          </Box>
        ) : data.length === 0 ? (
          <Box className="flex items-center justify-center h-[300px]">
            <Typography variant="body2" color="text.secondary">
              暂无数据
            </Typography>
          </Box>
        ) : (
          <Box className={isMobile ? "h-[250px]" : "h-[350px]"}>
            <ResponsiveContainer width="100%" height="100%">
              <ComposedChart
                data={data}
                margin={{
                  top: 5,
                  right: isMobile ? 10 : 40,
                  left: isMobile ? 0 : 20,
                  bottom: isMobile ? 5 : 20,
                }}
              >
                <CartesianGrid strokeDasharray="3 3" stroke={alpha(theme.palette.divider, 0.7)} />
                <XAxis
                  dataKey="timestamp"
                  tickFormatter={formatTimestamp}
                  stroke={theme.palette.text.secondary}
                  tick={{ fontSize: isMobile ? 10 : 12 }}
                  minTickGap={60}
                  interval="preserveEnd"
                  tickCount={isMobile ? 4 : 6}
                />
                <YAxis 
                  stroke={theme.palette.text.secondary} 
                  tick={{ fontSize: isMobile ? 10 : 12 }}
                  width={isMobile ? 30 : 40}
                />
                <Tooltip
                  content={<CustomTooltip theme={theme as Theme} timeRange={timeRange} />}
                  formatter={formatTooltipValue}
                  labelFormatter={formatTimestamp}
                  animationDuration={400}
                  animationEasing="ease-in-out"
                />
                <Legend 
                  wrapperStyle={{ paddingTop: isMobile ? 5 : 10 }} 
                  iconSize={isMobile ? 8 : 10} 
                  iconType="circle" 
                />
                
                <defs>
                  {metrics.map(metric => {
                    const color = metricColorMap[metric as keyof typeof metricColors] || '#8884d8';
                    return (
                      <linearGradient key={`gradient-${metric}`} id={`color${metric}`} x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor={color} stopOpacity={0.3}/>
                        <stop offset="95%" stopColor={color} stopOpacity={0}/>
                      </linearGradient>
                    );
                  })}
                </defs>
                
                {metrics.map(metric => {
                  const color = metricColorMap[metric as keyof typeof metricColors] || '#8884d8';
                  return (
                    <Area
                      key={metric}
                      type="monotone"
                      dataKey={metric}
                      name={metricNames[metric as keyof typeof metricNames] || metric}
                      stroke={color}
                      strokeWidth={isMobile ? 1.5 : 2.5}
                      dot={false}
                      activeDot={{ r: isMobile ? 4 : 6, strokeWidth: 0 }}
                      animationDuration={500}
                      animationEasing="ease-out"
                      fill={`url(#color${metric})`}
                      fillOpacity={1}
                    />
                  );
                })}

                {/* 当前时间参考线 */}
                {currentTimePoint && (
                  <ReferenceLine
                    x={currentTimePoint}
                    stroke="#ff5722"
                    strokeWidth={isMobile ? 1 : 2}
                    strokeDasharray="5 5"
                    label={isMobile ? undefined : {
                      value: '现在',
                      position: 'insideTopRight',
                      fill: theme.palette.text.primary,
                      fontSize: 12,
                    }}
                  />
                )}
              </ComposedChart>
            </ResponsiveContainer>
          </Box>
        )}
      </CardContent>
    </Card>
  )
}
