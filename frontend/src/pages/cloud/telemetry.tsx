import { useState, useEffect } from 'react'
import {
  Box,
  Typography,
  Card,
  CardContent,
  Grid,
  CircularProgress,
  Alert,
  useTheme,
} from '@mui/material'
import {
  Code as CodeIcon,
  People as PeopleIcon,
  Storage as StorageIcon,
  CheckCircle as CheckCircleIcon,
} from '@mui/icons-material'
import { telemetryApi } from '../../services/api/cloud/telemetry'
import type { CommunityStats } from '../../services/api/cloud/telemetry'
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip as RechartsTooltip,
  ResponsiveContainer,
} from 'recharts'
import { PieChart, Pie, Cell, Legend, Tooltip } from 'recharts'
import { format } from 'date-fns'
import { zhCN } from 'date-fns/locale'

// 统计卡片组件
const StatCard = ({
  title,
  value,
  icon,
  color,
}: {
  title: string
  value: number | string
  icon: JSX.Element
  color: string
}) => {
  const theme = useTheme()

  return (
    <Card
      sx={{
        flex: 1,
        transition: 'all 0.3s ease',
        '&:hover': {
          boxShadow: theme.shadows[4],
        },
      }}
    >
      <CardContent>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <Box>
            <Typography variant="body2" color="text.secondary">
              {title}
            </Typography>
            <Typography variant="h4" component="div" sx={{ mt: 1, fontWeight: 'medium' }}>
              {value}
            </Typography>
          </Box>
          <Box
            sx={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              bgcolor: `${color}20`,
              color: color,
              borderRadius: '50%',
              width: 48,
              height: 48,
            }}
          >
            {icon}
          </Box>
        </Box>
      </CardContent>
    </Card>
  )
}

// 自定义饼图提示组件
interface PieTooltipProps {
  active?: boolean
  payload?: Array<{
    payload: {
      version: string
      count: number
      total: number
    }
  }>
}

const CustomPieTooltip = ({ active, payload }: PieTooltipProps) => {
  const theme = useTheme()

  if (active && payload && payload.length) {
    const item = payload[0].payload
    return (
      <Box
        sx={{
          bgcolor: theme.palette.background.paper,
          border: `1px solid ${theme.palette.divider}`,
          boxShadow: theme.shadows[3],
          p: 1.5,
          borderRadius: 1,
          minWidth: 120,
          transition: 'all 0.2s ease',
          animation: 'fadeIn 0.3s ease-in-out',
          '@keyframes fadeIn': {
            '0%': { opacity: 0, transform: 'translateY(5px)' },
            '100%': { opacity: 1, transform: 'translateY(0)' },
          },
        }}
      >
        <Typography variant="body2" color="text.primary" fontWeight="medium" sx={{ mb: 0.5 }}>
          {item.version}
        </Typography>
        <Typography variant="body2" fontWeight="bold" color="text.primary">
          数量: {item.count}
        </Typography>
        <Typography variant="body2" fontWeight="bold" color="text.primary">
          占比: {((item.count / item.total) * 100).toFixed(1)}%
        </Typography>
      </Box>
    )
  }
  return null
}

// 自定义折线图提示组件
interface LineTooltipProps {
  active?: boolean
  payload?: Array<{
    value: number
  }>
  label?: string
}

const CustomLineTooltip = ({ active, payload, label }: LineTooltipProps) => {
  const theme = useTheme()

  if (active && payload && payload.length) {
    return (
      <Box
        sx={{
          bgcolor: theme.palette.background.paper,
          border: `1px solid ${theme.palette.divider}`,
          boxShadow: theme.shadows[3],
          p: 1.5,
          borderRadius: 1,
          minWidth: 120,
          transition: 'all 0.2s ease',
          animation: 'fadeIn 0.3s ease-in-out',
          '@keyframes fadeIn': {
            '0%': { opacity: 0, transform: 'translateY(5px)' },
            '100%': { opacity: 1, transform: 'translateY(0)' },
          },
        }}
      >
        <Typography variant="body2" color="text.primary" fontWeight="medium" sx={{ mb: 0.5 }}>
          日期: {label}
        </Typography>
        <Typography variant="body2" fontWeight="bold" color="text.primary">
          新增实例: {payload[0].value}
        </Typography>
      </Box>
    )
  }
  return null
}

interface VersionData {
  version: string
  count: number
  total: number
}

export default function CommunityStats() {
  const [stats, setStats] = useState<CommunityStats | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const theme = useTheme()

  useEffect(() => {
    const fetchStats = async () => {
      try {
        setLoading(true)
        const data = await telemetryApi.getCommunityStats()
        setStats(data)
        setError(null)
      } catch (err) {
        console.error('获取社区统计数据失败', err)
        setError('获取社区统计数据失败')
      } finally {
        setLoading(false)
      }
    }

    fetchStats()
  }, [])

  // 格式化日期
  const formatDate = (dateString: string) => {
    const date = new Date(dateString)
    return format(date, 'MM-dd', { locale: zhCN })
  }

  // 格式化大数字
  const formatNumber = (num: number) => {
    return num.toLocaleString('zh-CN')
  }

  // 社区活跃版本分布的饼图颜色
  const COLORS = ['#0088FE', '#00C49F', '#FFBB28', '#FF8042', '#8884d8']

  const renderLineChart = (data: CommunityStats['newInstancesTrend']) => {
    // 处理日期格式
    const chartData = data.map(item => ({
      date: formatDate(item.date),
      count: item.count,
    }))

    return (
      <ResponsiveContainer width="100%" height={320}>
        <LineChart
          data={chartData}
          margin={{
            top: 20,
            right: 30,
            left: 20,
            bottom: 5,
          }}
        >
          <CartesianGrid strokeDasharray="3 3" stroke={theme.palette.divider} />
          <XAxis
            dataKey="date"
            tick={{ fill: theme.palette.text.secondary }}
            stroke={theme.palette.divider}
          />
          <YAxis
            allowDecimals={false}
            tick={{ fill: theme.palette.text.secondary }}
            stroke={theme.palette.divider}
          />
          <RechartsTooltip
            content={<CustomLineTooltip />}
            wrapperStyle={{ zIndex: 1000, outline: 'none' }}
          />
          <Line
            type="monotone"
            dataKey="count"
            stroke={theme.palette.primary.main}
            activeDot={{ r: 8, fill: theme.palette.primary.main, strokeWidth: 0 }}
            dot={{
              fill: theme.palette.background.paper,
              stroke: theme.palette.primary.main,
              strokeWidth: 2,
              r: 4,
            }}
            strokeWidth={2}
          />
        </LineChart>
      </ResponsiveContainer>
    )
  }

  const renderPieChart = (data: CommunityStats['versionDistribution']) => {
    // 计算总数用于百分比计算
    const total = data.reduce((sum, item) => sum + item.count, 0)

    // 先按版本字符串排序数据
    const sortedData = [...data].sort((a, b) => a.version.localeCompare(b.version))

    // 增强数据，添加总数字段用于工具提示
    const enhancedData = sortedData.map(item => ({
      ...item,
      total,
    }))

    return (
      <ResponsiveContainer width="100%" height={320}>
        <PieChart>
          <defs>
            {enhancedData.map((_entry: VersionData, index: number) => {
              const color = COLORS[index % COLORS.length]
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
            data={enhancedData}
            cx="40%"
            cy="50%"
            labelLine={false}
            outerRadius={100}
            fill="#8884d8"
            dataKey="count"
            nameKey="version"
            label={({ cx, cy, midAngle, innerRadius, outerRadius, percent }) => {
              const RADIAN = Math.PI / 180
              const radius =
                (innerRadius as number) + ((outerRadius as number) - (innerRadius as number)) * 0.5
              const x = (cx as number) + radius * Math.cos(-midAngle * RADIAN)
              const y = (cy as number) + radius * Math.sin(-midAngle * RADIAN)

              return (
                <text
                  x={x}
                  y={y}
                  fill={
                    theme.palette.mode === 'dark'
                      ? theme.palette.grey[100]
                      : theme.palette.grey[800]
                  }
                  textAnchor={x > (cx as number) ? 'start' : 'end'}
                  dominantBaseline="central"
                  fontSize={12}
                  fontWeight="bold"
                >
                  {`${(percent * 100).toFixed(0)}%`}
                </text>
              )
            }}
          >
            {enhancedData.map((_entry: VersionData, index: number) => (
              <Cell
                key={`cell-${index}`}
                fill={`url(#colorGradient-${index})`}
                stroke={theme.palette.background.paper}
                strokeWidth={2}
              />
            ))}
          </Pie>
          <Tooltip
            content={<CustomPieTooltip />}
            wrapperStyle={{ zIndex: 1000, outline: 'none' }}
          />
          <Legend
            layout="vertical"
            verticalAlign="middle"
            align="right"
            wrapperStyle={{ paddingRight: 20 }}
            formatter={value => (
              <span
                style={{
                  color: theme.palette.text.primary,
                  fontWeight: 'medium',
                  fontSize: '0.875rem',
                  paddingLeft: 4,
                  paddingRight: 4,
                }}
              >
                {value}
              </span>
            )}
          />
        </PieChart>
      </ResponsiveContainer>
    )
  }

  if (loading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '70vh' }}>
        <CircularProgress />
      </Box>
    )
  }

  if (error) {
    return (
      <Box sx={{ p: 3 }}>
        <Alert severity="error">{error}</Alert>
      </Box>
    )
  }

  if (!stats) {
    return (
      <Box sx={{ p: 3 }}>
        <Alert severity="info">暂无统计数据</Alert>
      </Box>
    )
  }

  return (
    <Box sx={{ p: 3 }}>
      <Grid container spacing={3} sx={{ mb: 4 }}>
        <Grid item xs={12} sm={6} md={3}>
          <StatCard
            title="实例总数"
            value={stats.totalInstances}
            icon={<StorageIcon />}
            color="#3f51b5"
          />
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <StatCard
            title="活跃实例"
            value={stats.activeInstances}
            icon={<CheckCircleIcon />}
            color="#4caf50"
          />
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <StatCard
            title="总用户数"
            value={formatNumber(stats.totalUsers)}
            icon={<PeopleIcon />}
            color="#ff9800"
          />
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <StatCard
            title="沙盒调用"
            value={formatNumber(stats.totalSandboxCalls)}
            icon={<CodeIcon />}
            color="#e91e63"
          />
        </Grid>
      </Grid>

      <Grid container spacing={3}>
        <Grid item xs={12} md={6}>
          <Card
            sx={{
              transition: 'all 0.3s ease',
              height: 400,
              '&:hover': {
                boxShadow: theme.shadows[4],
              },
            }}
          >
            <CardContent sx={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
              <Typography variant="h6" gutterBottom>
                社区活跃版本分布
              </Typography>
              {renderPieChart(stats.versionDistribution)}
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} md={6}>
          <Card
            sx={{
              transition: 'all 0.3s ease',
              height: 400,
              '&:hover': {
                boxShadow: theme.shadows[4],
              },
            }}
          >
            <CardContent sx={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
              <Typography variant="h6" gutterBottom>
                新增实例趋势
              </Typography>
              {renderLineChart(stats.newInstancesTrend)}
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      <Box sx={{ mt: 4 }}>
        <Typography variant="subtitle1" color="text.secondary" gutterBottom>
          最后更新时间:{' '}
          {format(new Date(stats.lastUpdated), 'yyyy-MM-dd HH:mm:ss', { locale: zhCN })}
        </Typography>
      </Box>
    </Box>
  )
}
