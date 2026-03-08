import { useState, useEffect, useCallback, useRef } from 'react'
import {
  Box,
  Card,
  CircularProgress,
  Alert,
  Tabs,
  Tab,
} from '@mui/material'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { useNavigate, useParams, useSearchParams } from 'react-router-dom'
import {
  workspaceApi,
  WorkspaceDetail as _WorkspaceDetail,
  commApi,
  streamCommLog,
} from '../../services/api/workspace'
import { CARD_VARIANTS } from '../../theme/variants'
import { useTheme } from '@mui/material/styles'
import { motion } from 'framer-motion'
import { useTranslation } from 'react-i18next'
import { useSystemEvents } from '../../hooks/useSystemEvents'

// Components
import WorkspaceHeader from './components/WorkspaceHeader'

// Tabs
import OverviewTab from './tabs/OverviewTab'
import SandboxTab from './tabs/SandboxTab'
import CommTab from './tabs/CommTab'
import MemoryTab from './tabs/MemoryTab'
import ExtensionsTab from './tabs/ExtensionsTab'
import PromptTab from './tabs/PromptTab'
import ConfigTab from './tabs/ConfigTab'

// ──────────────────────────────────────────
// Main: WorkspaceDetailPage
// ──────────────────────────────────────────
export default function WorkspaceDetailPage() {
  const { id } = useParams<{ id: string }>()
  const workspaceId = Number(id)
  const navigate = useNavigate()
  const theme = useTheme()
  const { t } = useTranslation('workspace')
  const queryClient = useQueryClient()
  const [activeTab, setActiveTab] = useState(0)
  const [commPrefill, setCommPrefill] = useState('')
  const [searchParams, setSearchParams] = useSearchParams()

  // 支持从外部跳转时通过 ?tab=comm 自动切换到对应 tab（如 AgentActivityCard 点击跳转）
  useEffect(() => {
    const tabParam = searchParams.get('tab')
    if (tabParam === 'comm') {
      setActiveTab(2)
      setSearchParams({}, { replace: true })
    }
  // 仅在页面挂载时执行一次
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const handleNavigateToComm = (prefill: string) => {
    setCommPrefill(prefill)
    setActiveTab(2)
  }

  // 快速轮询：沙盒操作后开启 2s 间隔，30s 后恢复正常
  const [fastPoll, setFastPoll] = useState(false)
  const fastPollTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  const handleSandboxMutate = useCallback(() => {
    setFastPoll(true)
    if (fastPollTimerRef.current) clearTimeout(fastPollTimerRef.current)
    fastPollTimerRef.current = setTimeout(() => {
      setFastPoll(false)
      fastPollTimerRef.current = null
    }, 30000)
  }, [])

  useEffect(() => {
    return () => {
      if (fastPollTimerRef.current) clearTimeout(fastPollTimerRef.current)
    }
  }, [])

  const {
    data: workspace,
    isLoading,
    error,
  } = useQuery({
    queryKey: ['workspace', workspaceId],
    queryFn: () => workspaceApi.getDetail(workspaceId),
    enabled: !isNaN(workspaceId),
  })

  // 全局 SSE 实时状态（驱动 status / container_name / host_port）
  const { workspaceStatuses } = useSystemEvents()
  const sseSnapshot = workspaceStatuses.get(workspaceId)

  // sandbox/status 轮询：仅用于获取 session_id / cc_version / claude_code_version
  // status/container_name/host_port 已由 SSE 驱动，此处轮询频率大幅降低
  const { data: sandboxStatus } = useQuery({
    queryKey: ['sandbox-status', workspaceId],
    queryFn: () => workspaceApi.getSandboxStatus(workspaceId),
    enabled: !isNaN(workspaceId) && !!workspace,
    refetchInterval: fastPoll ? 3000 : 30000,
  })

  // 将 SSE 快照覆盖到 sandboxStatus 的 status/container_name/host_port
  const effectiveSandboxStatus = sandboxStatus
    ? {
        ...sandboxStatus,
        status: sseSnapshot?.status ?? sandboxStatus.status,
        container_name: sseSnapshot?.container_name !== undefined ? sseSnapshot.container_name : sandboxStatus.container_name,
        host_port: sseSnapshot?.host_port !== undefined ? sseSnapshot.host_port : sandboxStatus.host_port,
      }
    : undefined

  // ── CC 工作状态跟踪（SSE CC_STATUS 事件驱动，初始化查一次队列） ──────────
  const [ccCurrentTool, setCcCurrentTool] = useState<string | null>(null)
  const [ccWorking, setCcWorking] = useState(false)

  // 初始化：页面加载时查一次队列获取初始状态（不轮询）
  const { data: commQueueStatus } = useQuery({
    queryKey: ['workspace-comm-queue', workspaceId],
    queryFn: () => commApi.getQueue(workspaceId),
    enabled: !!workspace && workspace.status === 'active',
  })
  useEffect(() => {
    if (commQueueStatus !== undefined) {
      setCcWorking((commQueueStatus.current_task ?? null) !== null)
    }
  }, [commQueueStatus])

  // CC 完成时清除工具名
  useEffect(() => {
    if (!ccWorking) setCcCurrentTool(null)
  }, [ccWorking])

  // SSE 驱动：CC_STATUS 更新运行状态，TOOL_CALL/TOOL_RESULT 追踪当前工具名
  // 重连时重新查询 queue 状态，避免断线期间丢失 CC_STATUS 事件
  useEffect(() => {
    if (!workspace) return
    return streamCommLog(
      workspaceId,
      entry => {
        if (entry.direction === 'CC_STATUS') {
          try { setCcWorking((JSON.parse(entry.content) as { running: boolean }).running) } catch { /* */ }
        } else if (entry.direction === 'TOOL_CALL') {
          try { setCcCurrentTool(JSON.parse(entry.content).name ?? null) } catch { /* */ }
        } else if (entry.direction === 'TOOL_RESULT') {
          setCcCurrentTool(null)
        }
      },
      undefined,
      () => {
        // SSE 重连后：重新查询 queue 状态，补偿断线期间可能丢失的 CC_STATUS 事件
        queryClient.invalidateQueries({ queryKey: ['workspace-comm-queue', workspaceId] })
      },
    )
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [workspaceId, workspace?.id])

  if (isNaN(workspaceId)) {
    return (
      <Box sx={{ p: 3 }}>
        <Alert severity="error">{t('detail.config.invalidId')}</Alert>
      </Box>
    )
  }

  if (isLoading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100%' }}>
        <CircularProgress />
      </Box>
    )
  }

  if (error || !workspace) {
    return (
      <Box sx={{ p: 3 }}>
        <Alert severity="error">{t('detail.config.loadFailed', { message: (error as Error)?.message ?? t('detail.config.invalidId') })}</Alert>
      </Box>
    )
  }

  return (
    <Box
      sx={{
        height: 'calc(100vh - 64px)',
        display: 'flex',
        flexDirection: 'column',
        overflow: 'hidden',
      }}
    >
      {/* 顶部栏：返回 + 名称 + 沙盒状态 Chip（可点击） */}
      <WorkspaceHeader
        workspace={workspace}
        sandboxStatus={effectiveSandboxStatus}
        ccWorking={ccWorking}
        ccCurrentTool={ccCurrentTool}
        onBack={() => navigate('/workspace')}
        onNavigateToSandbox={() => setActiveTab(1)}
      />

      {/* Tab 导航 */}
      <Box sx={{ px: 2, pt: 1.5, flexShrink: 0 }}>
        <Card sx={CARD_VARIANTS.default.styles}>
          <Tabs
            value={activeTab}
            onChange={(_, val: number) => setActiveTab(val)}
            indicatorColor="primary"
            textColor="primary"
            sx={{
              minHeight: 48,
              px: 2,
              '& .MuiTab-root': {
                minHeight: 48,
                fontSize: '0.875rem',
                fontWeight: 600,
                textTransform: 'none',
                transition: 'all 0.2s ease',
                borderRadius: '8px',
                mx: 0.5,
                '&:hover': { backgroundColor: theme.palette.action.hover },
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
            <Tab label={t('detail.tabs.overview')} />
            <Tab label={t('detail.tabs.sandbox')} />
            <Tab
              label={
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.75 }}>
                  {t('detail.tabs.comm')}
                  {ccWorking && (
                    <Box
                      sx={{
                        width: 7,
                        height: 7,
                        borderRadius: '50%',
                        bgcolor: 'success.main',
                        flexShrink: 0,
                        animation: 'ccPulseDot 1.4s ease-in-out infinite',
                        '@keyframes ccPulseDot': {
                          '0%, 100%': { opacity: 1, transform: 'scale(1)' },
                          '50%': { opacity: 0.3, transform: 'scale(0.55)' },
                        },
                      }}
                    />
                  )}
                </Box>
              }
            />
            <Tab label={t('detail.tabs.memory')} />
            <Tab label={t('detail.tabs.extensions')} />
            <Tab label={t('detail.tabs.prompt')} />
            <Tab label={t('detail.tabs.config')} />
          </Tabs>
        </Card>
      </Box>

      {/* Tab 内容区 */}
      <Box
        sx={{
          flex: 1,
          minHeight: 0,
          overflow: activeTab === 1 || activeTab === 3 ? 'hidden' : 'auto',
          px: 2,
          py: 1.5,
          display: 'flex',
          flexDirection: 'column',
        }}
      >
        <motion.div
          key={activeTab}
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.25, ease: [0.4, 0, 0.2, 1] }}
          style={{
            flex: 1,
            display: 'flex',
            flexDirection: 'column',
            minHeight: 0,
            height: '100%',
          }}
        >
          {activeTab === 0 && (
            <OverviewTab
              workspace={workspace}
              sandboxStatus={effectiveSandboxStatus ?? null}
              onNavigateToSandbox={() => setActiveTab(1)}
              onNavigateToConfig={() => setActiveTab(6)}
              onNavigateToExtensions={() => setActiveTab(4)}
              onNavigateToComm={() => setActiveTab(2)}
            />
          )}
          {activeTab === 1 && (
            <SandboxTab
              workspace={workspace}
              sandboxStatus={effectiveSandboxStatus ?? null}
              onSandboxMutate={handleSandboxMutate}
              onNavigateToOverview={() => setActiveTab(0)}
            />
          )}
          {activeTab === 2 && (
            <Card sx={{ ...CARD_VARIANTS.default.styles, height: '100%', p: 0, overflow: 'hidden' }}>
              <CommTab workspace={workspace} prefill={commPrefill} ccRunning={ccWorking} />
            </Card>
          )}
          {activeTab === 3 && <MemoryTab workspace={workspace} />}
          {activeTab === 4 && <ExtensionsTab workspace={workspace} onNavigateToComm={handleNavigateToComm} />}
          {activeTab === 5 && <PromptTab workspace={workspace} />}
          {activeTab === 6 && (
            <ConfigTab workspace={workspace} onDeleted={() => navigate('/workspace')} />
          )}
        </motion.div>
      </Box>
    </Box>
  )
}
