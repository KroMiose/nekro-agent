import React, { useState, useEffect, useCallback } from 'react'
import { 
  Box, 
  Tabs, 
  Tab, 
  Grid, 
  Stack, 
  useMediaQuery, 
  useTheme, 
  Card,
  Button,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Typography,
  Alert
} from '@mui/material'
import { QueryClient, QueryClientProvider, useQuery } from '@tanstack/react-query'
import {
  Message as MessageIcon,
  Group as GroupIcon,
  Code as CodeIcon,
  CheckCircle as CheckCircleIcon,
  RestartAlt as RestartIcon,
} from '@mui/icons-material'
import { dashboardApi, RealTimeDataPoint } from '../../services/api/dashboard'
import { restartApi } from '../../services/api/restart'
import { useNotification } from '../../hooks/useNotification'
import { StatCard } from './components/StatCard'
import { TrendsChart } from './components/TrendsChart'
import { DistributionsCard } from './components/DistributionsCard'
import { RankingList } from './components/RankingList'
import { RealTimeStats } from './components/RealTimeStats'
import { createEventStream } from '../../services/api/utils/stream'
import { CARD_VARIANTS } from '../../theme/variants'

// 定义时间范围类型
type TimeRange = 'day' | 'week' | 'month'

const DashboardContent: React.FC = () => {
  // 状态
  const [timeRange, setTimeRange] = useState<TimeRange>('day')
  const [realTimeData, setRealTimeData] = useState<RealTimeDataPoint[]>([])
  const [granularity, setGranularity] = useState<number>(10) // 默认10分钟粒度
  const [streamCancel, setStreamCancel] = useState<(() => void) | null>(null)
  const [restartDialogOpen, setRestartDialogOpen] = useState(false)
  const [isRestarting, setIsRestarting] = useState(false)

  const theme = useTheme()
  const isMobile = useMediaQuery(theme.breakpoints.down('md'))
  const isSmallMobile = useMediaQuery(theme.breakpoints.down('sm'))
  const notification = useNotification()

  // 处理实时数据
  const handleRealTimeData = useCallback((data: string) => {
    try {
      const newData = JSON.parse(data) as RealTimeDataPoint
      setRealTimeData(prev => {
        // 检查是否已存在相同时间戳的数据点
        const existingIndex = prev.findIndex(item => item.timestamp === newData.timestamp)

        if (existingIndex >= 0) {
          // 更新已存在的数据点
          const updated = [...prev]
          updated[existingIndex] = newData
          return updated
        } else {
          // 添加新数据点并保持按时间排序
          const updated = [...prev, newData].sort(
            (a, b) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime()
          )

          // 限制数据点数量，保留最近50个数据点
          if (updated.length > 50) {
            return updated.slice(updated.length - 50)
          }
          return updated
        }
      })
    } catch (error) {
      console.error('解析实时数据失败:', error)
    }
  }, [])

  // 初始化实时数据流
  useEffect(() => {
    // 取消之前的流
    if (streamCancel) {
      streamCancel()
    }

    // 清空之前的数据
    setRealTimeData([])

    // 创建新的流连接
    const cancelStream = createEventStream({
      endpoint: `/dashboard/stats/stream?granularity=${granularity}`,
      onMessage: handleRealTimeData,
      onError: error => console.error('仪表盘数据流错误:', error),
    })

    // 保存取消函数
    setStreamCancel(() => cancelStream)

    return () => {
      if (cancelStream) cancelStream()
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [handleRealTimeData, granularity])

  // 处理粒度变更
  const handleGranularityChange = useCallback((newGranularity: number) => {
    setGranularity(newGranularity)
  }, [])

  // 查询概览数据
  const { data: overview, isLoading: overviewLoading } = useQuery({
    queryKey: ['dashboard-overview', timeRange],
    queryFn: () => dashboardApi.getOverview({ time_range: timeRange }),
  })

  // 查询趋势数据
  const { data: trends, isLoading: trendsLoading } = useQuery({
    queryKey: ['dashboard-trends', timeRange],
    queryFn: () =>
      dashboardApi.getTrends({
        metrics: 'messages,sandbox_calls,success_calls,failed_calls,success_rate',
        time_range: timeRange,
        interval: timeRange === 'day' ? 'hour' : 'day',
      }),
  })

  // 查询分布数据
  const { data: distributions, isLoading: distributionsLoading } = useQuery({
    queryKey: ['dashboard-distributions', timeRange],
    queryFn: () => dashboardApi.getDistributions({ time_range: timeRange }),
  })

  // 查询活跃用户排名
  const { data: activeUsers, isLoading: usersLoading } = useQuery({
    queryKey: ['dashboard-active-ranking', 'users', timeRange],
    queryFn: () =>
      dashboardApi.getActiveRanking({
        ranking_type: 'users',
        time_range: timeRange,
      }),
  })

  const handleTimeRangeChange = (_: React.SyntheticEvent, newValue: TimeRange) => {
    setTimeRange(newValue)
  }

  // 处理重启系统
  const handleRestartSystem = async () => {
    setIsRestarting(true)
    try {
      const response = await restartApi.restartSystem()
      if (response.code === 200) {
        notification.success('系统重启请求已发送，请稍候...')
        setRestartDialogOpen(false)
      } else {
        notification.error(response.msg || '重启失败')
      }
    } catch (error) {
      console.error('重启系统失败:', error)
      notification.error('重启系统失败，请检查网络连接')
    } finally {
      setIsRestarting(false)
    }
  }

  return (
    <Box className="h-[calc(100vh-64px)] flex flex-col gap-3 overflow-auto p-4">
      {/* 时间范围选择器 */}
      <Card sx={{ ...CARD_VARIANTS.default.styles, flexShrink: 0 }}>
        <Box sx={{ 
          display: 'flex', 
          alignItems: 'center', 
          justifyContent: 'space-between',
          px: { xs: 1, md: 3 }
        }}>
          <Tabs 
            value={timeRange} 
            onChange={handleTimeRangeChange} 
            variant={isSmallMobile ? 'fullWidth' : 'standard'}
            indicatorColor="primary"
            textColor="primary"
            sx={{
              minHeight: 56,
              flex: 1,
              '& .MuiTab-root': {
                minHeight: 56,
                fontSize: '0.875rem',
                fontWeight: 600,
                textTransform: 'none',
                transition: 'all 0.2s ease',
                borderRadius: '8px',
                mx: 0.5,
                '&:hover': {
                  backgroundColor: theme.palette.action.hover,
                },
                '&.Mui-selected': {
                  color: theme.palette.primary.main,
                  backgroundColor: theme.palette.primary.main + '10',
                },
              },
              '& .MuiTabs-indicator': {
                height: 3,
                borderRadius: '2px',
                boxShadow: `0 0 8px ${theme.palette.primary.main}`,
              },
            }}
          >
            <Tab value="day" label="今天" />
            <Tab value="week" label="本周" />
            <Tab value="month" label="本月" />
          </Tabs>
          
          <Button
            variant="outlined"
            color="error"
            startIcon={<RestartIcon />}
            onClick={() => setRestartDialogOpen(true)}
            sx={{
              ml: 2,
              minWidth: 'auto',
              px: { xs: 1.5, sm: 2 },
              fontSize: '0.875rem',
              fontWeight: 600,
              textTransform: 'none',
              borderRadius: '8px',
              transition: 'all 0.2s ease',
              '&:hover': {
                transform: 'translateY(-1px)',
                boxShadow: `0 4px 12px ${theme.palette.error.main}20`,
              },
            }}
          >
            {isSmallMobile ? '' : '重启系统'}
          </Button>
        </Box>
      </Card>

      {/* 统计卡片 - 移动端改为两行显示 */}
      {isMobile ? (
        <Grid container spacing={2} className="flex-shrink-0">
          <Grid item xs={6} sm={6}>
            <StatCard
              title="总消息数"
              value={overview?.total_messages || 0}
              loading={overviewLoading}
              icon={<MessageIcon />}
            />
          </Grid>
          <Grid item xs={6} sm={6}>
            <StatCard
              title="活跃会话"
              value={overview?.active_sessions || 0}
              loading={overviewLoading}
              icon={<GroupIcon />}
            />
          </Grid>
          <Grid item xs={6} sm={6}>
            <StatCard
              title="独立用户"
              value={overview?.unique_users || 0}
              loading={overviewLoading}
              icon={<MessageIcon />}
            />
          </Grid>
          <Grid item xs={6} sm={6}>
            <StatCard
              title="沙盒执行"
              value={overview?.total_sandbox_calls || 0}
              loading={overviewLoading}
              icon={<CodeIcon />}
            />
          </Grid>
          <Grid item xs={12}>
            <StatCard
              title="执行成功率"
              value={`${overview?.success_rate || 0}%`}
              loading={overviewLoading}
              icon={<CheckCircleIcon />}
              color={(overview?.success_rate || 0) >= 90 ? 'success.main' : 'warning.main'}
            />
          </Grid>
        </Grid>
      ) : (
        <Stack 
          direction="row" 
          spacing={2} 
          className="flex-shrink-0"
          sx={{ 
            overflowX: 'auto',
            pb: 1,
            '&::-webkit-scrollbar': {
              height: 8,
            },
            '&::-webkit-scrollbar-thumb': {
              backgroundColor:
                theme.palette.mode === 'dark' ? 'rgba(255,255,255,0.2)' : 'rgba(0,0,0,0.2)',
              borderRadius: 4,
            },
          }}
        >
          <StatCard
            title="总消息数"
            value={overview?.total_messages || 0}
            loading={overviewLoading}
            icon={<MessageIcon />}
          />
          <StatCard
            title="活跃会话"
            value={overview?.active_sessions || 0}
            loading={overviewLoading}
            icon={<GroupIcon />}
          />
          <StatCard
            title="独立用户"
            value={overview?.unique_users || 0}
            loading={overviewLoading}
            icon={<MessageIcon />}
          />
          <StatCard
            title="沙盒执行"
            value={overview?.total_sandbox_calls || 0}
            loading={overviewLoading}
            icon={<CodeIcon />}
          />
          <StatCard
            title="执行成功率"
            value={`${overview?.success_rate || 0}%`}
            loading={overviewLoading}
            icon={<CheckCircleIcon />}
            color={(overview?.success_rate || 0) >= 90 ? 'success.main' : 'warning.main'}
          />
        </Stack>
      )}

      {/* 趋势图和实时数据 */}
      <Grid container spacing={2}>
        {/* 在移动端上，RealTimeStats 和 TrendsChart 各占一行 */}
        <Grid item xs={12} lg={8}>
          <RealTimeStats
            title="实时数据"
            data={realTimeData}
            granularity={granularity}
            onGranularityChange={handleGranularityChange}
          />
        </Grid>
        <Grid item xs={12} lg={4}>
          <TrendsChart
            title="概览"
            data={trends}
            loading={trendsLoading}
            metrics={['messages', 'sandbox_calls']}
            timeRange={timeRange}
          />
        </Grid>
      </Grid>

      {/* 消息和执行趋势 */}
      <Grid container spacing={2}>
        <Grid item xs={12} md={6}>
          <TrendsChart
            title="执行状态"
            data={trends}
            loading={trendsLoading}
            metrics={['success_calls', 'failed_calls']}
            timeRange={timeRange}
          />
        </Grid>
        <Grid item xs={12} md={6}>
          <TrendsChart
            title="响应成功率"
            data={trends}
            loading={trendsLoading}
            metrics={['success_rate']}
            timeRange={timeRange}
          />
        </Grid>
      </Grid>

      {/* 分布统计与排名 - 移动端上改为垂直布局 */}
      <Grid container spacing={2}>
        <Grid item xs={12} lg={8}>
          <DistributionsCard
            stopTypeData={distributions?.stop_type}
            messageTypeData={distributions?.message_type}
            loading={distributionsLoading}
          />
        </Grid>
        <Grid item xs={12} lg={4}>
          <RankingList title="活跃排名" data={activeUsers} loading={usersLoading} type="users" />
        </Grid>
      </Grid>

      {/* 重启系统确认对话框 */}
      <Dialog
        open={restartDialogOpen}
        onClose={() => !isRestarting && setRestartDialogOpen(false)}
        PaperProps={{
          sx: {
            ...CARD_VARIANTS.default.styles,
          },
        }}
      >
        <DialogTitle
          sx={{
            px: 3,
            py: 2,
            background: theme =>
              theme.palette.mode === 'dark' ? 'rgba(255,255,255,0.03)' : 'rgba(0,0,0,0.02)',
          }}
        >
          重启系统确认
        </DialogTitle>
        <DialogContent sx={{ p: 3 }}>
          <Alert severity="warning" sx={{ mb: 2 }}>
            重启期间 WebUI 功能将无法正常使用，如果长时间未恢复请检查 NekroAgent 容器日志是否出现异常
          </Alert>
          <Typography sx={{ mt: 1, mb: 2 }}>
            确定要重启系统吗？重启过程可能需要大概一分钟，请耐心等待。
          </Typography>
        </DialogContent>
        <DialogActions sx={{ px: 3, py: 2 }}>
          <Button 
            onClick={() => setRestartDialogOpen(false)}
            disabled={isRestarting}
          >
            取消
          </Button>
          <Button 
            onClick={handleRestartSystem}
            color="error" 
            variant="contained"
            disabled={isRestarting}
            startIcon={<RestartIcon />}
          >
            {isRestarting ? '重启中...' : '确认重启'}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  )
}

// 提供查询客户端
const DashboardPage: React.FC = () => {
  const queryClient = new QueryClient()

  return (
    <QueryClientProvider client={queryClient}>
      <DashboardContent />
    </QueryClientProvider>
  )
}

export default DashboardPage
