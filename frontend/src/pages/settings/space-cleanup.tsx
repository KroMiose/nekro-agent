import { useState, useEffect, useCallback, useRef, useMemo } from 'react'
import {
  Box,
  Button,
  Typography,
  LinearProgress,
  Grid,
  Chip,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Checkbox,
  TextField,
  Alert,
  CircularProgress,
  List,
  ListItem,
  ListItemText,
  Paper,
  Stack,
  IconButton,
  FormControlLabel,
  Switch,
  alpha,
  useTheme,
  useMediaQuery,
  Collapse,
  ListItemButton,
  Tooltip,
  ToggleButton,
  ToggleButtonGroup,
} from '@mui/material'
import {
  Refresh as RefreshIcon,
  Delete as DeleteIcon,
  ExpandMore as ExpandMoreIcon,
  ExpandLess as ExpandLessIcon,
  Storage as StorageIcon,
  Folder as FolderIcon,
  Warning as WarningIcon,
  CheckCircle as CheckCircleIcon,
  Error as ErrorIcon,
  Info as InfoIcon,
  Schedule as ScheduleIcon,
  CleaningServices as CleaningServicesIcon,
  Search as SearchIcon,
  PieChart as PieChartIcon,
  Extension as ExtensionIcon,
} from '@mui/icons-material'
import { motion, AnimatePresence } from 'framer-motion'
import {
  PieChart,
  Pie,
  Cell,
  ResponsiveContainer,
  Tooltip as RechartsTooltip,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Legend,
} from 'recharts'
import { useNotification } from '../../hooks/useNotification'
import { CARD_VARIANTS, SCROLLBAR_VARIANTS } from '../../theme/variants'
import {
  spaceCleanupApi,
  formatBytes,
  formatDuration,
  ResourceType,
  CleanupStatus,
  type ScanResult,
  type CleanupRequest,
  type CleanupProgress,
  type CleanupResult,
  type ResourceCategory,
} from '../../services/api/space-cleanup'
import { chatChannelApi } from '../../services/api/chat-channel'
import { useQuery } from '@tanstack/react-query'

const MotionBox = motion(Box)

// 颜色方案
const COLORS = [
  '#FF6B6B',
  '#4ECDC4',
  '#45B7D1',
  '#FFA07A',
  '#98D8C8',
  '#F7DC6F',
  '#BB8FCE',
  '#85C1E2',
  '#F8B739',
  '#52B788',
]

// 风险等级排序权重
const RISK_LEVEL_WEIGHT = {
  safe: 1,
  warning: 2,
  danger: 3,
}

// 资源排序函数
const sortResources = (categories: ResourceCategory[]): ResourceCategory[] => {
  return [...categories].sort((a, b) => {
    // 1. 不可清理的排最后
    if (a.can_cleanup !== b.can_cleanup) {
      return a.can_cleanup ? -1 : 1
    }

    // 2. 可清理的按风险等级排序（风险低的在前）
    if (a.can_cleanup && b.can_cleanup) {
      const aWeight = RISK_LEVEL_WEIGHT[a.risk_level as keyof typeof RISK_LEVEL_WEIGHT] || 0
      const bWeight = RISK_LEVEL_WEIGHT[b.risk_level as keyof typeof RISK_LEVEL_WEIGHT] || 0
      if (aWeight !== bWeight) {
        return aWeight - bWeight
      }
    }

    // 3. 同等级按占用空间排序（大的在前）
    return b.total_size - a.total_size
  })
}

export default function SpaceCleanupPage() {
  const theme = useTheme()
  const notification = useNotification()
  const isMobile = useMediaQuery(theme.breakpoints.down('sm'))
  const isTablet = useMediaQuery(theme.breakpoints.down('md'))
  const scanIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null)
  const cleanupIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null)

  // 扫描相关状态
  const [initialLoading, setInitialLoading] = useState(true)
  const [scanning, setScanning] = useState(false)
  const [scanProgress, setScanProgress] = useState(0)
  const [loadingResult, setLoadingResult] = useState(false) // 是否正在加载扫描结果
  const [scanResult, setScanResult] = useState<ScanResult | null>(null)

  // 清理相关状态
  const [cleaning, setCleaning] = useState(false)
  const [cleanupProgress, setCleanupProgress] = useState<CleanupProgress | null>(null)
  const [cleanupResult, setCleanupResult] = useState<CleanupResult | null>(null)

  // 过滤条件
  const [selectedResourceTypes, setSelectedResourceTypes] = useState<ResourceType[]>([])
  const [selectedChatKeys, setSelectedChatKeys] = useState<Record<ResourceType, string[]>>(
    {} as Record<ResourceType, string[]>
  )
  const [beforeDays, setBeforeDays] = useState<number>(7)
  const [enableTimeFilter, setEnableTimeFilter] = useState(true)

  // UI 状态
  const [confirmDialogOpen, setConfirmDialogOpen] = useState(false)
  const [expandedCategories, setExpandedCategories] = useState<Set<string>>(new Set())
  const [rightChartType, setRightChartType] = useState<'pie' | 'bar'>('pie')

  // 获取所有聊天频道信息（用于显示频道名）
  const { data: allChannels } = useQuery({
    queryKey: ['chat-channels-all'],
    queryFn: async () => {
      // 获取所有聊天频道（不分页）
      const result = await chatChannelApi.getList({
        page: 1,
        page_size: 10000, // 获取所有频道
      })
      return result.items
    },
    staleTime: 5 * 60 * 1000, // 5分钟缓存
  })

  // 建立 chat_key 到 channel_name 的映射
  const chatKeyToNameMap = useMemo(() => {
    const map = new Map<string, string>()
    if (allChannels) {
      allChannels.forEach(channel => {
        map.set(channel.chat_key, channel.channel_name || channel.chat_key)
      })
    }
    return map
  }, [allChannels])

  // 清理定时器
  const clearScanInterval = useCallback(() => {
    if (scanIntervalRef.current) {
      clearTimeout(scanIntervalRef.current)
      scanIntervalRef.current = null
    }
  }, [])

  const clearCleanupInterval = useCallback(() => {
    if (cleanupIntervalRef.current) {
      clearTimeout(cleanupIntervalRef.current)
      cleanupIntervalRef.current = null
    }
  }, [])

  // 加载扫描结果
  const loadScanResult = useCallback(async () => {
    try {
      const result = await spaceCleanupApi.loadScanResultFromCache()
      setScanResult(result)
    } catch {
      console.log('暂无扫描结果')
    } finally {
      setInitialLoading(false)
    }
  }, [])

  // 启动扫描
  const handleStartScan = async () => {
    try {
      setScanning(true)
      setScanProgress(0)
      clearScanInterval()

      await spaceCleanupApi.startScan()
      notification.info('扫描已启动')

      // 轮询扫描进度（使用递归方式避免并发请求）
      const pollProgress = async () => {
        try {
          const progress = await spaceCleanupApi.getScanProgress()
          setScanProgress(progress.progress || 0)

          if (progress.status === 'completed') {
            clearScanInterval()
            // 扫描完成，但需要等待加载扫描结果
            setScanProgress(100)
            setLoadingResult(true)
            try {
              await loadScanResult()
              notification.success('扫描完成')
            } catch (error) {
              console.error('加载扫描结果失败:', error)
              notification.error('加载扫描结果失败')
            } finally {
              setScanning(false)
              setLoadingResult(false)
            }
          } else if (progress.status === 'failed') {
            clearScanInterval()
            setScanning(false)
            setLoadingResult(false)
            notification.error('扫描失败')
          } else if (progress.status === 'scanning') {
            // 继续轮询
            scanIntervalRef.current = setTimeout(pollProgress, 1000) as unknown as ReturnType<
              typeof setInterval
            >
          }
        } catch (error) {
          console.error('获取扫描进度失败:', error)
          // 出错后继续轮询
          scanIntervalRef.current = setTimeout(pollProgress, 2000) as unknown as ReturnType<
            typeof setInterval
          >
        }
      }

      // 启动轮询
      pollProgress()
    } catch {
      setScanning(false)
      notification.error('启动扫描失败')
    }
  }

  // 计算预计释放空间（返回 { min, max, hasUncertainty }）
  const calculateEstimatedSpace = useCallback((): {
    min: number
    max: number
    hasUncertainty: boolean
  } => {
    if (!scanResult) return { min: 0, max: 0, hasUncertainty: false }

    let minSpace = 0 // 能精确计算的空间（有文件详情的）
    let maxSpace = 0 // 最大可能空间（包含无法精确计算的）
    let hasUncertainty = false // 是否存在无法精确计算的资源

    const cutoffTimestamp =
      enableTimeFilter && beforeDays > 0 ? Date.now() / 1000 - beforeDays * 24 * 60 * 60 : null

    for (const category of scanResult.categories) {
      // 只计算选中的资源类型
      if (!selectedResourceTypes.includes(category.resource_type)) continue
      if (!category.can_cleanup) continue

      // 检查是否有文件详情（chat_resources 且有 files 数组）
      const hasFileDetails =
        category.chat_resources &&
        category.chat_resources.length > 0 &&
        category.chat_resources.some(cr => cr.files && cr.files.length > 0)

      // 检查该资源是否有 chat_resources（有些资源类型没有按聊天分组）
      const hasChatResources = category.chat_resources && category.chat_resources.length > 0

      // 获取该资源类型选中的聊天 keys
      const categoryChatKeys = selectedChatKeys[category.resource_type] || []

      // 如果有选中的聊天
      if (categoryChatKeys.length > 0) {
        if (hasChatResources) {
          // 有 chat_resources 的资源类型，只计算选中的聊天
          for (const chatRes of category.chat_resources || []) {
            if (!categoryChatKeys.includes(chatRes.chat_key)) continue

            if (cutoffTimestamp) {
              // 启用了时间过滤
              if (chatRes.files && chatRes.files.length > 0) {
                // 有文件详情，按时间精确过滤
                for (const file of chatRes.files) {
                  if (file.modified_time < cutoffTimestamp) {
                    minSpace += file.size
                    maxSpace += file.size
                  }
                }
              } else {
                // 没有文件详情，无法精确计算
                // min: 0（可能没有符合条件的文件）
                // max: total_size（可能所有文件都符合条件）
                maxSpace += chatRes.total_size
                hasUncertainty = true
              }
            } else {
              // 不过滤时间，使用总大小（精确）
              minSpace += chatRes.total_size
              maxSpace += chatRes.total_size
            }
          }
        } else {
          // 没有 chat_resources 的资源类型（如缓存、依赖包等）
          // 这些资源不是按聊天分组的，清理时会完全清理
          if (cutoffTimestamp) {
            // 启用了时间过滤
            if (!category.supports_time_filter) {
              // 不支持时间过滤的资源，完全清理
              minSpace += category.total_size
              maxSpace += category.total_size
            } else {
              // 支持时间过滤但没有文件详情，无法精确计算
              maxSpace += category.total_size
              hasUncertainty = true
            }
          } else {
            // 不过滤时间，完全清理
            minSpace += category.total_size
            maxSpace += category.total_size
          }
        }
      } else {
        // 没有选中聊天，计算所有资源
        if (cutoffTimestamp) {
          // 启用了时间过滤
          if (!category.supports_time_filter) {
            // 不支持时间过滤的资源（如Python包、缓存等），完全清理
            minSpace += category.total_size
            maxSpace += category.total_size
          } else if (hasFileDetails) {
            // 支持时间过滤且有文件详情，按时间精确过滤
            for (const chatRes of category.chat_resources || []) {
              if (chatRes.files && chatRes.files.length > 0) {
                for (const file of chatRes.files) {
                  if (file.modified_time < cutoffTimestamp) {
                    minSpace += file.size
                    maxSpace += file.size
                  }
                }
              }
            }
          } else {
            // 支持时间过滤但没有文件详情，无法精确计算
            // min: 0（最坏情况）
            // max: total_size（最好情况）
            maxSpace += category.total_size
            hasUncertainty = true
          }
        } else {
          // 不过滤时间，直接使用分类总大小（精确）
          minSpace += category.total_size
          maxSpace += category.total_size
        }
      }
    }

    return { min: minSpace, max: maxSpace, hasUncertainty }
  }, [scanResult, selectedResourceTypes, selectedChatKeys, beforeDays, enableTimeFilter])

  // 获取预计释放空间
  const estimatedSpace = useMemo(() => calculateEstimatedSpace(), [calculateEstimatedSpace])

  // 启动清理
  const handleStartCleanup = async () => {
    if (selectedResourceTypes.length === 0) {
      notification.warning('请选择要清理的资源类型')
      return
    }
    setConfirmDialogOpen(true)
  }

  // 确认清理
  const handleConfirmCleanup = async () => {
    setConfirmDialogOpen(false)

    try {
      setCleaning(true)
      setCleanupProgress(null)
      setCleanupResult(null)
      clearCleanupInterval()

      // 收集所有选中的聊天 keys（合并所有资源类型的选中聊天）
      const allSelectedChatKeys = selectedResourceTypes
        .flatMap(rt => selectedChatKeys[rt] || [])
        .filter((key, index, arr) => arr.indexOf(key) === index) // 去重

      const request: CleanupRequest = {
        resource_types: selectedResourceTypes,
        chat_keys: allSelectedChatKeys.length > 0 ? allSelectedChatKeys : undefined,
        before_date:
          enableTimeFilter && beforeDays > 0
            ? new Date(Date.now() - beforeDays * 24 * 60 * 60 * 1000).toISOString()
            : undefined,
        dry_run: false,
      }

      const { task_id: taskId } = await spaceCleanupApi.startCleanup(request)
      notification.info('清理已启动')

      // 轮询清理进度（使用递归方式避免并发请求）
      const pollCleanupProgress = async () => {
        try {
          const progress = await spaceCleanupApi.getCleanupProgress(taskId)
          setCleanupProgress(progress)

          if (progress.status === CleanupStatus.COMPLETED) {
            clearCleanupInterval()
            setCleaning(false)
            const result: CleanupResult = {
              task_id: progress.task_id,
              status: progress.status,
              total_files: progress.total_files,
              deleted_files: progress.processed_files,
              failed_files: 0,
              freed_space: progress.freed_space,
              failed_file_list: [],
            }
            setCleanupResult(result)
            notification.success('清理完成')
            await handleStartScan()
          } else if (progress.status === CleanupStatus.FAILED) {
            clearCleanupInterval()
            setCleaning(false)
            const result: CleanupResult = {
              task_id: progress.task_id,
              status: progress.status,
              total_files: progress.total_files,
              deleted_files: progress.processed_files,
              failed_files: 0,
              freed_space: progress.freed_space,
              error_message: progress.message,
              failed_file_list: [],
            }
            setCleanupResult(result)
            notification.error('清理失败')
          } else if (progress.status === CleanupStatus.RUNNING) {
            // 继续轮询
            cleanupIntervalRef.current = setTimeout(
              pollCleanupProgress,
              1000
            ) as unknown as ReturnType<typeof setInterval>
          }
        } catch (error) {
          console.error('获取清理进度失败:', error)
          // 出错后继续轮询
          cleanupIntervalRef.current = setTimeout(
            pollCleanupProgress,
            2000
          ) as unknown as ReturnType<typeof setInterval>
        }
      }

      // 启动轮询
      pollCleanupProgress()
    } catch {
      setCleaning(false)
      notification.error('启动清理失败')
    }
  }

  // 切换分类展开状态
  const toggleCategory = (categoryType: string) => {
    setExpandedCategories(prev => {
      const newSet = new Set(prev)
      if (newSet.has(categoryType)) {
        newSet.delete(categoryType)
      } else {
        newSet.add(categoryType)
      }
      return newSet
    })
  }

  // 初始加载
  useEffect(() => {
    loadScanResult()
    return () => {
      clearScanInterval()
      clearCleanupInterval()
    }
  }, [loadScanResult, clearScanInterval, clearCleanupInterval])

  // 获取风险图标
  const getRiskIcon = (riskLevel: string) => {
    switch (riskLevel) {
      case 'safe':
        return <CheckCircleIcon color="success" fontSize="small" />
      case 'warning':
        return <WarningIcon color="warning" fontSize="small" />
      case 'danger':
        return <ErrorIcon color="error" fontSize="small" />
      default:
        return <InfoIcon color="info" fontSize="small" />
    }
  }

  // 准备系统空间分布数据（左侧饼图）
  const systemSpaceData = useMemo(() => {
    if (!scanResult?.disk_info) return []

    const freeSpace = scanResult.disk_info.free_space || 0
    const nekroAgentSize = scanResult.disk_info.data_dir_size || 0
    const usedSpace = scanResult.disk_info.used_space || 0
    // 其他数据空间 = 系统已使用空间 - NekroAgent 数据
    const otherDataSize = Math.max(0, usedSpace - nekroAgentSize)

    return [
      {
        name: '系统闲置空间',
        value: freeSpace,
        color: COLORS[4],
      },
      {
        name: '其他数据空间',
        value: otherDataSize,
        color: COLORS[8],
      },
      {
        name: 'NekroAgent 数据',
        value: nekroAgentSize,
        color: COLORS[0],
      },
    ].filter(item => item.value > 0)
  }, [scanResult])

  // 准备资源分布数据（右侧图表）
  const resourceDistributionData =
    scanResult?.categories
      .filter(c => c.total_size > 0)
      .map((category, index) => ({
        name: category.display_name,
        value: category.total_size,
        color: COLORS[index % COLORS.length],
      })) || []

  // 准备柱状图数据
  const barChartData =
    scanResult?.categories
      .filter(c => c.total_size > 0)
      .sort((a, b) => b.total_size - a.total_size)
      .slice(0, 10)
      .map(category => ({
        name: category.display_name,
        size: category.total_size / (1024 * 1024 * 1024), // 转换为 GB
        files: category.file_count,
      })) || []

  // 自定义图表工具提示
  const CustomTooltip = ({
    active,
    payload,
  }: {
    active?: boolean
    payload?: Array<{
      name: string
      value: number
      payload?: { value?: number; name?: string; size?: number }
    }>
  }) => {
    if (active && payload && payload.length) {
      const data = payload[0]
      return (
        <Paper
          sx={{
            p: 1.5,
            background: alpha(theme.palette.background.paper, 0.95),
            backdropFilter: 'blur(10px)',
            border: `1px solid ${theme.palette.divider}`,
            borderRadius: 1,
          }}
        >
          <Typography variant="body2" fontWeight="600">
            {data.payload?.name || data.name}
          </Typography>
          <Typography variant="caption" color="text.secondary">
            {data.payload?.size !== undefined
              ? `${data.payload.size.toFixed(2)} GB`
              : formatBytes(data.payload?.value || data.value || 0)}
          </Typography>
        </Paper>
      )
    }
    return null
  }

  // 排序后的资源列表
  const sortedCategories = scanResult ? sortResources(scanResult.categories) : []

  return (
    <Box className="h-full flex flex-col overflow-auto p-4">
      <Box sx={{ mb: 4 }}>
        {/* 扫描控制区域 */}
        <Paper className="p-4 mb-4" sx={CARD_VARIANTS.default.styles}>
          <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
            <SearchIcon sx={{ mr: 1, color: 'primary.main', fontSize: 28 }} />
            <Typography variant="h6">占用分析</Typography>
          </Box>

          <Alert severity="warning" sx={{ mb: 2 }}>
            <Typography variant="body2">
              空间回收功能尚处于实验性阶段，请注意备份关键数据并谨慎使用
            </Typography>
          </Alert>

          <Box
            sx={{
              display: 'flex',
              flexDirection: isMobile ? 'column' : 'row',
              justifyContent: 'space-between',
              alignItems: isMobile ? 'flex-start' : 'center',
              gap: isMobile ? 2 : 0,
            }}
          >
            <Box sx={{ mt: 2, flex: 1 }}>
              {(scanResult && (
                <Typography
                  variant="body2"
                  color="text.secondary"
                  sx={{ fontSize: isMobile ? '0.75rem' : '0.875rem' }}
                >
                  上次扫描:{' '}
                  {scanResult.summary.end_time
                    ? new Date(scanResult.summary.end_time).toLocaleString('zh-CN')
                    : '未知'}{' '}
                  · 耗时 {formatDuration(scanResult.summary.duration_seconds || 0)} · 发现{' '}
                  {scanResult.summary.total_files || 0} 个文件
                </Typography>
              )) || (
                <Typography variant="body2" color="text.secondary">
                  待扫描资源...
                </Typography>
              )}
            </Box>
            <Button
              variant="contained"
              startIcon={
                scanning ? <CircularProgress size={20} color="inherit" /> : <RefreshIcon />
              }
              onClick={handleStartScan}
              disabled={scanning}
              fullWidth={isMobile}
              size={isMobile ? 'medium' : 'large'}
            >
              {scanning ? '扫描中...' : scanResult ? '重新扫描' : '开始扫描'}
            </Button>
          </Box>

          {/* 扫描进度 */}
          <AnimatePresence>
            {scanning && (
              <MotionBox
                initial={{ opacity: 0, height: 0 }}
                animate={{ opacity: 1, height: 'auto' }}
                exit={{ opacity: 0, height: 0 }}
                transition={{ duration: 0.3 }}
              >
                <Box sx={{ mt: 2 }}>
                  <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
                    <Typography variant="body2" color="text.secondary">
                      {loadingResult ? '正在加载扫描结果...' : '正在扫描资源...'}
                    </Typography>
                    {!loadingResult && (
                      <Typography variant="body2" fontWeight="600">
                        {scanProgress.toFixed(1)}%
                      </Typography>
                    )}
                  </Box>
                  <LinearProgress
                    variant={loadingResult ? 'indeterminate' : 'determinate'}
                    value={loadingResult ? undefined : scanProgress}
                    sx={{
                      height: 8,
                      borderRadius: 4,
                      backgroundColor: alpha(theme.palette.primary.main, 0.1),
                      '& .MuiLinearProgress-bar': {
                        borderRadius: 4,
                        background: loadingResult
                          ? `linear-gradient(90deg, ${theme.palette.info.main} 0%, ${theme.palette.info.light} 100%)`
                          : `linear-gradient(90deg, ${theme.palette.success.main} 0%, ${theme.palette.success.light} 100%)`,
                      },
                    }}
                  />
                </Box>
              </MotionBox>
            )}
          </AnimatePresence>
        </Paper>

        {/* 未扫描状态 */}
        {initialLoading && (
          <Paper className="p-4 mb-4" sx={CARD_VARIANTS.default.styles}>
            <Box sx={{ textAlign: 'center', py: 6 }}>
              <CircularProgress size={60} sx={{ mb: 2 }} />
              <Typography variant="h6" gutterBottom>
                正在加载扫描结果...
              </Typography>
              <Typography variant="body2" color="text.secondary">
                请稍候
              </Typography>
            </Box>
          </Paper>
        )}

        {!initialLoading && !scanResult && !scanning && !loadingResult && (
          <Paper className="p-4 mb-4" sx={CARD_VARIANTS.default.styles}>
            <Box sx={{ textAlign: 'center', py: 6 }}>
              <CleaningServicesIcon sx={{ fontSize: 80, color: 'text.disabled', mb: 2 }} />
              <Typography variant="h6" gutterBottom>
                尚未进行空间扫描
              </Typography>
              <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
                点击上方的"开始扫描"按钮，系统将分析各类资源的占用情况
              </Typography>
            </Box>
          </Paper>
        )}

        {/* 磁盘信息和图表 */}
        {scanResult?.summary && (
          <Paper className="p-4 mb-4" sx={CARD_VARIANTS.default.styles}>
            <Box sx={{ display: 'flex', alignItems: 'center', mb: 3 }}>
              <PieChartIcon sx={{ mr: 1, color: 'primary.main' }} />
              <Typography variant="h6">空间分布概览</Typography>
            </Box>

            <Grid container spacing={3}>
              {/* 统计卡片 */}
              <Grid item xs={12} sm={6} md={3}>
                <Paper
                  sx={{
                    p: 2.5,
                    background: alpha(theme.palette.primary.main, 0.05),
                    border: `1px solid ${alpha(theme.palette.primary.main, 0.2)}`,
                    borderRadius: 2,
                    textAlign: 'center',
                  }}
                >
                  <StorageIcon sx={{ fontSize: 40, color: 'primary.main', mb: 1 }} />
                  <Typography variant="body2" color="text.secondary" gutterBottom>
                    系统总空间
                  </Typography>
                  <Typography
                    variant={isMobile ? 'h6' : 'h5'}
                    fontWeight="bold"
                    color="primary.main"
                    sx={{ fontSize: isMobile ? '1.1rem' : '1.5rem' }}
                  >
                    {formatBytes(scanResult.disk_info?.total_space || 0)}
                  </Typography>
                </Paper>
              </Grid>
              <Grid item xs={12} sm={6} md={3}>
                <Paper
                  sx={{
                    p: 2.5,
                    background: alpha(theme.palette.info.main, 0.05),
                    border: `1px solid ${alpha(theme.palette.info.main, 0.2)}`,
                    borderRadius: 2,
                    textAlign: 'center',
                  }}
                >
                  <FolderIcon sx={{ fontSize: 40, color: 'info.main', mb: 1 }} />
                  <Typography variant="body2" color="text.secondary" gutterBottom>
                    NekroAgent 占用
                  </Typography>
                  <Typography
                    variant={isMobile ? 'h6' : 'h5'}
                    fontWeight="bold"
                    color="info.main"
                    sx={{ fontSize: isMobile ? '1.1rem' : '1.5rem' }}
                  >
                    {formatBytes(scanResult.disk_info?.data_dir_size || 0)}
                  </Typography>
                </Paper>
              </Grid>
              <Grid item xs={12} sm={6} md={3}>
                <Paper
                  sx={{
                    p: 2.5,
                    background: alpha(theme.palette.success.main, 0.05),
                    border: `1px solid ${alpha(theme.palette.success.main, 0.2)}`,
                    borderRadius: 2,
                    textAlign: 'center',
                  }}
                >
                  <DeleteIcon sx={{ fontSize: 40, color: 'success.main', mb: 1 }} />
                  <Typography variant="body2" color="text.secondary" gutterBottom>
                    可清理空间
                  </Typography>
                  <Typography
                    variant={isMobile ? 'h6' : 'h5'}
                    fontWeight="bold"
                    color="success.main"
                    sx={{ fontSize: isMobile ? '1.1rem' : '1.5rem' }}
                  >
                    {formatBytes(scanResult.summary.total_size || 0)}
                  </Typography>
                </Paper>
              </Grid>
              <Grid item xs={12} sm={6} md={3}>
                <Paper
                  sx={{
                    p: 2.5,
                    background: alpha(theme.palette.warning.main, 0.05),
                    border: `1px solid ${alpha(theme.palette.warning.main, 0.2)}`,
                    borderRadius: 2,
                    textAlign: 'center',
                  }}
                >
                  <WarningIcon sx={{ fontSize: 40, color: 'warning.main', mb: 1 }} />
                  <Typography variant="body2" color="text.secondary" gutterBottom>
                    文件总数
                  </Typography>
                  <Typography
                    variant={isMobile ? 'h6' : 'h5'}
                    fontWeight="bold"
                    color="warning.main"
                    sx={{ fontSize: isMobile ? '1.1rem' : '1.5rem' }}
                  >
                    {scanResult.summary.total_files?.toLocaleString() || 0}
                  </Typography>
                </Paper>
              </Grid>

              {/* 系统空间分布饼图 */}
              <Grid item xs={12} md={6}>
                <Paper
                  sx={{
                    p: 2,
                    background: alpha(theme.palette.background.paper, 0.6),
                    backdropFilter: 'blur(10px)',
                    border: `1px solid ${alpha(theme.palette.divider, 0.1)}`,
                    borderRadius: 2,
                    height: 350,
                    display: 'flex',
                    flexDirection: 'column',
                    overflow: 'hidden',
                  }}
                >
                  <Typography variant="subtitle1" fontWeight="600" gutterBottom sx={{ flexShrink: 0 }}>
                    系统空间分布
                  </Typography>
                  <Box sx={{ flex: 1, minHeight: 0, width: '100%' }}>
                    <ResponsiveContainer width="100%" height="100%">
                      <PieChart>
                        <Pie
                          data={systemSpaceData}
                          cx={isMobile ? '50%' : '35%'}
                          cy={isMobile ? '45%' : '50%'}
                          labelLine={false}
                          outerRadius={isMobile ? 80 : 80}
                          innerRadius={isMobile ? 50 : 50}
                          fill="#8884d8"
                          dataKey="value"
                        >
                          {systemSpaceData.map((entry, index) => (
                            <Cell key={`cell-${index}`} fill={entry.color} />
                          ))}
                        </Pie>
                        <RechartsTooltip content={<CustomTooltip />} />
                        <Legend
                          layout={isMobile ? 'horizontal' : 'vertical'}
                          verticalAlign={isMobile ? 'bottom' : 'middle'}
                          align={isMobile ? 'center' : 'right'}
                          wrapperStyle={{
                            fontSize: isMobile ? '11px' : '12px',
                            color: theme.palette.text.primary,
                            paddingLeft: isMobile ? '0' : '20px',
                            paddingTop: isMobile ? '15px' : '0',
                          }}
                        />
                      </PieChart>
                    </ResponsiveContainer>
                  </Box>
                </Paper>
              </Grid>

              {/* 资源分布图（可切换饼图/柱状图） */}
              <Grid item xs={12} md={6}>
                <Paper
                  sx={{
                    p: 2,
                    background: alpha(theme.palette.background.paper, 0.6),
                    backdropFilter: 'blur(10px)',
                    border: `1px solid ${alpha(theme.palette.divider, 0.1)}`,
                    borderRadius: 2,
                    height: isMobile ? 410 : 350,
                    display: 'flex',
                    flexDirection: 'column',
                    overflow: 'hidden',
                  }}
                >
                  <Box
                    sx={{
                      display: 'flex',
                      flexDirection: isMobile ? 'column' : 'row',
                      justifyContent: 'space-between',
                      alignItems: isMobile ? 'flex-start' : 'center',
                      gap: isMobile ? 1 : 0,
                      mb: 1,
                      flexShrink: 0,
                    }}
                  >
                    <Typography variant="subtitle1" fontWeight="600">
                      NekroAgent 资源分布
                    </Typography>
                    <ToggleButtonGroup
                      value={rightChartType}
                      exclusive
                      onChange={(_, newType) => {
                        if (newType !== null) {
                          setRightChartType(newType)
                        }
                      }}
                      size="small"
                      sx={{ width: isMobile ? '100%' : 'auto' }}
                    >
                      <ToggleButton value="pie" sx={{ flex: isMobile ? 1 : 'none' }}>
                        饼图
                      </ToggleButton>
                      <ToggleButton value="bar" sx={{ flex: isMobile ? 1 : 'none' }}>
                        排行
                      </ToggleButton>
                    </ToggleButtonGroup>
                  </Box>
                  <Box sx={{ flex: 1, minHeight: 0, width: '100%' }}>
                    <ResponsiveContainer width="100%" height="100%">
                      {rightChartType === 'pie' ? (
                        <PieChart>
                          <Pie
                            data={resourceDistributionData}
                            cx={isMobile ? '50%' : '35%'}
                            cy={isMobile ? '45%' : '50%'}
                            labelLine={false}
                            outerRadius={isMobile ? 80 : 80}
                            innerRadius={isMobile ? 50 : 50}
                            fill="#8884d8"
                            dataKey="value"
                          >
                            {resourceDistributionData.map((entry, index) => (
                              <Cell key={`cell-${index}`} fill={entry.color} />
                            ))}
                          </Pie>
                          <RechartsTooltip content={<CustomTooltip />} />
                          <Legend
                            layout={isMobile ? 'horizontal' : 'vertical'}
                            verticalAlign={isMobile ? 'bottom' : 'middle'}
                            align={isMobile ? 'center' : 'right'}
                            wrapperStyle={{
                              fontSize: isMobile ? '11px' : '12px',
                              color: theme.palette.text.primary,
                              paddingLeft: isMobile ? '0' : '20px',
                              paddingTop: isMobile ? '15px' : '0',
                            }}
                          />
                        </PieChart>
                      ) : (
                        <BarChart data={barChartData} layout="vertical">
                          <CartesianGrid
                            strokeDasharray="3 3"
                            stroke={alpha(theme.palette.divider, 0.2)}
                          />
                          <XAxis
                            type="number"
                            stroke={theme.palette.text.secondary}
                            style={{ fontSize: isMobile ? '10px' : '12px' }}
                          />
                          <YAxis
                            dataKey="name"
                            type="category"
                            width={isMobile ? 60 : 100}
                            stroke={theme.palette.text.secondary}
                            style={{ fontSize: isMobile ? '10px' : '12px' }}
                          />
                          <RechartsTooltip content={<CustomTooltip />} />
                          <Bar
                            dataKey="size"
                            fill={theme.palette.primary.main}
                            radius={[0, 8, 8, 0]}
                          />
                        </BarChart>
                      )}
                    </ResponsiveContainer>
                  </Box>
                </Paper>
              </Grid>
            </Grid>
          </Paper>
        )}

        {/* 资源分类列表 */}
        {scanResult && sortedCategories.length > 0 && (
          <Paper className="p-4 mb-4" sx={CARD_VARIANTS.default.styles}>
            <Box
              sx={{
                display: 'flex',
                flexDirection: isMobile ? 'column' : 'row',
                alignItems: isMobile ? 'flex-start' : 'center',
                mb: 3,
                gap: isMobile ? 1 : 0,
              }}
            >
              <Box sx={{ display: 'flex', alignItems: 'center' }}>
                <FolderIcon sx={{ mr: 1, color: 'primary.main' }} />
                <Typography variant="h6">资源分类详情</Typography>
              </Box>
              {!isMobile && (
                <Typography variant="body2" color="text.secondary" sx={{ ml: 2 }}>
                  点击展开查看详细信息
                </Typography>
              )}
            </Box>

            <List
              sx={{ ...SCROLLBAR_VARIANTS.thin.styles, maxHeight: 600, overflow: 'auto', pr: 2 }}
            >
              {sortedCategories.map(category => (
                <Box key={category.resource_type}>
                  <Box
                    sx={{
                      borderRadius: 2,
                      mb: 1,
                      border: selectedResourceTypes.includes(category.resource_type)
                        ? `2px solid ${theme.palette.primary.main}`
                        : `1px solid ${alpha(theme.palette.divider, 0.1)}`,
                      background: selectedResourceTypes.includes(category.resource_type)
                        ? alpha(theme.palette.primary.main, 0.05)
                        : 'transparent',
                      display: 'flex',
                      alignItems: 'center',
                    }}
                  >
                    {/* Checkbox 区域 - 只处理选择 */}
                    {category.can_cleanup && (
                      <Box
                        onClick={e => e.stopPropagation()}
                        sx={{
                          display: 'flex',
                          alignItems: 'center',
                          p: 1,
                          cursor: 'pointer',
                        }}
                      >
                        <Checkbox
                          checked={selectedResourceTypes.includes(category.resource_type)}
                          onChange={e => {
                            if (e.target.checked) {
                              setSelectedResourceTypes(prev => [...prev, category.resource_type])
                            } else {
                              setSelectedResourceTypes(prev =>
                                prev.filter(t => t !== category.resource_type)
                              )
                              // 取消选择资源类型时，清除该资源类型的聊天选择
                              setSelectedChatKeys(prev => {
                                const newChatKeys = { ...prev }
                                delete newChatKeys[category.resource_type]
                                return newChatKeys
                              })
                            }
                          }}
                        />
                      </Box>
                    )}
                    {/* 主要内容区域 - 处理展开/关闭 */}
                    <ListItemButton
                      onClick={() => {
                        // 只有有内容才允许展开
                        const hasContent =
                          (category.plugin_resources && category.plugin_resources.length > 0) ||
                          (category.chat_resources && category.chat_resources.length > 0)
                        if (hasContent) {
                          toggleCategory(category.resource_type)
                        }
                      }}
                      sx={{
                        flex: 1,
                        borderRadius: 2,
                        '&:hover': {
                          background: alpha(theme.palette.primary.main, 0.08),
                        },
                      }}
                    >
                      <Box
                        sx={{
                          display: 'flex',
                          flexDirection: isMobile ? 'column' : 'row',
                          alignItems: isMobile ? 'flex-start' : 'center',
                          gap: isMobile ? 1 : 2,
                          flex: 1,
                          width: '100%',
                        }}
                      >
                        <Box
                          sx={{
                            display: 'flex',
                            alignItems: 'center',
                            gap: 1,
                            width: isMobile ? '100%' : 'auto',
                            flex: 1,
                            minWidth: 0,
                          }}
                        >
                          {category.risk_message ? (
                            <Tooltip title={category.risk_message} arrow placement="top">
                              <Box sx={{ display: 'inline-flex', cursor: 'help', flexShrink: 0 }}>
                                {getRiskIcon(category.risk_level)}
                              </Box>
                            </Tooltip>
                          ) : (
                            <Box sx={{ flexShrink: 0 }}>{getRiskIcon(category.risk_level)}</Box>
                          )}
                          <ListItemText
                            primary={
                              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, flexWrap: 'wrap' }}>
                                <Typography
                                  variant={isMobile ? 'body2' : 'subtitle1'}
                                  fontWeight="600"
                                >
                                  {category.display_name}
                                </Typography>
                                {!category.supports_time_filter && category.can_cleanup && (
                                  <Tooltip
                                    title="此类资源不支持按时间过滤（如Python包、特殊资源缓存等），启用时间过滤时将完全清理"
                                    arrow
                                    placement="top"
                                  >
                                    <InfoIcon
                                      fontSize="small"
                                      sx={{
                                        color: 'text.secondary',
                                        cursor: 'help',
                                        fontSize: isMobile ? '0.875rem' : '1rem',
                                        '&:hover': {
                                          color: 'primary.main',
                                        },
                                      }}
                                    />
                                  </Tooltip>
                                )}
                                {!category.can_cleanup && (
                                  <Chip
                                    label="仅查看"
                                    size="small"
                                    variant="outlined"
                                    sx={{ fontSize: isMobile ? '0.65rem' : '0.75rem', height: isMobile ? 18 : 'auto' }}
                                  />
                                )}
                              </Box>
                            }
                            secondary={
                              <Typography
                                variant="body2"
                                color="text.secondary"
                                sx={{
                                  overflow: 'hidden',
                                  textOverflow: 'ellipsis',
                                  whiteSpace: isMobile ? 'normal' : 'nowrap',
                                  mt: 0.5,
                                  fontSize: isMobile ? '0.75rem' : '0.875rem',
                                }}
                              >
                                {category.description}
                              </Typography>
                            }
                          />
                        </Box>
                        <Stack
                          direction="row"
                          spacing={0.5}
                          sx={{
                            mr: isMobile ? 0 : 2,
                            ml: isMobile ? 0 : 'auto',
                            flexShrink: 0,
                          }}
                        >
                          <Chip
                            label={formatBytes(category.total_size)}
                            size="small"
                            color="primary"
                            variant="outlined"
                            sx={{ fontSize: isMobile ? '0.65rem' : '0.875rem', height: isMobile ? 20 : 'auto' }}
                          />
                          <Chip
                            label={`${category.file_count} 文件`}
                            size="small"
                            variant="outlined"
                            sx={{ fontSize: isMobile ? '0.65rem' : '0.875rem', height: isMobile ? 20 : 'auto' }}
                          />
                        </Stack>
                        {/* 只有有内容才显示展开按钮 */}
                        {((category.plugin_resources && category.plugin_resources.length > 0) ||
                          (category.chat_resources && category.chat_resources.length > 0)) && (
                          <IconButton
                            size="small"
                            onClick={e => {
                              e.stopPropagation()
                              toggleCategory(category.resource_type)
                            }}
                          >
                            {expandedCategories.has(category.resource_type) ? (
                              <ExpandLessIcon />
                            ) : (
                              <ExpandMoreIcon />
                            )}
                          </IconButton>
                        )}
                      </Box>
                    </ListItemButton>
                  </Box>

                  <Collapse
                    in={expandedCategories.has(category.resource_type)}
                    timeout="auto"
                    unmountOnExit
                  >
                    <Box sx={{ py: 1, pr: 2, pl: 4 }}>
                      {/* 插件资源 */}
                      {category.plugin_resources && category.plugin_resources.length > 0 && (
                        <Box sx={{ mb: 2 }}>
                          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
                            <ExtensionIcon fontSize="small" color="primary" />
                            <Typography variant="subtitle2">
                              插件资源 ({category.plugin_resources.length})
                            </Typography>
                          </Box>
                          <List
                            dense
                            sx={{
                              maxHeight: 200,
                              overflow: 'auto',
                              ...SCROLLBAR_VARIANTS.thin.styles,
                            }}
                          >
                            {category.plugin_resources
                              .sort((a, b) => b.total_size - a.total_size)
                              .map(pluginRes => (
                                <ListItem key={pluginRes.plugin_key}>
                                  <ListItemText
                                    primary={pluginRes.plugin_name || pluginRes.plugin_key}
                                    secondary={`${formatBytes(pluginRes.total_size)} · ${pluginRes.file_count} 文件`}
                                  />
                                </ListItem>
                              ))}
                          </List>
                        </Box>
                      )}

                      {/* 聊天资源 */}
                      {category.chat_resources && category.chat_resources.length > 0 && (
                        <Box>
                          <Typography variant="subtitle2" gutterBottom>
                            聊天资源 ({category.chat_resources.length})
                          </Typography>
                          <Box
                            sx={{
                              maxHeight: 200,
                              overflow: 'auto',
                              ...SCROLLBAR_VARIANTS.thin.styles,
                              pr: 2,
                            }}
                          >
                            <Grid container spacing={1}>
                              {category.chat_resources
                                .sort((a, b) => b.total_size - a.total_size)
                                .slice(0, 20)
                                .map(chatRes => {
                                  // 对于沙盒临时代码，目录名格式是 sandbox_{chat_key}，需要提取实际的 chat_key
                                  let actualChatKey = chatRes.chat_key
                                  let displayName = chatRes.chat_name || chatRes.chat_key

                                  if (
                                    category.resource_type === ResourceType.SANDBOX_SHARED &&
                                    chatRes.chat_key.startsWith('sandbox_')
                                  ) {
                                    // 提取实际的 chat_key（去掉 sandbox_ 前缀）
                                    actualChatKey = chatRes.chat_key.replace(/^sandbox_/, '')
                                    // 使用实际的 chat_key 查找频道名
                                    displayName =
                                      chatKeyToNameMap.get(actualChatKey) ||
                                      chatRes.chat_name ||
                                      chatRes.chat_key
                                  } else {
                                    // 其他资源类型直接使用 chat_key 查找
                                    displayName =
                                      chatKeyToNameMap.get(chatRes.chat_key) ||
                                      chatRes.chat_name ||
                                      chatRes.chat_key
                                  }

                                  const isChatSelected = (
                                    selectedChatKeys[category.resource_type] || []
                                  ).includes(chatRes.chat_key)

                                  return (
                                    <Grid item xs={12} sm={6} md={isTablet ? 6 : 4} lg={3} key={chatRes.chat_key}>
                                      <ListItemButton
                                        onClick={() => {
                                          if (category.can_cleanup) {
                                            const currentChatKeys =
                                              selectedChatKeys[category.resource_type] || []
                                            if (isChatSelected) {
                                              setSelectedChatKeys(prev => ({
                                                ...prev,
                                                [category.resource_type]: currentChatKeys.filter(
                                                  k => k !== chatRes.chat_key
                                                ),
                                              }))
                                            } else {
                                              setSelectedChatKeys(prev => ({
                                                ...prev,
                                                [category.resource_type]: [
                                                  ...currentChatKeys,
                                                  chatRes.chat_key,
                                                ],
                                              }))
                                            }
                                          }
                                        }}
                                        sx={{
                                          borderRadius: 1,
                                          height: '100%',
                                          flexDirection: 'column',
                                          alignItems: 'flex-start',
                                          py: isMobile ? 1 : 1.5,
                                          px: isMobile ? 1 : 1.5,
                                          background: isChatSelected
                                            ? alpha(theme.palette.primary.main, 0.1)
                                            : 'transparent',
                                          '&:hover': {
                                            background: isChatSelected
                                              ? alpha(theme.palette.primary.main, 0.15)
                                              : alpha(theme.palette.action.hover, 0.05),
                                          },
                                        }}
                                      >
                                        <Box
                                          sx={{
                                            display: 'flex',
                                            alignItems: 'center',
                                            width: '100%',
                                            mb: 0.5,
                                          }}
                                        >
                                          {category.can_cleanup && (
                                            <Checkbox
                                              checked={isChatSelected}
                                              size="small"
                                              onClick={e => e.stopPropagation()}
                                              onChange={e => {
                                                const currentChatKeys =
                                                  selectedChatKeys[category.resource_type] || []
                                                if (e.target.checked) {
                                                  setSelectedChatKeys(prev => ({
                                                    ...prev,
                                                    [category.resource_type]: [
                                                      ...currentChatKeys,
                                                      chatRes.chat_key,
                                                    ],
                                                  }))
                                                } else {
                                                  setSelectedChatKeys(prev => ({
                                                    ...prev,
                                                    [category.resource_type]:
                                                      currentChatKeys.filter(
                                                        k => k !== chatRes.chat_key
                                                      ),
                                                  }))
                                                }
                                              }}
                                              sx={{ mr: 0.5, p: 0.5 }}
                                            />
                                          )}
                                          <Typography
                                            variant={isMobile ? 'caption' : 'body2'}
                                            sx={{
                                              flex: 1,
                                              fontWeight: 500,
                                              overflow: 'hidden',
                                              textOverflow: 'ellipsis',
                                              whiteSpace: 'nowrap',
                                              fontSize: isMobile ? '0.75rem' : '0.875rem',
                                            }}
                                          >
                                            {displayName}
                                          </Typography>
                                        </Box>
                                        <Stack
                                          direction="row"
                                          spacing={0.5}
                                          sx={{ width: '100%', mt: 0.5 }}
                                        >
                                          <Chip
                                            label={formatBytes(chatRes.total_size)}
                                            size="small"
                                            variant="outlined"
                                            sx={{
                                              height: isMobile ? 18 : 20,
                                              fontSize: isMobile ? '0.65rem' : '0.7rem',
                                            }}
                                          />
                                          <Chip
                                            label={`${chatRes.file_count} 文件`}
                                            size="small"
                                            variant="outlined"
                                            sx={{
                                              height: isMobile ? 18 : 20,
                                              fontSize: isMobile ? '0.65rem' : '0.7rem',
                                            }}
                                          />
                                        </Stack>
                                      </ListItemButton>
                                    </Grid>
                                  )
                                })}
                            </Grid>
                          </Box>
                        </Box>
                      )}
                    </Box>
                  </Collapse>
                </Box>
              ))}
            </List>
          </Paper>
        )}

        {/* 清理控制 */}
        {scanResult && (
          <Paper className="p-4 mb-4" sx={CARD_VARIANTS.default.styles}>
            <Box sx={{ display: 'flex', alignItems: 'center', mb: 3 }}>
              <DeleteIcon sx={{ mr: 1, color: 'error.main' }} />
              <Typography variant="h6">清理设置</Typography>
            </Box>

            <Grid container spacing={3}>
              <Grid item xs={12} md={6}>
                <FormControlLabel
                  control={
                    <Switch
                      checked={enableTimeFilter}
                      onChange={e => setEnableTimeFilter(e.target.checked)}
                    />
                  }
                  label={
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                      <ScheduleIcon fontSize="small" />
                      <Typography variant="body2">启用时间过滤</Typography>
                    </Box>
                  }
                />
                <TextField
                  type="number"
                  label="清理多少天前的文件"
                  value={beforeDays}
                  onChange={e => setBeforeDays(Math.max(0, parseInt(e.target.value) || 0))}
                  fullWidth
                  disabled={!enableTimeFilter}
                  helperText={enableTimeFilter ? '仅清理指定天数前修改的文件' : '已禁用时间过滤'}
                  sx={{ mt: 2 }}
                />
                <Stack
                  direction={isMobile ? 'column' : 'row'}
                  spacing={2}
                  sx={{ mt: 3 }}
                >
                  <Button
                    variant="contained"
                    color="error"
                    startIcon={
                      cleaning ? <CircularProgress size={20} color="inherit" /> : <DeleteIcon />
                    }
                    onClick={handleStartCleanup}
                    disabled={cleaning || scanning || loadingResult || selectedResourceTypes.length === 0}
                    fullWidth={isMobile}
                  >
                    {cleaning ? '清理中...' : '开始清理'}
                  </Button>
                  <Button
                    variant="outlined"
                    onClick={() => {
                      setSelectedResourceTypes([])
                      setSelectedChatKeys({} as Record<ResourceType, string[]>)
                    }}
                    disabled={cleaning || scanning || loadingResult}
                    fullWidth={isMobile}
                  >
                    清除选择
                  </Button>
                </Stack>
              </Grid>
              <Grid item xs={12} md={6}>
                <Paper
                  sx={{
                    p: 3,
                    height: '100%',
                    display: 'flex',
                    flexDirection: 'column',
                    justifyContent: 'center',
                    alignItems: 'center',
                    background: alpha(theme.palette.success.main, 0.05),
                    border: `1px solid ${alpha(theme.palette.success.main, 0.2)}`,
                    borderRadius: 2,
                  }}
                >
                  <Typography variant="body2" color="text.secondary" gutterBottom>
                    预计释放空间
                  </Typography>
                  {estimatedSpace.hasUncertainty ? (
                    <>
                      <Typography
                        variant={isMobile ? 'h5' : 'h3'}
                        fontWeight="bold"
                        color="success.main"
                        sx={{ fontSize: isMobile ? '1.5rem' : '2.5rem', textAlign: 'center' }}
                      >
                        {formatBytes(estimatedSpace.min)} ~ {formatBytes(estimatedSpace.max)}
                      </Typography>
                      <Typography
                        variant="caption"
                        color="warning.main"
                        sx={{ mt: 1, display: 'block', textAlign: 'center', fontSize: isMobile ? '0.7rem' : '0.75rem' }}
                      >
                        ⚠️ 部分资源无法精确按时间过滤，显示为范围值
                      </Typography>
                    </>
                  ) : (
                    <Typography
                      variant={isMobile ? 'h5' : 'h3'}
                      fontWeight="bold"
                      color="success.main"
                      sx={{ fontSize: isMobile ? '1.5rem' : '2.5rem', textAlign: 'center' }}
                    >
                      {formatBytes(estimatedSpace.min)}
                    </Typography>
                  )}
                  <Typography variant="caption" color="text.secondary" sx={{ mt: 1 }}>
                    已选择 {selectedResourceTypes.length} 个资源类型
                    {(() => {
                      // 收集所有资源类型的聊天 keys 并去重
                      const allChatKeys = new Set<string>()
                      selectedResourceTypes.forEach(rt => {
                        ;(selectedChatKeys[rt] || []).forEach(key => allChatKeys.add(key))
                      })
                      return allChatKeys.size > 0 ? ` · ${allChatKeys.size} 个聊天` : ''
                    })()}
                  </Typography>
                </Paper>
              </Grid>
            </Grid>

            {/* 清理进度 */}
            <AnimatePresence>
              {cleaning && cleanupProgress && (
                <MotionBox
                  initial={{ opacity: 0, height: 0 }}
                  animate={{ opacity: 1, height: 'auto' }}
                  exit={{ opacity: 0, height: 0 }}
                  transition={{ duration: 0.3 }}
                >
                  <Box sx={{ mt: 3 }}>
                    <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
                      <Typography variant="body2" color="text.secondary">
                        {cleanupProgress.message || '正在清理...'}
                      </Typography>
                      <Typography variant="body2" fontWeight="600">
                        {cleanupProgress.processed_files}/{cleanupProgress.total_files} 文件
                      </Typography>
                    </Box>
                    <LinearProgress
                      variant="determinate"
                      value={cleanupProgress.progress}
                      sx={{
                        height: 8,
                        borderRadius: 4,
                        backgroundColor: alpha(theme.palette.error.main, 0.1),
                        '& .MuiLinearProgress-bar': {
                          borderRadius: 4,
                          background: `linear-gradient(90deg, ${theme.palette.error.main} 0%, ${theme.palette.error.light} 100%)`,
                        },
                      }}
                    />
                    <Typography
                      variant="caption"
                      color="text.secondary"
                      sx={{ mt: 1, display: 'block' }}
                    >
                      已释放: {formatBytes(cleanupProgress.freed_space)}
                    </Typography>
                  </Box>
                </MotionBox>
              )}
            </AnimatePresence>

            {/* 清理结果 */}
            <AnimatePresence>
              {cleanupResult && (
                <MotionBox
                  initial={{ opacity: 0, scale: 0.95 }}
                  animate={{ opacity: 1, scale: 1 }}
                  exit={{ opacity: 0, scale: 0.95 }}
                  transition={{ duration: 0.3 }}
                >
                  <Alert
                    severity={
                      cleanupResult.status === CleanupStatus.COMPLETED ? 'success' : 'error'
                    }
                    sx={{ mt: 3 }}
                  >
                    <Typography variant="body2" fontWeight="600" gutterBottom>
                      清理{cleanupResult.status === CleanupStatus.COMPLETED ? '完成' : '失败'}
                    </Typography>
                    <Stack direction="row" spacing={2} flexWrap="wrap" sx={{ mt: 1 }}>
                      <Chip
                        label={`删除 ${cleanupResult.deleted_files}/${cleanupResult.total_files} 文件`}
                        size="small"
                        variant="outlined"
                      />
                      <Chip
                        label={`释放 ${formatBytes(cleanupResult.freed_space)}`}
                        size="small"
                        variant="outlined"
                        color="success"
                      />
                      {cleanupResult.duration_seconds && (
                        <Chip
                          label={`耗时 ${formatDuration(cleanupResult.duration_seconds)}`}
                          size="small"
                          variant="outlined"
                        />
                      )}
                    </Stack>
                  </Alert>
                </MotionBox>
              )}
            </AnimatePresence>
          </Paper>
        )}
      </Box>

      {/* 确认对话框 */}
      <Dialog
        open={confirmDialogOpen}
        onClose={() => setConfirmDialogOpen(false)}
        maxWidth="sm"
        fullWidth
        fullScreen={isMobile}
      >
        <DialogTitle>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <WarningIcon color="warning" />
            <Typography variant="h6" fontWeight="600">
              确认清理
            </Typography>
          </Box>
        </DialogTitle>
        <DialogContent>
          <Alert severity="warning" sx={{ mb: 2 }}>
            <Typography variant="body2" fontWeight="600">
              ⚠️ 清理操作不可恢复，请确认您的选择！
            </Typography>
          </Alert>
          <Paper
            sx={{
              p: 2,
              background: alpha(theme.palette.success.main, 0.05),
              border: `1px solid ${alpha(theme.palette.success.main, 0.2)}`,
              mb: 2,
            }}
          >
            <Typography variant="body2" color="text.secondary" gutterBottom>
              预计释放空间
            </Typography>
            {estimatedSpace.hasUncertainty ? (
              <>
                <Typography
                  variant={isMobile ? 'h6' : 'h5'}
                  fontWeight="bold"
                  color="success.main"
                  sx={{ fontSize: isMobile ? '1.2rem' : '1.5rem', textAlign: 'center' }}
                >
                  {formatBytes(estimatedSpace.min)} ~ {formatBytes(estimatedSpace.max)}
                </Typography>
                <Typography
                  variant="caption"
                  color="warning.main"
                  sx={{ mt: 1, display: 'block', textAlign: 'center', fontSize: isMobile ? '0.7rem' : '0.75rem' }}
                >
                  ⚠️ 部分资源（如缓存、日志）无法精确按时间过滤，实际清理空间在此范围内
                </Typography>
              </>
            ) : (
              <Typography
                variant={isMobile ? 'h6' : 'h5'}
                fontWeight="bold"
                color="success.main"
                sx={{ fontSize: isMobile ? '1.2rem' : '1.5rem', textAlign: 'center' }}
              >
                {formatBytes(estimatedSpace.min)}
              </Typography>
            )}
          </Paper>
          <Typography variant="body2" gutterBottom>
            已选择 {selectedResourceTypes.length} 个资源类型
          </Typography>
          {enableTimeFilter && beforeDays > 0 && (
            <Typography variant="body2" color="text.secondary">
              📅 仅清理 {beforeDays} 天前修改的文件
            </Typography>
          )}
          {(() => {
            // 收集所有资源类型的聊天 keys 并去重
            const allChatKeys = new Set<string>()
            selectedResourceTypes.forEach(rt => {
              ;(selectedChatKeys[rt] || []).forEach(key => allChatKeys.add(key))
            })
            return allChatKeys.size > 0 ? (
              <Typography variant="body2" color="text.secondary">
                💬 仅清理选定的 {allChatKeys.size} 个聊天
              </Typography>
            ) : null
          })()}
          {(() => {
            // 检查选中的资源类型中是否有风险等级为 warning 或 danger 的
            if (!scanResult) return null

            const riskyCategories = scanResult.categories.filter(
              cat =>
                selectedResourceTypes.includes(cat.resource_type) &&
                (cat.risk_level === 'warning' || cat.risk_level === 'danger')
            )

            if (riskyCategories.length === 0) return null

            // 按风险等级分组
            const dangerCategories = riskyCategories.filter(cat => cat.risk_level === 'danger')
            const warningCategories = riskyCategories.filter(cat => cat.risk_level === 'warning')

            return (
              <Box sx={{ mt: 3 }}>
                {dangerCategories.length > 0 && (
                  <Alert severity="error" sx={{ mb: 2 }}>
                    <Typography variant="body2" fontWeight="600" gutterBottom>
                      ⚠️ 高风险资源警告
                    </Typography>
                    <Box component="ul" sx={{ m: 0, pl: 2 }}>
                      {dangerCategories.map(cat => (
                        <li key={cat.resource_type}>
                          <Typography variant="body2">
                            <strong>{cat.display_name}</strong>
                            {cat.risk_message && `: ${cat.risk_message}`}
                          </Typography>
                        </li>
                      ))}
                    </Box>
                  </Alert>
                )}
                {warningCategories.length > 0 && (
                  <Alert severity="warning">
                    <Typography variant="body2" fontWeight="600" gutterBottom>
                      ⚠️ 中等风险资源提示
                    </Typography>
                    <Box component="ul" sx={{ m: 0, pl: 2 }}>
                      {warningCategories.map(cat => (
                        <li key={cat.resource_type}>
                          <Typography variant="body2">
                            <strong>{cat.display_name}</strong>
                            {cat.risk_message && `: ${cat.risk_message}`}
                          </Typography>
                        </li>
                      ))}
                    </Box>
                  </Alert>
                )}
              </Box>
            )
          })()}
        </DialogContent>
        <DialogActions
          sx={{
            p: 2.5,
            flexDirection: isMobile ? 'column-reverse' : 'row',
            gap: isMobile ? 1 : 0,
          }}
        >
          <Button
            onClick={() => setConfirmDialogOpen(false)}
            fullWidth={isMobile}
            size={isMobile ? 'large' : 'medium'}
          >
            取消
          </Button>
          <Button
            onClick={handleConfirmCleanup}
            color="error"
            variant="contained"
            fullWidth={isMobile}
            size={isMobile ? 'large' : 'medium'}
          >
            确认清理
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  )
}
