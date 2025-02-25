import React, { useMemo } from 'react'
import { Card, CardContent, Typography, Box, CircularProgress, useTheme } from '@mui/material'
import {
  PieChart,
  Pie,
  Cell,
  Tooltip,
  Legend,
  ResponsiveContainer,
  PieLabelRenderProps,
} from 'recharts'
import { DistributionItem } from '../../../services/api/dashboard'
import { getStopTypeText, getStopTypeColorValue, CHART_COLORS } from '../../../theme/constants'

interface DistributionChartProps {
  title: string
  data?: DistributionItem[]
  loading?: boolean
  colors?: string[]
  type?: 'stopType' | 'messageType' | 'other'
}

// 扩展DistributionItem接口，添加name字段
interface EnhancedDistributionItem extends DistributionItem {
  name?: string
  color?: string
}

interface TooltipProps {
  active?: boolean
  payload?: Array<{
    payload: EnhancedDistributionItem
  }>
}

// 定义常量
const RADIAN = Math.PI / 180

export const DistributionChart: React.FC<DistributionChartProps> = ({
  title,
  data = [],
  loading = false,
  colors = CHART_COLORS,
  type = 'other',
}) => {
  const theme = useTheme()

  // 格式化工具提示
  const CustomTooltip = ({ active, payload }: TooltipProps) => {
    if (active && payload && payload.length) {
      const item = payload[0].payload
      const labelText = type === 'stopType' ? 
        getStopTypeText(Number(item.label)) : 
        item.label

      return (
        <Box
          className="p-3 rounded-lg shadow-lg"
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
          <Typography variant="body2" color="text.primary" fontWeight="medium" className="mb-1">
            {labelText}
          </Typography>
          <Typography variant="body2" fontWeight="bold" color="text.primary">
            数量: {item.value}
          </Typography>
          <Typography variant="body2" fontWeight="bold" color="text.primary">
            占比: {item.percentage}%
          </Typography>
        </Box>
      )
    }
    return null
  }

  // 自定义标签渲染
  const renderCustomizedLabel = (props: PieLabelRenderProps) => {
    const { cx, cy, midAngle, innerRadius, outerRadius, percent } = props
    const radius =
      (innerRadius as number) + ((outerRadius as number) - (innerRadius as number)) * 0.5
    const x = (cx as number) + radius * Math.cos(-midAngle * RADIAN)
    const y = (cy as number) + radius * Math.sin(-midAngle * RADIAN)

    return (
      <text
        x={x}
        y={y}
        fill="white"
        textAnchor={x > (cx as number) ? 'start' : 'end'}
        dominantBaseline="central"
        fontSize={12}
        fontWeight="bold"
      >
        {`${((percent || 0) * 100).toFixed(0)}%`}
      </text>
    )
  }

  // 处理数据，确保有颜色和百分比
  const processedData = useMemo(() => {
    if (!data || data.length === 0) return []

    const result = data.map((item, index) => {
      const enhancedItem = { ...item } as EnhancedDistributionItem
      
      if (type === 'stopType') {
        // 处理沙盒停止类型分布数据
        enhancedItem.name = getStopTypeText(Number(item.label))
        enhancedItem.color = getStopTypeColorValue(Number(item.label))
      } else if (type === 'messageType') {
        // 处理消息类型分布数据
        enhancedItem.name = item.label
        enhancedItem.color = colors[index % colors.length]
      } else {
        // 其他类型数据
        enhancedItem.name = item.label
        enhancedItem.color = colors[index % colors.length]
      }

      return enhancedItem
    })

    return result
  }, [data, colors, type])

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
        <Typography variant="h6" gutterBottom>
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
          <Box className="h-[300px]">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <defs>
                  {processedData.map((entry, index) => {
                    const color = entry.color
                    return (
                      <linearGradient
                        key={`colorGradient-${index}`}
                        id={`colorGradient-${index}`}
                        x1="0"
                        y1="0"
                        x2="0"
                        y2="1"
                      >
                        <stop offset="0%" stopColor={color} stopOpacity={0.8} />
                        <stop offset="100%" stopColor={color} stopOpacity={0.3} />
                      </linearGradient>
                    )
                  })}
                </defs>
                <Pie
                  data={processedData}
                  cx="50%"
                  cy="50%"
                  labelLine={false}
                  innerRadius={60}
                  outerRadius={90}
                  fill="#8884d8"
                  dataKey="value"
                  nameKey="label"
                  label={renderCustomizedLabel}
                  paddingAngle={4}
                  animationBegin={0}
                  animationDuration={500}
                  animationEasing="ease-out"
                >
                  {processedData.map((_entry, index) => (
                    <Cell
                      key={`cell-${index}`}
                      fill={`url(#colorGradient-${index})`}
                      stroke={theme.palette.background.paper}
                      strokeWidth={2}
                    />
                  ))}
                </Pie>
                <Tooltip content={<CustomTooltip />} />
                <Legend
                  layout="horizontal"
                  verticalAlign="bottom"
                  align="center"
                  wrapperStyle={{ paddingTop: 20 }}
                  formatter={(value) => {
                    if (type === 'stopType') {
                      return <span style={{ color: theme.palette.text.primary }}>
                        {getStopTypeText(Number(value))}
                      </span>
                    }
                    return <span style={{ color: theme.palette.text.primary }}>{value}</span>
                  }}
                />
              </PieChart>
            </ResponsiveContainer>
          </Box>
        )}
      </CardContent>
    </Card>
  )
}