import React, { useState, useEffect, useCallback, useRef } from 'react'
import { useTranslation } from 'react-i18next'
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
  Alert,
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
  const streamCancelRef = useRef<(() => void) | null>(null)
  const [restartDialogOpen, setRestartDialogOpen] = useState(false)
  const [isRestarting, setIsRestarting] = useState(false)

  const theme = useTheme()
  const isMobile = useMediaQuery(theme.breakpoints.down('md'))
  const isSmallMobile = useMediaQuery(theme.breakpoints.down('sm'))
  const { t } = useTranslation('dashboard')
  const notification = useNotification()
  const notificationRef = useRef(notification)
  const tRef = useRef(t)

  // 处理实时数据
  useEffect(() => {
    notificationRef.current = notification
    tRef.current = t
  }, [notification, t])

  const handleRealTimeData = useCallback((data: string) => {
    if (!data || data.trim().length === 0) {
      return
    }
    const trimmed = data.trim()
    if (!trimmed.startsWith('{') || !trimmed.endsWith('}')) {
      return
    }
    try {
      const newData = JSON.parse(trimmed) as RealTimeDataPoint
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
      notificationRef.current.error(tRef.current('messages.operationFailed', { ns: 'common' }))
    }
  }, [])

  // 初始化实时数据流
  useEffect(() => {
    // 取消之前的流
    if (streamCancelRef.current) {
      streamCancelRef.current()
    }

    // 清空之前的数据
    setRealTimeData([])

    // 创建新的流连接
    const cancelStream = createEventStream({
      endpoint: `/dashboard/stats/stream?granularity=${granularity}`,
      onMessage: handleRealTimeData,
      onError: () => notificationRef.current.error(tRef.current('messages.connectionLost', { ns: 'common' })),
    })

    // 保存取消函数
    streamCancelRef.current = cancelStream

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
      if (response.ok) {
        notification.success(t('restart.requestSent'))
        setRestartDialogOpen(false)
      } else {
        notification.error(t('restart.failed'))
      }
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : String(error)
      notification.error(`${t('restart.networkError')}: ${errorMessage}`)
    } finally {
      setIsRestarting(false)
    }
  }

  return (
    <Box className="h-[calc(100vh-64px)] flex flex-col gap-3 overflow-auto p-4">
      {/* 时间范围选择器 */}
      <Card sx={{ ...CARD_VARIANTS.default.styles, flexShrink: 0 }}>
        <Box
          sx={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            px: { xs: 1, md: 3 },
          }}
        >
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
            <Tab value="day" label={t('tabs.day')} />
            <Tab value="week" label={t('tabs.week')} />
            <Tab value="month" label={t('tabs.month')} />
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
            {isSmallMobile ? '' : t('restart.button')}
          </Button>
        </Box>
      </Card>

      {/* 统计卡片 - 移动端改为两行显示 */}
      {isMobile ? (
        <Grid container spacing={2} className="flex-shrink-0">
          <Grid item xs={6} sm={6}>
            <StatCard
              title={t('cards.totalMessages')}
              value={overview?.total_messages || 0}
              loading={overviewLoading}
              icon={<MessageIcon />}
            />
          </Grid>
          <Grid item xs={6} sm={6}>
            <StatCard
              title={t('cards.activeChannels')}
              value={overview?.active_sessions || 0}
              loading={overviewLoading}
              icon={<GroupIcon />}
            />
          </Grid>
          <Grid item xs={6} sm={6}>
            <StatCard
              title={t('cards.uniqueUsers')}
              value={overview?.unique_users || 0}
              loading={overviewLoading}
              icon={<MessageIcon />}
            />
          </Grid>
          <Grid item xs={6} sm={6}>
            <StatCard
              title={t('cards.sandboxCalls')}
              value={overview?.total_sandbox_calls || 0}
              loading={overviewLoading}
              icon={<CodeIcon />}
            />
          </Grid>
          <Grid item xs={12}>
            <StatCard
              title={t('cards.successRate')}
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
            title={t('cards.totalMessages')}
            value={overview?.total_messages || 0}
            loading={overviewLoading}
            icon={<MessageIcon />}
          />
          <StatCard
            title={t('cards.activeChannels')}
            value={overview?.active_sessions || 0}
            loading={overviewLoading}
            icon={<GroupIcon />}
          />
          <StatCard
            title={t('cards.uniqueUsers')}
            value={overview?.unique_users || 0}
            loading={overviewLoading}
            icon={<MessageIcon />}
          />
          <StatCard
            title={t('cards.sandboxCalls')}
            value={overview?.total_sandbox_calls || 0}
            loading={overviewLoading}
            icon={<CodeIcon />}
          />
          <StatCard
            title={t('cards.successRate')}
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
            title={t('charts.realTimeData')}
            data={realTimeData}
            granularity={granularity}
            onGranularityChange={handleGranularityChange}
          />
        </Grid>
        <Grid item xs={12} lg={4}>
          <TrendsChart
            title={t('charts.overview')}
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
            title={t('charts.executionStatus')}
            data={trends}
            loading={trendsLoading}
            metrics={['success_calls', 'failed_calls']}
            timeRange={timeRange}
          />
        </Grid>
        <Grid item xs={12} md={6}>
          <TrendsChart
            title={t('charts.successRate')}
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
          <RankingList
            title={t('charts.activeRanking')}
            data={activeUsers}
            loading={usersLoading}
            type="users"
          />
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
          {t('restart.dialogTitle')}
        </DialogTitle>
        <DialogContent sx={{ p: 3 }}>
          <Alert severity="warning" sx={{ mb: 2 }}>
            {t('restart.warning')}
          </Alert>
          <Typography sx={{ mt: 1, mb: 2 }}>{t('restart.confirmMessage')}</Typography>
        </DialogContent>
        <DialogActions sx={{ px: 3, py: 2 }}>
          <Button onClick={() => setRestartDialogOpen(false)} disabled={isRestarting}>
            {t('restart.cancel')}
          </Button>
          <Button
            onClick={handleRestartSystem}
            color="error"
            variant="contained"
            disabled={isRestarting}
            startIcon={<RestartIcon />}
          >
            {isRestarting ? t('restart.restarting') : t('restart.confirm')}
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
