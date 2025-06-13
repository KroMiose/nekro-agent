import React, { useMemo } from 'react'
import {
  Card,
  CardContent,
  Box,
  Typography,
  useTheme,
  useMediaQuery,
  Theme,
  FormControl,
  InputLabel,
  Select,
  SelectChangeEvent,
  alpha,
  MenuItem,
} from '@mui/material'
import {
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
  Area,
  ComposedChart,
} from 'recharts'
import { formatTimestampToTime } from '../../../utils/time'
import { RealTimeDataPoint } from '../../../services/api/dashboard'
import {
  UI_STYLES,
  BORDER_RADIUS,
  metricColors
} from '../../../theme/themeConfig'
import { CARD_VARIANTS } from '../../../theme/variants'

interface RealTimeStatsProps {
  title: string
  data: RealTimeDataPoint[]
  granularity: number
  onGranularityChange: (granularity: number) => void
}

interface CustomTooltipProps {
  active?: boolean
  payload?: Array<{
    name: string
    value: number
    color: string
    dataKey: string
  }>
  label?: string | number
  theme: Theme
}

const CustomTooltip: React.FC<CustomTooltipProps> = ({ active, payload, label, theme }) => {
  if (active && payload && payload.length) {
    return (
      <Box
        className="p-3 rounded-md shadow-lg"
        sx={{
          bgcolor: theme.palette.background.paper,
          border: UI_STYLES.BORDERS.CARD.DEFAULT,
          borderRadius: BORDER_RADIUS.SMALL,
          boxShadow: UI_STYLES.SHADOWS.CARD.DEFAULT,
          transition: 'all 0.2s ease',
          animation: 'fadeIn 0.3s ease-in-out',
          '@keyframes fadeIn': {
            '0%': { opacity: 0, transform: 'translateY(10px)' },
            '100%': { opacity: 1, transform: 'translateY(0)' },
          },
        }}
      >
        <Typography variant="subtitle2" className="mb-1" color="text.primary">
          {label && formatTimestampToTime(label.toString())}
        </Typography>
        {payload.map((entry, index) => (
          <Box key={`item-${index}`} className="flex items-center gap-2 my-1">
            <Box
              component="span"
              className="w-3 h-3 rounded-full"
              sx={{ backgroundColor: entry.color }}
            />
            <Typography variant="body2" color="text.primary" className="font-medium">
              {entry.name}: {entry.dataKey === 'success_rate' ? `${entry.value}%` : entry.value}
            </Typography>
          </Box>
        ))}
      </Box>
    )
  }
  return null
}

// 定义粒度选项
const granularityOptions = [
  { value: 1, label: '1分钟' },
  { value: 5, label: '5分钟' },
  { value: 10, label: '10分钟' },
  { value: 30, label: '30分钟' },
  { value: 60, label: '1小时' },
]

// 指标配置 - 直接使用动态颜色系统
const getMetrics = () => [
  {
    id: 'messages',
    name: '消息数',
    color: metricColors.messages,
  },
  {
    id: 'sandbox_calls',
    name: '沙盒调用',
    color: metricColors.sandbox_calls,
  },
  {
    id: 'success_calls',
    name: '成功调用',
    color: metricColors.success_calls,
  },
  {
    id: 'failed_calls',
    name: '失败调用',
    color: metricColors.failed_calls,
  },
]

// 移动端和桌面端的图表高度
const CHART_HEIGHT = {
  MOBILE: 250,
  DESKTOP: 350,
}

// 定义滚动条样式
const scrollbar = {
  WIDTH: '6px',
  HEIGHT: '6px',
  TRACK: (theme: Theme) => alpha(theme.palette.divider, 0.1),
  THUMB: (theme: Theme) => alpha(theme.palette.primary.main, 0.2),
  THUMB_HOVER: (theme: Theme) => alpha(theme.palette.primary.main, 0.3)
}

export const RealTimeStats: React.FC<RealTimeStatsProps> = ({
  title,
  data,
  granularity,
  onGranularityChange,
}) => {
  const theme = useTheme()
  const isMobile = useMediaQuery(theme.breakpoints.down('sm'))
  
  // 获取当前主题下的指标配置
  const metricsConfig = useMemo(() => getMetrics(), [])

  // 处理粒度变更
  const handleGranularityChange = (value: number) => {
    onGranularityChange(value)
  }

  // 格式化数据以方便显示
  const formattedData = useMemo(() => {
    return data.map(point => {
      // 计算合理的失败调用数（确保数据合理性）
      const success = point.recent_success_calls || 0
      const total = point.recent_sandbox_calls || 0
      const failed = Math.max(0, total - success)

      return {
        timestamp: point.timestamp,
        messages: point.recent_messages || 0,
        sandbox_calls: total,
        success_calls: success,
        failed_calls: failed,
      }
    })
  }, [data])

  return (
    <Card
      className="w-full h-full"
      sx={CARD_VARIANTS.default.styles}
    >
      <CardContent className="h-full">
        <Box
          className={`flex ${isMobile ? 'flex-col' : 'justify-between'} items-${
            isMobile ? 'start' : 'center'
          } mb-${isMobile ? '4' : '2'}`}
        >
          <Typography variant="h6" className={isMobile ? 'mb-2' : ''} color="text.primary">
            {title}
          </Typography>
          <FormControl
            size="small"
            sx={{
              minWidth: isMobile ? '100%' : 120,
              '& .MuiOutlinedInput-root': {
                '& fieldset': {
                  borderColor:
                    theme.palette.mode === 'dark'
                      ? alpha(theme.palette.primary.main, 0.3)
                      : alpha(theme.palette.primary.main, 0.2),
                },
                '&:hover fieldset': {
                  borderColor: theme.palette.primary.main,
                },
                '&.Mui-focused fieldset': {
                  borderColor: theme.palette.primary.main,
                  borderWidth: '1px',
                },
              },
            }}
          >
            <InputLabel id="granularity-select-label">数据粒度</InputLabel>
            <Select
              labelId="granularity-select-label"
              id="granularity-select"
              value={granularity}
              label="数据粒度"
              onChange={(event: SelectChangeEvent<number>) => handleGranularityChange(Number(event.target.value))}
              sx={{
                bgcolor: theme.palette.background.paper,
                '&:hover': {
                  bgcolor: alpha(theme.palette.background.paper, 0.9),
                },
                '& .MuiOutlinedInput-notchedOutline': {
                  borderColor: alpha(theme.palette.primary.main, 0.2),
                },
              }}
            >
              {granularityOptions.map(option => (
                <MenuItem key={option.value} value={option.value}>
                  {option.label}
                </MenuItem>
              ))}
            </Select>
          </FormControl>
        </Box>

        {data.length > 0 ? (
          <Box 
            className="h-full" 
            sx={{ 
              overflow: 'auto',
              '&::-webkit-scrollbar': {
                width: scrollbar.WIDTH,
                height: scrollbar.HEIGHT,
              },
              '&::-webkit-scrollbar-track': {
                background: scrollbar.TRACK(theme),
                borderRadius: BORDER_RADIUS.SMALL,
              },
              '&::-webkit-scrollbar-thumb': {
                background: scrollbar.THUMB(theme),
                borderRadius: BORDER_RADIUS.SMALL,
                '&:hover': {
                  background: scrollbar.THUMB_HOVER(theme),
                },
              },
              mt: 2,
            }}
          >
            <Box sx={{ height: isMobile ? CHART_HEIGHT.MOBILE : CHART_HEIGHT.DESKTOP, minWidth: isMobile ? 500 : 'auto', pt: 1 }}>
              <ResponsiveContainer width="100%" height="100%">
                <ComposedChart
                  data={formattedData}
                  margin={{
                    top: 5,
                    right: isMobile ? 10 : 40,
                    left: isMobile ? 0 : 20,
                    bottom: isMobile ? 5 : 20,
                  }}
                >
                  <CartesianGrid 
                    strokeDasharray="3 3" 
                    stroke={alpha(theme.palette.divider, 0.7)} 
                    vertical={false}
                  />
                  <defs>
                    {metricsConfig.map((metric) => (
                      <linearGradient key={`gradient-${metric.id}`} id={`color${metric.id}`} x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor={metric.color} stopOpacity={0.3}/>
                        <stop offset="95%" stopColor={metric.color} stopOpacity={0}/>
                      </linearGradient>
                    ))}
                  </defs>
                  <XAxis
                    dataKey="timestamp"
                    tickFormatter={formatTimestampToTime}
                    tick={{ fontSize: isMobile ? 10 : 12, fill: theme.palette.text.secondary }}
                    stroke={theme.palette.text.secondary}
                    minTickGap={isMobile ? 30 : 60}
                    interval="preserveEnd"
                    tickCount={isMobile ? 4 : 6}
                  />
                  <YAxis 
                    tick={{ fontSize: isMobile ? 10 : 12, fill: theme.palette.text.secondary }}
                    stroke={theme.palette.text.secondary}
                    width={isMobile ? 30 : 40}
                  />
                  <Tooltip 
                    content={<CustomTooltip theme={theme as Theme} />} 
                    animationDuration={300}
                    animationEasing="ease-in-out"
                    cursor={{
                      stroke: alpha(theme.palette.divider, 0.8),
                      strokeDasharray: '5 5',
                      strokeWidth: 1,
                    }}
                  />
                  <Legend 
                    wrapperStyle={{ paddingTop: isMobile ? 5 : 10 }} 
                    iconSize={isMobile ? 8 : 10} 
                    iconType="circle"
                    formatter={(value) => (
                      <span style={{ color: theme.palette.text.primary, fontSize: isMobile ? '0.75rem' : '0.875rem' }}>
                        {value}
                      </span>
                    )}
                  />
                  {metricsConfig.map(metric => (
                    <Area
                      key={metric.id}
                      type="monotone"
                      dataKey={metric.id}
                      name={metric.name}
                      stroke={metric.color}
                      strokeWidth={isMobile ? 1.5 : 2.5}
                      activeDot={{ 
                        r: isMobile ? 4 : 6, 
                        strokeWidth: 0, 
                        fill: metric.color
                      }}
                      dot={false}
                      isAnimationActive={true}
                      animationDuration={800}
                      animationEasing="ease-out"
                      connectNulls={true}
                      fill={`url(#color${metric.id})`}
                      fillOpacity={1}
                    />
                  ))}
                </ComposedChart>
              </ResponsiveContainer>
            </Box>
          </Box>
        ) : (
          <Box className="flex justify-center items-center h-[350px]">
            <Typography variant="body2" color="text.secondary" className="text-center px-4">
              暂无实时数据，请等待数据收集
            </Typography>
          </Box>
        )}
      </CardContent>
    </Card>
  )
}
