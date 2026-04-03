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

import { forwardRef, useEffect, useRef, useState, useCallback, type ReactNode } from 'react'
import { useNavigate } from 'react-router-dom'
import { chatChannelPath, workspaceDetailPath } from '../../router/routes'
import { Box, Avatar, Tooltip, Typography, useTheme } from '@mui/material'
import {
  Autorenew as AutorenewIcon,
  Build as BuildIcon,
  CheckCircle as CheckCircleIcon,
  ErrorOutline as ErrorOutlineIcon,
  HourglassBottom as HourglassBottomIcon,
  RotateRight as RotateRightIcon,
  SmartToy as SmartToyIcon,
  StopCircle as StopCircleIcon,
  Terminal as TerminalIcon,
} from '@mui/icons-material'
import { motion, AnimatePresence } from 'framer-motion'
import { alpha } from '@mui/material/styles'
import { useQuery } from '@tanstack/react-query'
import { presetsApi } from '../../services/api/presets'
import {
  type AgentActiveInfo,
  type AgentRuntimeStatusInfo,
  type WorkspaceCcActiveInfo,
  type WorkspaceCcRuntimeStatusInfo,
  type WorkspaceStatusSnapshot,
} from '../../hooks/useSystemEvents'
import { BORDER_RADIUS } from '../../theme/variants'
import { useTranslation } from 'react-i18next'
import { getStopTypeColorValue, getStopTypeTranslatedText } from '../../theme/utils'

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
  info: AgentRuntimeStatusInfo
  isLeaving: boolean
  onNavigate: (chatKey: string) => void
  onDismiss: (key: string) => void
}

function getAgentPhaseAccentColor(info: AgentRuntimeStatusInfo, fallbackColor: string, errorColor: string, successColor: string): string {
  switch (info.phase) {
    case 'llm_generating':
      return fallbackColor
    case 'llm_retrying':
      return '#ffb300'
    case 'sandbox_running':
      return '#26a69a'
    case 'sandbox_stopped':
      return info.sandbox_stop_type != null ? getStopTypeColorValue(info.sandbox_stop_type) : '#9e9e9e'
    case 'iterating':
      return '#7e57c2'
    case 'completed':
      return successColor
    case 'failed':
      return errorColor
    default:
      return fallbackColor
  }
}

function getAgentPhaseLabel(
  info: AgentRuntimeStatusInfo,
  t: (key: string, options?: { ns?: string; [key: string]: unknown }) => string,
): string {
  switch (info.phase) {
    case 'llm_generating':
      return t('agentRuntime.phase.llmGenerating')
    case 'llm_retrying':
      return t('agentRuntime.phase.llmRetrying')
    case 'sandbox_running':
      return t('agentRuntime.phase.sandboxRunning')
    case 'sandbox_stopped':
      return t('agentRuntime.phase.sandboxStopped')
    case 'iterating':
      return t('agentRuntime.phase.iterating')
    case 'completed':
      return t('agentRuntime.phase.completed')
    case 'failed':
      return t('agentRuntime.phase.failed')
    default:
      return t('agentRuntime.phase.llmGenerating')
  }
}

function getWorkspacePhaseAccentColor(info: WorkspaceCcRuntimeStatusInfo, fallbackColor: string, errorColor: string, successColor: string): string {
  switch (info.phase) {
    case 'queued':
      return '#ffb300'
    case 'running':
      return fallbackColor
    case 'responding':
      return '#26a69a'
    case 'completed':
      return successColor
    case 'failed':
      return errorColor
    case 'cancelled':
      return '#9e9e9e'
    default:
      return fallbackColor
  }
}

function getWorkspacePhaseLabel(
  info: WorkspaceCcRuntimeStatusInfo,
  t: (key: string, options?: { ns?: string; [key: string]: unknown }) => string,
): string {
  switch (info.phase) {
    case 'queued':
      return t('workspaceActivity.phase.queued')
    case 'running':
      return t('workspaceActivity.phase.running')
    case 'responding':
      return t('workspaceActivity.phase.responding')
    case 'completed':
      return t('workspaceActivity.phase.completed')
    case 'failed':
      return t('workspaceActivity.phase.failed')
    case 'cancelled':
      return t('workspaceActivity.phase.cancelled')
    default:
      return t('workspaceActivity.phase.running')
  }
}

const AgentItem = forwardRef<HTMLDivElement, AgentItemProps>(function AgentItem(
  { info, isLeaving, onNavigate, onDismiss },
  ref
) {
  const theme = useTheme()
  const { t } = useTranslation(['layout-MainLayout', 'common'])
  const elapsed = useElapsedSeconds(info.started_at)

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
  const accentColor = getAgentPhaseAccentColor(
    info,
    theme.palette.primary.main,
    theme.palette.error.main,
    theme.palette.success.main,
  )
  const phaseLabel = getAgentPhaseLabel(info, (key, options) => t(key, options))
  const stopTypeLabel = info.sandbox_stop_type != null
    ? getStopTypeTranslatedText(info.sandbox_stop_type, (key, options) => t(key, options))
    : null
  const shouldPulse = !isLeaving && ['llm_generating', 'llm_retrying', 'sandbox_running', 'iterating'].includes(info.phase)

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
          <tr>
            <td style={{ paddingRight: 8, whiteSpace: 'nowrap', opacity: 0.7 }}>{t('agentRuntime.tooltipPhase')}</td>
            <td>{phaseLabel}</td>
          </tr>
          {stopTypeLabel && (
            <tr>
              <td style={{ paddingRight: 8, whiteSpace: 'nowrap', opacity: 0.7 }}>{t('agentRuntime.tooltipSandboxStop')}</td>
              <td>{stopTypeLabel}</td>
            </tr>
          )}
          {info.model_name && (
            <tr>
              <td style={{ paddingRight: 8, whiteSpace: 'nowrap', opacity: 0.7 }}>{t('agentRuntime.tooltipModel')}</td>
              <td>{info.model_name}</td>
            </tr>
          )}
          {info.llm_retry_total > 1 && (
            <tr>
              <td style={{ paddingRight: 8, whiteSpace: 'nowrap', opacity: 0.7 }}>{t('agentRuntime.tooltipRetry')}</td>
              <td>{info.llm_retry_index}/{info.llm_retry_total}</td>
            </tr>
          )}
          {info.iteration_total > 1 && (
            <tr>
              <td style={{ paddingRight: 8, whiteSpace: 'nowrap', opacity: 0.7 }}>{t('agentRuntime.tooltipIteration')}</td>
              <td>{info.iteration_index}/{info.iteration_total}</td>
            </tr>
          )}
        </tbody>
      </Box>
      {info.error_summary && (
        <Box sx={{ mt: 0.85 }}>
          <Typography variant="caption" sx={{ display: 'block', opacity: 0.7, fontSize: '0.68rem', mb: 0.3 }}>
            {t('agentRuntime.tooltipErrorSummary')}
          </Typography>
          <Typography variant="caption" sx={{ display: 'block', fontSize: '0.68rem', lineHeight: 1.45 }}>
            {info.error_summary}
          </Typography>
        </Box>
      )}
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
        sweepColor={info.phase === 'failed' ? theme.palette.error.main : theme.palette.success.main}
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
          {shouldPulse && <PingRing color={accentColor} />}
        </Box>
        <Box sx={{ minWidth: 0, maxWidth: 180 }}>
          <Typography
            variant="caption"
            noWrap
            sx={{
              display: 'block',
              fontWeight: 600,
              fontSize: '0.72rem',
              letterSpacing: '0.01em',
              color: isDark ? 'rgba(255,255,255,0.88)' : 'rgba(0,0,0,0.78)',
              lineHeight: 1,
              mb: 0.35,
            }}
          >
            {displayName}
          </Typography>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5, minWidth: 0 }}>
            {info.phase === 'llm_retrying' ? (
              <AutorenewIcon sx={{ fontSize: 12, color: accentColor, animation: 'spin 1.4s linear infinite', '@keyframes spin': { '100%': { transform: 'rotate(360deg)' } } }} />
            ) : info.phase === 'sandbox_running' ? (
              <TerminalIcon sx={{ fontSize: 12, color: accentColor }} />
            ) : info.phase === 'failed' ? (
              <ErrorOutlineIcon sx={{ fontSize: 12, color: accentColor }} />
            ) : info.phase === 'completed' ? (
              <CheckCircleIcon sx={{ fontSize: 12, color: accentColor }} />
            ) : (
              <SmartToyIcon sx={{ fontSize: 12, color: accentColor }} />
            )}
            <Typography
              variant="caption"
              noWrap
              sx={{
                minWidth: 0,
                color: accentColor,
                fontSize: '0.67rem',
                fontWeight: 700,
                letterSpacing: '0.01em',
              }}
            >
              {phaseLabel}
            </Typography>
            {stopTypeLabel && (
              <Typography
                variant="caption"
                noWrap
                sx={{ minWidth: 0, color: theme.palette.text.secondary, fontSize: '0.64rem', fontWeight: 600 }}
              >
                {stopTypeLabel}
              </Typography>
            )}
            {info.llm_retry_total > 1 && (
              <InlineIconCounter
                icon={<AutorenewIcon sx={{ fontSize: 11 }} />}
                color={theme.palette.warning.main}
                text={`${info.llm_retry_index}/${info.llm_retry_total}`}
              />
            )}
            {info.iteration_total > 1 && (
              <InlineIconCounter
                icon={<RotateRightIcon sx={{ fontSize: 11 }} />}
                color={theme.palette.secondary.main}
                text={`${info.iteration_index}/${info.iteration_total}`}
              />
            )}
          </Box>
        </Box>
      </BroadcastCard>
    </BroadcastMotionWrapper>
  )
})

// ── 工作区 CC 播报卡片 ────────────────────────────────────────────────────────

interface WorkspaceCcItemProps {
  workspaceId: number
  runtimeInfo: WorkspaceCcRuntimeStatusInfo
  snapshot: WorkspaceStatusSnapshot | undefined
  isLeaving: boolean
  onNavigate: (workspaceId: number) => void
  onDismiss: (key: string) => void
}

const WorkspaceCcItem = forwardRef<HTMLDivElement, WorkspaceCcItemProps>(function WorkspaceCcItem(
  { workspaceId, runtimeInfo, snapshot, isLeaving, onNavigate, onDismiss },
  ref
) {
  const theme = useTheme()
  const { t } = useTranslation('layout-MainLayout')
  const elapsed = useElapsedSeconds(runtimeInfo.started_at)

  const isDark = theme.palette.mode === 'dark'
  // 优先用 cc 事件里的名字，其次 workspace_status 快照，最后降级用 ID
  const displayName = runtimeInfo.name ?? snapshot?.name ?? `Workspace #${workspaceId}`
  const accentColor = getWorkspacePhaseAccentColor(
    runtimeInfo,
    theme.palette.warning.main,
    theme.palette.error.main,
    theme.palette.success.main,
  )
  const phaseLabel = getWorkspacePhaseLabel(runtimeInfo, (key, options) => t(key, options))
  const currentToolLabel = runtimeInfo.current_tool
  const RuntimeIcon = runtimeInfo.phase === 'queued'
    ? HourglassBottomIcon
    : runtimeInfo.phase === 'responding'
      ? AutorenewIcon
      : runtimeInfo.phase === 'completed'
        ? CheckCircleIcon
        : runtimeInfo.phase === 'failed'
          ? ErrorOutlineIcon
          : runtimeInfo.phase === 'cancelled'
            ? StopCircleIcon
            : TerminalIcon

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
          <tr>
            <td style={{ paddingRight: 8, whiteSpace: 'nowrap', opacity: 0.7 }}>{t('workspaceActivity.tooltipPhase')}</td>
            <td>{phaseLabel}</td>
          </tr>
          {runtimeInfo.current_tool && (
            <tr>
              <td style={{ paddingRight: 8, whiteSpace: 'nowrap', opacity: 0.7 }}>{t('workspaceActivity.tooltipTool')}</td>
              <td>{runtimeInfo.current_tool}</td>
            </tr>
          )}
          {runtimeInfo.last_block_summary && (
            <tr>
              <td style={{ paddingRight: 8, whiteSpace: 'nowrap', opacity: 0.7 }}>{t('workspaceActivity.tooltipBlockSummary')}</td>
              <td>{runtimeInfo.last_block_summary}</td>
            </tr>
          )}
          {runtimeInfo.operation_block_count > 0 && (
            <tr>
              <td style={{ paddingRight: 8, whiteSpace: 'nowrap', opacity: 0.7 }}>{t('workspaceActivity.tooltipBlockCount')}</td>
              <td>{runtimeInfo.operation_block_count}</td>
            </tr>
          )}
          {runtimeInfo.queue_length > 0 && (
            <tr>
              <td style={{ paddingRight: 8, whiteSpace: 'nowrap', opacity: 0.7 }}>{t('workspaceActivity.tooltipQueue')}</td>
              <td>{t('workspaceActivity.queueLength', { count: runtimeInfo.queue_length })}</td>
            </tr>
          )}
        </tbody>
      </Box>
      {runtimeInfo.error_summary && (
        <Typography variant="caption" sx={{ display: 'block', mt: 0.65, fontSize: '0.68rem', lineHeight: 1.45 }}>
          {runtimeInfo.error_summary}
        </Typography>
      )}
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
            <RuntimeIcon
              sx={{
                fontSize: 15,
                color: accentColor,
                animation: runtimeInfo.phase === 'responding' ? 'workspaceCardSpin 1.6s linear infinite' : 'none',
                '@keyframes workspaceCardSpin': { '100%': { transform: 'rotate(360deg)' } },
              }}
            />
          </Avatar>
          {!isLeaving && ['queued', 'running', 'responding'].includes(runtimeInfo.phase) && <PingRing color={accentColor} />}
        </Box>
        <Box sx={{ minWidth: 0, maxWidth: 180 }}>
          <Typography
            variant="caption"
            noWrap
            sx={{
              display: 'block',
              fontWeight: 600,
              fontSize: '0.72rem',
              letterSpacing: '0.01em',
              color: isDark ? 'rgba(255,255,255,0.88)' : 'rgba(0,0,0,0.78)',
              lineHeight: 1,
              mb: 0.35,
            }}
          >
            {displayName}
          </Typography>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5, minWidth: 0, mb: currentToolLabel ? 0.15 : 0 }}>
            <Typography
              variant="caption"
              noWrap
              sx={{ minWidth: 0, color: accentColor, fontSize: '0.67rem', fontWeight: 700, letterSpacing: '0.01em' }}
            >
              {phaseLabel}
            </Typography>
            {runtimeInfo.operation_block_count > 0 && (
              <InlineIconCounter
                icon={<BuildIcon sx={{ fontSize: 11 }} />}
                color={theme.palette.warning.main}
                text={String(runtimeInfo.operation_block_count)}
              />
            )}
          </Box>
          {currentToolLabel && (
            <Typography
              variant="caption"
              noWrap
              sx={{
                display: 'block',
                minWidth: 0,
                color: theme.palette.text.secondary,
                fontSize: '0.64rem',
                fontWeight: 600,
                lineHeight: 1.2,
              }}
            >
              {currentToolLabel}
            </Typography>
          )}
        </Box>
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

function InlineIconCounter({ icon, color, text }: { icon: ReactNode; color: string; text: string }) {
  return (
    <Box
      sx={{
        flexShrink: 0,
        display: 'inline-flex',
        alignItems: 'center',
        gap: 0.3,
        color,
      }}
    >
      {icon}
      <Typography variant="caption" sx={{ fontSize: '0.62rem', fontWeight: 700, lineHeight: 1 }}>
        {text}
      </Typography>
    </Box>
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
  agentRuntimeStatuses: Map<string, AgentRuntimeStatusInfo>
  workspaceStatuses: Map<number, WorkspaceStatusSnapshot>
  workspaceCcActive: Map<number, WorkspaceCcActiveInfo>
  workspaceCcRuntimeStatuses: Map<number, WorkspaceCcRuntimeStatusInfo>
}

/** 卡片相位：active（显示中）| leaving（消失动画） */
interface AgentCardPhase {
  phase: 'active' | 'leaving'
  runtimeInfo: AgentRuntimeStatusInfo
}

interface WorkspaceCardPhase {
  phase: 'active' | 'leaving'
  runtimeInfo: WorkspaceCcRuntimeStatusInfo
}

function buildFallbackRuntimeInfo(info: AgentActiveInfo): AgentRuntimeStatusInfo {
  return {
    chat_key: info.chat_key,
    channel_name: info.channel_name,
    chat_type: info.chat_type,
    preset_id: info.preset_id,
    preset_name: info.preset_name,
    started_at: info.started_at,
    updated_at: info.started_at,
    phase: 'llm_generating',
    iteration_index: 1,
    iteration_total: 1,
    llm_retry_index: 1,
    llm_retry_total: 1,
    sandbox_stop_type: null,
    model_name: null,
    error_summary: null,
  }
}

export default function AgentActivityCard({
  agentActives,
  agentRuntimeStatuses,
  workspaceStatuses,
  workspaceCcActive,
  workspaceCcRuntimeStatuses,
}: AgentActivityCardProps) {
  const navigate = useNavigate()

  // agent 卡片状态机
  const [agentCards, setAgentCards] = useState<Map<string, AgentCardPhase>>(new Map())
  const agentLingerTimers = useRef<Map<string, ReturnType<typeof setTimeout>>>(new Map())

  // workspace cc 卡片状态机
  const [wsCards, setWsCards] = useState<Map<number, WorkspaceCardPhase>>(new Map())
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
      const currentInfos = new Map<string, AgentRuntimeStatusInfo>()
      for (const [chatKey, info] of agentActives) {
        currentInfos.set(chatKey, agentRuntimeStatuses.get(chatKey) ?? buildFallbackRuntimeInfo(info))
      }
      for (const [chatKey, runtimeInfo] of agentRuntimeStatuses) {
        currentInfos.set(chatKey, runtimeInfo)
      }
      for (const [chatKey, runtimeInfo] of currentInfos) {
        const existing = next.get(chatKey)
        if (!existing) {
          next.set(chatKey, { phase: 'active', runtimeInfo })
          // 新条目进入时移除临时隐藏
          dismissedRef.current.delete(`agent:${chatKey}`)
        } else {
          next.set(chatKey, { phase: 'active', runtimeInfo })
        }
      }
      for (const [chatKey, card] of next) {
        if (!currentInfos.has(chatKey) && card.phase === 'active') {
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
  }, [agentActives, agentRuntimeStatuses])

  // 同步 workspaceCcActive / workspaceCcRuntimeStatuses → wsCards
  useEffect(() => {
    setWsCards(prev => {
      const next = new Map(prev)
      const currentInfos = new Map<number, WorkspaceCcRuntimeStatusInfo>()
      for (const [wsId, ccInfo] of workspaceCcActive) {
        currentInfos.set(wsId, {
          workspace_id: wsId,
          name: ccInfo.name,
          started_at: ccInfo.started_at,
          updated_at: ccInfo.started_at,
          phase: 'running',
        current_tool: null,
        source_chat_key: null,
        queue_length: 0,
        operation_block_count: 0,
        last_block_kind: null,
        last_block_summary: null,
        error_summary: null,
      })
      }
      for (const [wsId, runtimeInfo] of workspaceCcRuntimeStatuses) {
        currentInfos.set(wsId, runtimeInfo)
      }
      for (const [wsId, runtimeInfo] of currentInfos) {
        const existing = next.get(wsId)
        if (!existing) {
          next.set(wsId, { phase: 'active', runtimeInfo })
          // 新条目进入时移除临时隐藏
          dismissedRef.current.delete(`workspace:${wsId}`)
        } else {
          next.set(wsId, { phase: 'active', runtimeInfo })
        }
      }
      for (const [wsId, card] of next) {
        if (!currentInfos.has(wsId) && card.phase === 'active') {
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
  }, [workspaceCcActive, workspaceCcRuntimeStatuses])

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
    navigate(chatChannelPath(chatKey, 'message-history'))
  }, [navigate])

  const handleNavigateWorkspace = useCallback((wsId: number) => {
    navigate(workspaceDetailPath(wsId, 'comm'))
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
          return (
            <AgentItem
              key={`agent:${chatKey}`}
              info={card.runtimeInfo}
              isLeaving={card.phase === 'leaving'}
              onNavigate={handleNavigateAgent}
              onDismiss={handleDismiss}
            />
          )
        })}
        {visibleWsCards.map(([wsId, card]) => {
          const snapshot = workspaceStatuses.get(wsId)
          return (
            <WorkspaceCcItem
              key={`workspace:${wsId}`}
              workspaceId={wsId}
              runtimeInfo={card.runtimeInfo}
              snapshot={snapshot}
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
