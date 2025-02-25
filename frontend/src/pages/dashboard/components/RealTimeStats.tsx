import React, { useMemo } from 'react'
import { Card, CardContent, Typography, useTheme, Box, alpha, Select, MenuItem, FormControl, InputLabel, SelectChangeEvent } from '@mui/material'
import {
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  CartesianGrid,
  ReferenceLine,
  Legend,
  Area,
  ComposedChart
} from 'recharts'
import { RealTimeDataPoint } from '../../../services/api/dashboard'

interface RealTimeStatsProps {
  title: string
  data: RealTimeDataPoint[]
  granularity: number
  onGranularityChange: (granularity: number) => void
}

// 自定义提示框组件
interface CustomTooltipProps {
  active?: boolean
  payload?: Array<{
    value: number
    name: string
    color: string
  }>
  label?: string
}

const CustomTooltip: React.FC<CustomTooltipProps> = ({ active, payload, label }) => {
  const theme = useTheme()

  if (active && payload && payload.length) {
    return (
      <Box
        className="p-2 rounded-md shadow-lg"
        sx={{
          bgcolor: theme.palette.background.paper,
          border: `1px solid ${theme.palette.divider}`,
          transition: 'all 0.2s ease',
          animation: 'fadeIn 0.3s ease-in-out',
          '@keyframes fadeIn': {
            '0%': { opacity: 0, transform: 'translateY(5px)' },
            '100%': { opacity: 1, transform: 'translateY(0)' },
          },
        }}
      >
        <Typography variant="body2" color="text.primary" fontWeight="medium">
          {new Date(label || '').toLocaleTimeString()}
        </Typography>
        {payload.map((entry, index) => (
          <Box key={`tooltip-item-${index}`} className="flex items-center gap-2 mt-1">
            <Box
              component="span"
              className="w-2 h-2 rounded-full"
              sx={{ backgroundColor: entry.color }}
            />
            <Typography variant="body2" color="text.primary">
              {entry.name}: {entry.value}
            </Typography>
          </Box>
        ))}
      </Box>
    )
  }
  return null
}

export const RealTimeStats: React.FC<RealTimeStatsProps> = ({ 
  title, 
  data, 
  granularity, 
  onGranularityChange 
}) => {
  const theme = useTheme()

  // 粒度选项
  const granularityOptions = [
    { value: 1, label: '1分钟' },
    { value: 5, label: '5分钟' },
    { value: 10, label: '10分钟' },
    { value: 30, label: '30分钟' },
    { value: 60, label: '60分钟' },
  ]

  // 处理粒度变更
  const handleGranularityChange = (event: SelectChangeEvent<number>) => {
    onGranularityChange(Number(event.target.value))
  }

  // 格式化时间标签
  const formatTime = (time: string) => {
    try {
      const date = new Date(time)
      return `${date.getHours()}:${date.getMinutes().toString().padStart(2, '0')}`
    } catch {
      return time
    }
  }

  // 将数据按粒度聚合
  const aggregatedData = useMemo(() => {
    if (!data || data.length === 0) return []

    const minuteMap = new Map<string, RealTimeDataPoint>()

    data.forEach(point => {
      try {
        const date = new Date(point.timestamp)
        // 将秒和毫秒设置为0
        date.setSeconds(0, 0)
        const minuteKey = date.toISOString()

        if (minuteMap.has(minuteKey)) {
          const existing = minuteMap.get(minuteKey)!
          minuteMap.set(minuteKey, {
            timestamp: minuteKey,
            recent_messages: Math.max(existing.recent_messages, point.recent_messages),
            recent_sandbox_calls: Math.max(
              existing.recent_sandbox_calls,
              point.recent_sandbox_calls
            ),
            recent_success_calls: Math.max(
              existing.recent_success_calls,
              point.recent_success_calls
            ),
            recent_avg_exec_time: point.recent_avg_exec_time, // 使用最新的平均执行时间
          })
        } else {
          minuteMap.set(minuteKey, {
            timestamp: minuteKey,
            recent_messages: point.recent_messages,
            recent_sandbox_calls: point.recent_sandbox_calls,
            recent_success_calls: point.recent_success_calls,
            recent_avg_exec_time: point.recent_avg_exec_time,
          })
        }
      } catch {
        // 忽略无效的时间戳
      }
    })

    // 转换为数组并按时间排序
    const sortedData = Array.from(minuteMap.values()).sort(
      (a, b) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime()
    )

    // 如果数据点太少，添加一些空数据点以确保图表显示效果
    if (sortedData.length < 2) {
      const now = new Date()
      now.setSeconds(0, 0)
      
      // 添加当前时间点
      if (sortedData.length === 0) {
        sortedData.push({
          timestamp: now.toISOString(),
          recent_messages: 0,
          recent_sandbox_calls: 0,
          recent_success_calls: 0,
          recent_avg_exec_time: 0
        })
      }
      
      // 添加前一个时间点
      const prevTime = new Date(now.getTime() - granularity * 60000) // 一个粒度前
      sortedData.unshift({
        timestamp: prevTime.toISOString(),
        recent_messages: 0,
        recent_sandbox_calls: 0,
        recent_success_calls: 0,
        recent_avg_exec_time: 0
      })
    }

    return sortedData
  }, [data, granularity])

  // 确保"现在"的时间线始终在图表最右侧
  const currentTimePoint = useMemo(() => {
    if (!aggregatedData || aggregatedData.length === 0) return null

    // 使用最新的数据点作为"现在"的时间点
    return aggregatedData[aggregatedData.length - 1].timestamp
  }, [aggregatedData])

  return (
    <Card
      className="w-full h-full"
      sx={{
        transition: 'all 0.3s ease',
        '&:hover': {
          boxShadow: theme.shadows[4],
        },
      }}
    >
      <CardContent className="h-full">
        <Box className="flex justify-between items-center mb-2">
          <Typography variant="h6">
            {title}
          </Typography>
          <FormControl size="small" sx={{ minWidth: 120 }}>
            <InputLabel id="granularity-select-label">数据粒度</InputLabel>
            <Select
              labelId="granularity-select-label"
              id="granularity-select"
              value={granularity}
              label="数据粒度"
              onChange={handleGranularityChange}
            >
              {granularityOptions.map(option => (
                <MenuItem key={option.value} value={option.value}>
                  {option.label}
                </MenuItem>
              ))}
            </Select>
          </FormControl>
        </Box>

        <Box className="h-[300px]">
          <ResponsiveContainer width="100%" height="100%">
            <ComposedChart data={aggregatedData} margin={{ top: 10, right: 30, left: 10, bottom: 10 }}>
              <CartesianGrid strokeDasharray="3 3" stroke={alpha(theme.palette.divider, 0.5)} />
              <XAxis
                dataKey="timestamp"
                tickFormatter={formatTime}
                minTickGap={30}
                stroke={theme.palette.text.secondary}
                tick={{ fontSize: 12 }}
                padding={{ left: 10, right: 10 }}
              />
              <YAxis 
                stroke={theme.palette.text.secondary} 
                tick={{ fontSize: 12 }}
                width={40}
                tickCount={5}
                domain={[0, 'auto']}
              />
              <Tooltip
                content={<CustomTooltip />}
                animationDuration={100}
                animationEasing="ease-in-out"
                cursor={{ stroke: alpha(theme.palette.primary.main, 0.5), strokeWidth: 1 }}
              />
              <Legend 
                wrapperStyle={{ paddingTop: 10 }} 
                iconSize={10} 
                iconType="circle"
                align="center"
              />
              <defs>
                <linearGradient id="colorMessages" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#8884d8" stopOpacity={0.3}/>
                  <stop offset="95%" stopColor="#8884d8" stopOpacity={0}/>
                </linearGradient>
                <linearGradient id="colorSandbox" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#82ca9d" stopOpacity={0.3}/>
                  <stop offset="95%" stopColor="#82ca9d" stopOpacity={0}/>
                </linearGradient>
              </defs>
              <Area
                type="monotone"
                dataKey="recent_messages"
                name="消息数"
                stroke="#8884d8"
                strokeWidth={2.5}
                fillOpacity={1}
                fill="url(#colorMessages)"
                activeDot={{ r: 6, strokeWidth: 0 }}
                animationDuration={300}
                animationEasing="ease-out"
                isAnimationActive={true}
                dot={false}
              />
              <Area
                type="monotone"
                dataKey="recent_sandbox_calls"
                name="沙盒调用"
                stroke="#82ca9d"
                strokeWidth={2.5}
                fillOpacity={1}
                fill="url(#colorSandbox)"
                activeDot={{ r: 6, strokeWidth: 0 }}
                animationDuration={300}
                animationEasing="ease-out"
                isAnimationActive={true}
                dot={false}
              />
              {/* 当前时间参考线 */}
              {currentTimePoint && (
                <ReferenceLine
                  x={currentTimePoint}
                  stroke="#ff5722"
                  strokeWidth={2}
                  strokeDasharray="5 5"
                  label={{
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
      </CardContent>
    </Card>
  )
}
