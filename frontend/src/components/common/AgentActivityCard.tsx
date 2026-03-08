/**
 * AgentActivityCard — 全局活动播报组件（FPS 战斗播报风格）
 *
 * 播报内容：
 * 1. AI 响应活动（agent_active）：频道正在被 AI 处理，展示人设头像 + 频道名
 * 2. 工作区 CC 活跃（workspace_cc_active）：沙盒正在执行任务，展示工作区名
 *
 * 交互：
 * - 左键：跳转到对应页面
 * - 右键：临时隐藏该条目（刷新后恢复，不持久化）
 * - 悬浮：显示详细信息 tooltip
 *
 * 挂载位置：MainLayout 根节点（position: fixed，右下角）
 */

import { forwardRef, useEffect, useRef, useState, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { Box, Avatar, Tooltip, Typography, useTheme } from '@mui/material'
import { SmartToy as SmartToyIcon, Terminal as TerminalIcon } from '@mui/icons-material'
import { motion, AnimatePresence } from 'framer-motion'
import { alpha } from '@mui/material/styles'
import { useQuery } from '@tanstack/react-query'
import { presetsApi } from '../../services/api/presets'
import { type AgentActiveInfo, type WorkspaceCcActiveInfo, type WorkspaceStatusSnapshot } from '../../hooks/useSystemEvents'
import { BORDER_RADIUS } from '../../theme/variants'
import { useTranslation } from 'react-i18next'

// ── 常量 ─────────────────────────────────────────────────────────────────────

/** 卡片距底部间距（px） */
const BOTTOM_OFFSET = 24
/** 卡片右侧间距 */
const RIGHT_OFFSET = 16
/** 卡片入场/消失动画时长 */
const ANIM_DURATION = 0.28
/** 消失阶段：卡片在"已完成"态停留的时间 ms，之后才真正从 DOM 移除 */
const DONE_LINGER_MS = 1200

// ── 通用计时 hook ─────────────────────────────────────────────────────────────

function useElapsedSeconds(startTime: number) {
  const [elapsed, setElapsed] = useState(Math.floor((Date.now() - startTime) / 1000))
  useEffect(() => {
    const id = setInterval(() => {
      setElapsed(Math.floor((Date.now() - startTime) / 1000))
    }, 1000)
    return () => clearInterval(id)
  }, [startTime])
  return elapsed
}

// ── Agent 播报卡片 ────────────────────────────────────────────────────────────

interface AgentItemProps {
  info: AgentActiveInfo
  isLeaving: boolean
  onNavigate: (chatKey: string) => void
  onDismiss: (key: string) => void
}

const AgentItem = forwardRef<HTMLDivElement, AgentItemProps>(function AgentItem(
  { info, isLeaving, onNavigate, onDismiss },
  ref
) {
  const theme = useTheme()
  const { t } = useTranslation('layout-MainLayout')
  const elapsed = useElapsedSeconds(info.start_time)

  const { data: preset } = useQuery({
    queryKey: ['preset-detail', info.preset_id],
    queryFn: () => presetsApi.getDetail(info.preset_id!),
    enabled: info.preset_id != null,
    staleTime: 5 * 60 * 1000,
  })

  const displayName = info.channel_name || info.chat_key
  const presetTitle = preset?.title || preset?.name || info.preset_name || t('agentActivity.tooltipNoPreset')

  const chatTypeLabel = info.chat_type === 'group'
    ? t('agentActivity.tooltipTypeGroup')
    : info.chat_type === 'private'
      ? t('agentActivity.tooltipTypePrivate')
      : t('agentActivity.tooltipTypeUnknown')

  const isDark = theme.palette.mode === 'dark'
  const accentColor = theme.palette.primary.main

  const tooltipContent = (
    <Box sx={{ p: 0.25, minWidth: 160 }}>
      <Typography variant="caption" fontWeight={700} sx={{ display: 'block', mb: 0.5, fontSize: '0.75rem' }}>
        {displayName}
      </Typography>
      <Box component="table" sx={{ borderSpacing: '2px 1px', fontSize: '0.68rem', color: 'text.secondary' }}>
        <tbody>
          <tr>
            <td style={{ paddingRight: 8, whiteSpace: 'nowrap', opacity: 0.7 }}>{t('agentActivity.tooltipChatKey')}</td>
            <td style={{ fontFamily: 'monospace', opacity: 0.9 }}>{info.chat_key}</td>
          </tr>
          <tr>
            <td style={{ paddingRight: 8, whiteSpace: 'nowrap', opacity: 0.7 }}>{t('agentActivity.tooltipType')}</td>
            <td>{chatTypeLabel}</td>
          </tr>
          <tr>
            <td style={{ paddingRight: 8, whiteSpace: 'nowrap', opacity: 0.7 }}>{t('agentActivity.tooltipPreset')}</td>
            <td>{presetTitle}</td>
          </tr>
          <tr>
            <td style={{ paddingRight: 8, whiteSpace: 'nowrap', opacity: 0.7 }}>{t('agentActivity.tooltipElapsed')}</td>
            <td>{t('agentActivity.tooltipElapsedSec', { s: elapsed })}</td>
          </tr>
        </tbody>
      </Box>
      <Typography variant="caption" sx={{ display: 'block', mt: 0.75, opacity: 0.55, fontSize: '0.65rem' }}>
        {t('activity.dismissHint')}
      </Typography>
    </Box>
  )

  return (
    <BroadcastMotionWrapper ref={ref} isLeaving={isLeaving}>
      <BroadcastCard
        isLeaving={isLeaving}
        accentColor={accentColor}
        isDark={isDark}
        onClick={() => onNavigate(info.chat_key)}
        onDismiss={() => onDismiss(`agent:${info.chat_key}`)}
        sweepColor={theme.palette.success.main}
        tooltipContent={tooltipContent}
      >
        <Box sx={{ position: 'relative', flexShrink: 0 }}>
          <Avatar
            src={preset?.avatar || undefined}
            sx={{
              width: 28,
              height: 28,
              fontSize: 14,
              bgcolor: alpha(accentColor, isDark ? 0.25 : 0.15),
              border: `1.5px solid ${alpha(accentColor, isLeaving ? 0.3 : 0.5)}`,
              transition: 'border-color 0.3s ease',
            }}
          >
            <SmartToyIcon sx={{ fontSize: 15, color: accentColor }} />
          </Avatar>
          {!isLeaving && <PingRing color={accentColor} />}
        </Box>
        <Typography
          variant="caption"
          noWrap
          sx={{
            maxWidth: 120,
            fontWeight: 600,
            fontSize: '0.72rem',
            letterSpacing: '0.01em',
            color: isDark ? 'rgba(255,255,255,0.88)' : 'rgba(0,0,0,0.78)',
            lineHeight: 1,
          }}
        >
          {displayName}
        </Typography>
      </BroadcastCard>
    </BroadcastMotionWrapper>
  )
})

// ── 工作区 CC 播报卡片 ────────────────────────────────────────────────────────

interface WorkspaceCcItemProps {
  workspaceId: number
  ccInfo: WorkspaceCcActiveInfo
  snapshot: WorkspaceStatusSnapshot | undefined
  startTime: number
  isLeaving: boolean
  onNavigate: (workspaceId: number) => void
  onDismiss: (key: string) => void
}

const WorkspaceCcItem = forwardRef<HTMLDivElement, WorkspaceCcItemProps>(function WorkspaceCcItem(
  { workspaceId, ccInfo, snapshot, startTime, isLeaving, onNavigate, onDismiss },
  ref
) {
  const theme = useTheme()
  const { t } = useTranslation('layout-MainLayout')
  const elapsed = useElapsedSeconds(startTime)

  const isDark = theme.palette.mode === 'dark'
  // 优先用 cc 事件里的名字，其次 workspace_status 快照，最后降级用 ID
  const displayName = ccInfo.name ?? snapshot?.name ?? `Workspace #${workspaceId}`
  const accentColor = theme.palette.warning.main

  const tooltipContent = (
    <Box sx={{ p: 0.25, minWidth: 160 }}>
      <Typography variant="caption" fontWeight={700} sx={{ display: 'block', mb: 0.5, fontSize: '0.75rem' }}>
        {displayName}
      </Typography>
      <Box component="table" sx={{ borderSpacing: '2px 1px', fontSize: '0.68rem', color: 'text.secondary' }}>
        <tbody>
          <tr>
            <td style={{ paddingRight: 8, whiteSpace: 'nowrap', opacity: 0.7 }}>{t('workspaceActivity.tooltipId')}</td>
            <td style={{ fontFamily: 'monospace', opacity: 0.9 }}>{workspaceId}</td>
          </tr>
          {snapshot?.container_name && (
            <tr>
              <td style={{ paddingRight: 8, whiteSpace: 'nowrap', opacity: 0.7 }}>{t('workspaceActivity.tooltipContainer')}</td>
              <td style={{ fontFamily: 'monospace', opacity: 0.9, maxWidth: 120, overflow: 'hidden', textOverflow: 'ellipsis' }}>
                {snapshot.container_name}
              </td>
            </tr>
          )}
          <tr>
            <td style={{ paddingRight: 8, whiteSpace: 'nowrap', opacity: 0.7 }}>{t('agentActivity.tooltipElapsed')}</td>
            <td>{t('agentActivity.tooltipElapsedSec', { s: elapsed })}</td>
          </tr>
        </tbody>
      </Box>
      <Typography variant="caption" sx={{ display: 'block', mt: 0.75, opacity: 0.55, fontSize: '0.65rem' }}>
        {t('activity.dismissHint')}
      </Typography>
    </Box>
  )

  return (
    <BroadcastMotionWrapper ref={ref} isLeaving={isLeaving}>
      <BroadcastCard
        isLeaving={isLeaving}
        accentColor={accentColor}
        isDark={isDark}
        onClick={() => onNavigate(workspaceId)}
        onDismiss={() => onDismiss(`workspace:${workspaceId}`)}
        sweepColor={accentColor}
        tooltipContent={tooltipContent}
      >
        <Box sx={{ position: 'relative', flexShrink: 0 }}>
          <Avatar
            sx={{
              width: 28,
              height: 28,
              fontSize: 14,
              bgcolor: alpha(accentColor, isDark ? 0.25 : 0.15),
              border: `1.5px solid ${alpha(accentColor, isLeaving ? 0.3 : 0.5)}`,
              transition: 'border-color 0.3s ease',
            }}
          >
            <TerminalIcon sx={{ fontSize: 15, color: accentColor }} />
          </Avatar>
          {!isLeaving && <PingRing color={accentColor} />}
        </Box>
        <Typography
          variant="caption"
          noWrap
          sx={{
            maxWidth: 120,
            fontWeight: 600,
            fontSize: '0.72rem',
            letterSpacing: '0.01em',
            color: isDark ? 'rgba(255,255,255,0.88)' : 'rgba(0,0,0,0.78)',
            lineHeight: 1,
          }}
        >
          {displayName}
        </Typography>
      </BroadcastCard>
    </BroadcastMotionWrapper>
  )
})

// ── 共用子组件 ────────────────────────────────────────────────────────────────

function PingRing({ color }: { color: string }) {
  return (
    <Box
      sx={{
        position: 'absolute',
        inset: 0,
        borderRadius: '50%',
        border: `1.5px solid ${alpha(color, 0.6)}`,
        animation: 'agentPing 1.5s cubic-bezier(0,0,0.2,1) infinite',
        '@keyframes agentPing': {
          '0%': { transform: 'scale(1)', opacity: 0.7 },
          '100%': { transform: 'scale(1.9)', opacity: 0 },
        },
      }}
    />
  )
}

const BroadcastMotionWrapper = forwardRef<
  HTMLDivElement,
  { isLeaving: boolean; children: React.ReactNode }
>(function BroadcastMotionWrapper({ isLeaving, children }, ref) {
  return (
    <motion.div
      ref={ref}
      layout
      initial={{ opacity: 0, x: 48, scale: 0.92 }}
      animate={isLeaving
        ? { opacity: 0, x: 32, scale: 0.88, filter: 'blur(2px)' }
        : { opacity: 1, x: 0, scale: 1, filter: 'blur(0px)' }
      }
      exit={{ opacity: 0, x: 32, scale: 0.88, filter: 'blur(2px)' }}
      transition={{
        duration: isLeaving ? ANIM_DURATION * 0.8 : ANIM_DURATION,
        ease: isLeaving ? [0.4, 0, 1, 1] : [0, 0, 0.2, 1],
        layout: { duration: 0.2 },
      }}
      style={{ pointerEvents: isLeaving ? 'none' : 'auto' }}
    >
      {children}
    </motion.div>
  )
})


interface BroadcastCardProps {
  isLeaving: boolean
  accentColor: string
  isDark: boolean
  onClick: () => void
  onDismiss: () => void
  sweepColor: string
  tooltipContent: React.ReactNode
  children: React.ReactNode
}

function BroadcastCard({ isLeaving, accentColor, isDark, onClick, onDismiss, sweepColor, tooltipContent, children }: BroadcastCardProps) {
  const handleContextMenu = useCallback((e: React.MouseEvent) => {
    e.preventDefault()
    onDismiss()
  }, [onDismiss])

  return (
    <Tooltip
      title={tooltipContent}
      placement="left"
      arrow
      componentsProps={{
        tooltip: {
          sx: {
            maxWidth: 260,
            backdropFilter: 'blur(12px)',
            backgroundColor: isDark ? 'rgba(30, 30, 35, 0.92)' : 'rgba(255, 255, 255, 0.92)',
            border: `1px solid ${isDark ? 'rgba(255,255,255,0.1)' : 'rgba(0,0,0,0.08)'}`,
            borderRadius: BORDER_RADIUS.DEFAULT,
            boxShadow: isDark ? '0 8px 24px rgba(0,0,0,0.5)' : '0 8px 24px rgba(0,0,0,0.15)',
            color: isDark ? 'rgba(255,255,255,0.9)' : 'rgba(0,0,0,0.85)',
            p: 1,
          },
        },
        arrow: {
          sx: { color: isDark ? 'rgba(30, 30, 35, 0.92)' : 'rgba(255, 255, 255, 0.92)' },
        },
      }}
    >
      <Box
        onClick={onClick}
        onContextMenu={handleContextMenu}
        sx={{
          display: 'flex',
          alignItems: 'center',
          gap: 1,
          pl: 0.75,
          pr: 1.5,
          py: 0.6,
          mb: 0.75,
          cursor: 'pointer',
          borderRadius: BORDER_RADIUS.PILL,
          backdropFilter: 'blur(16px)',
          WebkitBackdropFilter: 'blur(16px)',
          backgroundColor: isDark ? 'rgba(30, 32, 38, 0.82)' : 'rgba(255, 255, 255, 0.82)',
          border: `1px solid ${isDark ? 'rgba(255,255,255,0.10)' : 'rgba(0,0,0,0.08)'}`,
          boxShadow: isDark
            ? `0 2px 12px rgba(0,0,0,0.45), 0 0 0 1px ${alpha(accentColor, 0.15)}`
            : `0 2px 12px rgba(0,0,0,0.12), 0 0 0 1px ${alpha(accentColor, 0.12)}`,
          transition: 'all 0.15s ease',
          userSelect: 'none',
          position: 'relative',
          overflow: 'hidden',
          '&:hover': {
            backgroundColor: isDark ? 'rgba(40, 42, 52, 0.92)' : 'rgba(255, 255, 255, 0.95)',
            boxShadow: isDark
              ? `0 4px 20px rgba(0,0,0,0.55), 0 0 0 1px ${alpha(accentColor, 0.3)}`
              : `0 4px 20px rgba(0,0,0,0.18), 0 0 0 1px ${alpha(accentColor, 0.25)}`,
            transform: 'translateX(-2px)',
          },
        }}
      >
        {children}
        {isLeaving && (
          <Box
            sx={{
              position: 'absolute',
              inset: 0,
              borderRadius: 'inherit',
              background: `linear-gradient(90deg, transparent 0%, ${alpha(sweepColor, 0.25)} 50%, transparent 100%)`,
              backgroundSize: '200% 100%',
              animation: 'leaveSweep 0.5s ease-out forwards',
              '@keyframes leaveSweep': {
                '0%': { backgroundPosition: '-100% 0' },
                '100%': { backgroundPosition: '200% 0' },
              },
              pointerEvents: 'none',
            }}
          />
        )}
      </Box>
    </Tooltip>
  )
}

// ── 主组件 ────────────────────────────────────────────────────────────────────

interface AgentActivityCardProps {
  agentActives: Map<string, AgentActiveInfo>
  workspaceStatuses: Map<number, WorkspaceStatusSnapshot>
  workspaceCcActive: Map<number, WorkspaceCcActiveInfo>
}

/** 卡片相位：active（显示中）| leaving（消失动画） */
interface CardPhase {
  phase: 'active' | 'leaving'
  startTime: number
}

export default function AgentActivityCard({ agentActives, workspaceStatuses, workspaceCcActive }: AgentActivityCardProps) {
  const navigate = useNavigate()

  // agent 卡片状态机
  const [agentCards, setAgentCards] = useState<Map<string, CardPhase>>(new Map())
  const agentLingerTimers = useRef<Map<string, ReturnType<typeof setTimeout>>>(new Map())

  // workspace cc 卡片状态机
  const [wsCards, setWsCards] = useState<Map<number, CardPhase>>(new Map())
  const wsLingerTimers = useRef<Map<number, ReturnType<typeof setTimeout>>>(new Map())

  // 右键临时隐藏集合（key 格式：'agent:{chat_key}' | 'workspace:{id}'）
  // 使用 useRef 避免触发重渲，在需要用时读取
  const dismissedRef = useRef<Set<string>>(new Set())
  // 用一个 flag state 触发重渲（Set 变更不触发渲染）
  const [dismissVersion, setDismissVersion] = useState(0)

  const handleDismiss = useCallback((key: string) => {
    dismissedRef.current.add(key)
    setDismissVersion(v => v + 1)
  }, [])

  // 同步 agentActives → agentCards
  useEffect(() => {
    setAgentCards(prev => {
      const next = new Map(prev)
      for (const [chatKey, info] of agentActives) {
        if (!next.has(chatKey)) {
          next.set(chatKey, { phase: 'active', startTime: info.start_time })
          // 新条目进入时移除临时隐藏
          dismissedRef.current.delete(`agent:${chatKey}`)
        }
      }
      for (const [chatKey, card] of next) {
        if (!agentActives.has(chatKey) && card.phase === 'active') {
          next.set(chatKey, { ...card, phase: 'leaving' })
          const prevTimer = agentLingerTimers.current.get(chatKey)
          if (prevTimer) clearTimeout(prevTimer)
          const timer = setTimeout(() => {
            setAgentCards(c => { const m = new Map(c); m.delete(chatKey); return m })
            agentLingerTimers.current.delete(chatKey)
          }, DONE_LINGER_MS)
          agentLingerTimers.current.set(chatKey, timer)
        }
      }
      return next
    })
  }, [agentActives])

  // 同步 workspaceCcActive → wsCards
  useEffect(() => {
    setWsCards(prev => {
      const next = new Map(prev)
      for (const [wsId, ccInfo] of workspaceCcActive) {
        if (ccInfo.active && !next.has(wsId)) {
          next.set(wsId, { phase: 'active', startTime: Date.now() })
          // 新条目进入时移除临时隐藏
          dismissedRef.current.delete(`workspace:${wsId}`)
        }
        if (!ccInfo.active && next.has(wsId) && next.get(wsId)!.phase === 'active') {
          const card = next.get(wsId)!
          next.set(wsId, { ...card, phase: 'leaving' })
          const prevTimer = wsLingerTimers.current.get(wsId)
          if (prevTimer) clearTimeout(prevTimer)
          const timer = setTimeout(() => {
            setWsCards(c => { const m = new Map(c); m.delete(wsId); return m })
            wsLingerTimers.current.delete(wsId)
          }, DONE_LINGER_MS)
          wsLingerTimers.current.set(wsId, timer)
        }
      }
      return next
    })
  }, [workspaceCcActive])

  // 清理 timers
  useEffect(() => {
    const aRef = agentLingerTimers.current
    const wRef = wsLingerTimers.current
    return () => {
      for (const t of aRef.values()) clearTimeout(t)
      aRef.clear()
      for (const t of wRef.values()) clearTimeout(t)
      wRef.clear()
    }
  }, [])

  const handleNavigateAgent = useCallback((chatKey: string) => {
    navigate(`/chat-channel?chat_key=${encodeURIComponent(chatKey)}`)
  }, [navigate])

  const handleNavigateWorkspace = useCallback((wsId: number) => {
    navigate(`/workspace/${wsId}?tab=comm`)
  }, [navigate])

  // 过滤被临时隐藏的条目（dismissVersion 作为依赖触发重算）
  const visibleAgentCards = [...agentCards.entries()].filter(
    ([chatKey]) => !dismissedRef.current.has(`agent:${chatKey}`)
  )
  const visibleWsCards = [...wsCards.entries()].filter(
    ([wsId]) => !dismissedRef.current.has(`workspace:${wsId}`)
  )

  // dismissVersion 仅用于触发重渲，此处消费以避免 lint 未使用警告
  void dismissVersion

  if (visibleAgentCards.length === 0 && visibleWsCards.length === 0) return null

  return (
    <Box
      sx={{
        position: 'fixed',
        bottom: BOTTOM_OFFSET,
        right: RIGHT_OFFSET,
        zIndex: theme => theme.zIndex.drawer,
        display: 'flex',
        flexDirection: 'column-reverse',
        alignItems: 'flex-end',
        pointerEvents: 'none',
        '& > *': { pointerEvents: 'auto' },
      }}
    >
      <AnimatePresence mode="popLayout">
        {visibleAgentCards.map(([chatKey, card]) => {
          const info = agentActives.get(chatKey)
          if (!info) return null
          return (
            <AgentItem
              key={`agent:${chatKey}`}
              info={info}
              isLeaving={card.phase === 'leaving'}
              onNavigate={handleNavigateAgent}
              onDismiss={handleDismiss}
            />
          )
        })}
        {visibleWsCards.map(([wsId, card]) => {
          const snapshot = workspaceStatuses.get(wsId)
          const ccInfo = workspaceCcActive.get(wsId) ?? { active: false, name: null }
          return (
            <WorkspaceCcItem
              key={`workspace:${wsId}`}
              workspaceId={wsId}
              ccInfo={ccInfo}
              snapshot={snapshot}
              startTime={card.startTime}
              isLeaving={card.phase === 'leaving'}
              onNavigate={handleNavigateWorkspace}
              onDismiss={handleDismiss}
            />
          )
        })}
      </AnimatePresence>
    </Box>
  )
}
