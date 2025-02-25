import React from 'react'
import { Card, CardContent, Typography, Box, CircularProgress, useTheme, Grid } from '@mui/material'
import { PieChart, Pie, Cell, Tooltip, Legend, ResponsiveContainer } from 'recharts'
import { DistributionItem } from '../../../services/api/dashboard'
import { getStopTypeText, getStopTypeColorValue, CHART_COLORS } from '../../../theme/constants'

interface DistributionsCardProps {
  stopTypeData?: DistributionItem[]
  messageTypeData?: DistributionItem[]
  loading?: boolean
}

interface TooltipProps {
  active?: boolean
  payload?: Array<{
    payload: {
      label: string | number
      value: number
      percentage: number
      name: string
    }
  }>
  chartType: 'stopType' | 'messageType'
}

const CustomTooltip: React.FC<TooltipProps> = ({ active, payload, chartType }) => {
  const theme = useTheme()

  if (active && payload && payload.length) {
    const item = payload[0].payload
    const labelText = chartType === 'stopType' ? 
      getStopTypeText(Number(item.label)) : 
      item.label

    return (
      <Box
        className="p-3 rounded-lg shadow-lg"
        sx={{ bgcolor: theme.palette.background.paper, border: `1px solid ${theme.palette.divider}` }}
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

export const DistributionsCard: React.FC<DistributionsCardProps> = ({
  stopTypeData = [],
  messageTypeData = [],
  loading = false,
}) => {
  const theme = useTheme()

  const processedStopTypeData = React.useMemo(() => {
    return stopTypeData
      .filter(item => item.percentage > 0)
      .map(item => ({
        ...item,
        name: getStopTypeText(Number(item.label)),
        color: getStopTypeColorValue(Number(item.label)),
      }))
  }, [stopTypeData])

  const processedMessageTypeData = React.useMemo(() => {
    return messageTypeData
      .filter(item => item.percentage > 0)
      .map((item, index) => ({
        ...item,
        name: item.label,
        color: CHART_COLORS[index % CHART_COLORS.length],
      }))
  }, [messageTypeData])

  if (loading) {
    return (
      <Card>
        <CardContent>
          <Box className="flex items-center justify-center h-[300px]">
            <CircularProgress />
          </Box>
        </CardContent>
      </Card>
    )
  }

  if (stopTypeData.length === 0 && messageTypeData.length === 0) {
    return (
      <Card>
        <CardContent>
          <Box className="flex items-center justify-center h-[300px]">
            <Typography variant="body2" color="text.secondary">
              暂无数据
            </Typography>
          </Box>
        </CardContent>
      </Card>
    )
  }

  return (
    <Card>
      <CardContent>
        <Typography variant="h6" gutterBottom>
          分布统计
        </Typography>
        <Grid container spacing={2}>
          <Grid item xs={12} md={6}>
            <Box className="h-[300px] pb-6">
              <Typography variant="subtitle1" align="center" gutterBottom>
                沙盒停止类型分布
              </Typography>
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={processedStopTypeData}
                    cx="50%"
                    cy="50%"
                    innerRadius={60}
                    outerRadius={90}
                    fill="#8884d8"
                    dataKey="value"
                    nameKey="name"
                    paddingAngle={4}
                  >
                    {processedStopTypeData.map((entry) => (
                      <Cell
                        key={`cell-${entry.label}`}
                        fill={entry.color}
                        stroke={theme.palette.background.paper}
                        strokeWidth={2}
                      />
                    ))}
                  </Pie>
                  <Tooltip content={<CustomTooltip chartType="stopType" />} />
                  <Legend />
                </PieChart>
              </ResponsiveContainer>
            </Box>
          </Grid>

          <Grid item xs={12} md={6}>
            <Box className="h-[300px] pb-6">
              <Typography variant="subtitle1" align="center" gutterBottom>
                消息类型分布
              </Typography>
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={processedMessageTypeData}
                    cx="50%"
                    cy="50%"
                    innerRadius={60}
                    outerRadius={90}
                    fill="#8884d8"
                    dataKey="value"
                    nameKey="name"
                    paddingAngle={4}
                  >
                    {processedMessageTypeData.map((entry) => (
                      <Cell
                        key={`cell-${entry.label}`}
                        fill={entry.color}
                        stroke={theme.palette.background.paper}
                        strokeWidth={2}
                      />
                    ))}
                  </Pie>
                  <Tooltip content={<CustomTooltip chartType="messageType" />} />
                  <Legend />
                </PieChart>
              </ResponsiveContainer>
            </Box>
          </Grid>
        </Grid>
      </CardContent>
    </Card>
  )
} 