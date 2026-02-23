import { useState, useEffect, useCallback, useRef } from 'react'
import {
  Box,
  Card,
  CircularProgress,
  Alert,
  Tabs,
  Tab,
} from '@mui/material'
import { useQuery } from '@tanstack/react-query'
import { useNavigate, useParams } from 'react-router-dom'
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

// Components
import WorkspaceHeader from './components/WorkspaceHeader'

// Tabs
import OverviewTab from './tabs/OverviewTab'
import SandboxTab from './tabs/SandboxTab'
import CommTab from './tabs/CommTab'
import MemoryTab from './tabs/MemoryTab'
import ExtensionsTab from './tabs/ExtensionsTab'
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
  const [activeTab, setActiveTab] = useState(0)
  const [commPrefill, setCommPrefill] = useState('')

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

  const { data: sandboxStatus } = useQuery({
    queryKey: ['sandbox-status', workspaceId],
    queryFn: () => workspaceApi.getSandboxStatus(workspaceId),
    enabled: !isNaN(workspaceId) && !!workspace,
    refetchInterval: query =>
      fastPoll
        ? 2000
        : query.state.data?.status === 'active' || workspace?.status === 'active'
          ? 5000
          : 10000,
  })

  // ── CC 工作状态跟踪（SSE 实时 + 历史初始化） ─────────────────────
  const [ccWorking, setCcWorking] = useState(false)
  const [ccCurrentTool, setCcCurrentTool] = useState<string | null>(null)

  // 初始化：从历史记录判断当前是否有任务进行中
  useEffect(() => {
    if (!workspace) return
    commApi.getHistory(workspaceId, 30).then(r => {
      const items = r.items
      let lastNaIdx = -1
      for (let i = items.length - 1; i >= 0; i--) {
        if (items[i].direction === 'NA_TO_CC') { lastNaIdx = i; break }
      }
      if (lastNaIdx >= 0) {
        let hasCcReply = false
        for (let i = lastNaIdx + 1; i < items.length; i++) {
          if (items[i].direction === 'CC_TO_NA') { hasCcReply = true; break }
        }
        if (!hasCcReply) {
          setCcWorking(true)
          // 查找最新 TOOL_CALL
          for (let i = items.length - 1; i > lastNaIdx; i--) {
            if (items[i].direction === 'TOOL_CALL') {
              try { setCcCurrentTool(JSON.parse(items[i].content).name ?? null) } catch { /* */ }
              break
            }
          }
        }
      }
    }).catch(() => { /* ignore */ })
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [workspaceId, workspace?.id])

  // 实时追踪
  useEffect(() => {
    if (!workspace) return
    return streamCommLog(workspaceId, entry => {
      if (entry.direction === 'NA_TO_CC') {
        setCcWorking(true)
        setCcCurrentTool(null)
      } else if (entry.direction === 'CC_TO_NA') {
        setCcWorking(false)
        setCcCurrentTool(null)
      } else if (entry.direction === 'TOOL_CALL') {
        try { setCcCurrentTool(JSON.parse(entry.content).name ?? null) } catch { /* */ }
      } else if (entry.direction === 'TOOL_RESULT') {
        setCcCurrentTool(null)
      }
    })
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
        sandboxStatus={sandboxStatus}
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
              sandboxStatus={sandboxStatus ?? null}
              onNavigateToSandbox={() => setActiveTab(1)}
              onNavigateToConfig={() => setActiveTab(5)}
              onNavigateToExtensions={() => setActiveTab(4)}
              onNavigateToComm={() => setActiveTab(2)}
            />
          )}
          {activeTab === 1 && (
            <SandboxTab
              workspace={workspace}
              sandboxStatus={sandboxStatus ?? null}
              onSandboxMutate={handleSandboxMutate}
            />
          )}
          {activeTab === 2 && <CommTab workspace={workspace} prefill={commPrefill} />}
          {activeTab === 3 && <MemoryTab workspace={workspace} />}
          {activeTab === 4 && <ExtensionsTab workspace={workspace} onNavigateToComm={handleNavigateToComm} />}
          {activeTab === 5 && (
            <ConfigTab workspace={workspace} onDeleted={() => navigate('/workspace')} />
          )}
        </motion.div>
      </Box>
    </Box>
  )
}
