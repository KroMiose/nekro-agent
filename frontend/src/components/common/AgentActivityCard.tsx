/**
 * AgentActivityCard — AI 响应活动全局播报组件
 *
 * 设计风格：FPS 游戏右上角战斗播报
 * - 每个活跃频道以独立卡片形式从右侧滑入
 * - 展示人设头像 + 频道名 + 脉动指示
 * - 任务完成后播放消失动画，然后自动移除
 * - 悬浮显示详细信息（频道 ID、类型、人设、已处理时长）
 * - 点击跳转到聊天频道页面并自动选中该频道
 *
 * 挂载位置：MainLayout 根节点（position: fixed，右上角，AppBar 正下方）
 */

import { useEffect, useRef, useState, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { Box, Avatar, Tooltip, Typography, useTheme } from '@mui/material'
import { SmartToy as SmartToyIcon } from '@mui/icons-material'
import { motion, AnimatePresence } from 'framer-motion'
import { alpha } from '@mui/material/styles'
import { useQuery } from '@tanstack/react-query'
import { presetsApi } from '../../services/api/presets'
import { type AgentActiveInfo } from '../../hooks/useSystemEvents'
import { BORDER_RADIUS } from '../../theme/variants'
import { useTranslation } from 'react-i18next'

// ── 常量 ─────────────────────────────────────────────────────────────────────

/** 卡片距底部间距（px） */
const BOTTOM_OFFSET = 24
/** 卡片右侧间距 */
const RIGHT_OFFSET = 16
/** 卡片入场/消失动画时长 ms */
const ANIM_DURATION = 0.28
/** 消失阶段：卡片在"已完成"态停留的时间 ms，之后才真正从 DOM 移除 */
const DONE_LINGER_MS = 1200

// ── 单条播报卡片 ──────────────────────────────────────────────────────────────

interface ActivityItemProps {
  info: AgentActiveInfo
  isLeaving: boolean
  onNavigate: (chatKey: string) => void
}

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

function ActivityItem({ info, isLeaving, onNavigate }: ActivityItemProps) {
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
        {t('agentActivity.tooltipClickHint')}
      </Typography>
    </Box>
  )

  return (
    <motion.div
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
      <Tooltip
        title={tooltipContent}
        placement="left"
        arrow
        componentsProps={{
          tooltip: {
            sx: {
              maxWidth: 260,
              backdropFilter: 'blur(12px)',
              backgroundColor: isDark
                ? 'rgba(30, 30, 35, 0.92)'
                : 'rgba(255, 255, 255, 0.92)',
              border: `1px solid ${isDark ? 'rgba(255,255,255,0.1)' : 'rgba(0,0,0,0.08)'}`,
              borderRadius: BORDER_RADIUS.DEFAULT,
              boxShadow: isDark
                ? '0 8px 24px rgba(0,0,0,0.5)'
                : '0 8px 24px rgba(0,0,0,0.15)',
              color: isDark ? 'rgba(255,255,255,0.9)' : 'rgba(0,0,0,0.85)',
              p: 1,
            },
          },
          arrow: {
            sx: {
              color: isDark ? 'rgba(30, 30, 35, 0.92)' : 'rgba(255, 255, 255, 0.92)',
            },
          },
        }}
      >
        <Box
          onClick={() => onNavigate(info.chat_key)}
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
            backgroundColor: isDark
              ? 'rgba(30, 32, 38, 0.82)'
              : 'rgba(255, 255, 255, 0.82)',
            border: `1px solid ${isDark
              ? `rgba(255,255,255,0.10)`
              : `rgba(0,0,0,0.08)`}`,
            boxShadow: isDark
              ? `0 2px 12px rgba(0,0,0,0.45), 0 0 0 1px ${alpha(theme.palette.primary.main, 0.15)}`
              : `0 2px 12px rgba(0,0,0,0.12), 0 0 0 1px ${alpha(theme.palette.primary.main, 0.12)}`,
            transition: 'all 0.15s ease',
            userSelect: 'none',
            '&:hover': {
              backgroundColor: isDark
                ? 'rgba(40, 42, 52, 0.92)'
                : 'rgba(255, 255, 255, 0.95)',
              boxShadow: isDark
                ? `0 4px 20px rgba(0,0,0,0.55), 0 0 0 1px ${alpha(theme.palette.primary.main, 0.3)}`
                : `0 4px 20px rgba(0,0,0,0.18), 0 0 0 1px ${alpha(theme.palette.primary.main, 0.25)}`,
              transform: 'translateX(-2px)',
            },
          }}
        >
          {/* 人设头像 */}
          <Box sx={{ position: 'relative', flexShrink: 0 }}>
            <Avatar
              src={preset?.avatar || undefined}
              sx={{
                width: 28,
                height: 28,
                fontSize: 14,
                bgcolor: alpha(theme.palette.primary.main, isDark ? 0.25 : 0.15),
                border: `1.5px solid ${alpha(theme.palette.primary.main, isLeaving ? 0.3 : 0.5)}`,
                transition: 'border-color 0.3s ease',
              }}
            >
              <SmartToyIcon sx={{ fontSize: 15, color: theme.palette.primary.main }} />
            </Avatar>
            {/* 脉动圆圈 —— CSS 动画，active 时显示，leaving 时隐藏 */}
            {!isLeaving && (
              <Box
                sx={{
                  position: 'absolute',
                  inset: 0,
                  borderRadius: '50%',
                  border: `1.5px solid ${alpha(theme.palette.primary.main, 0.6)}`,
                  animation: 'agentPing 1.5s cubic-bezier(0,0,0.2,1) infinite',
                  '@keyframes agentPing': {
                    '0%': { transform: 'scale(1)', opacity: 0.7 },
                    '100%': { transform: 'scale(1.9)', opacity: 0 },
                  },
                }}
              />
            )}
          </Box>

          {/* 频道名 */}
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

          {/* 完成态扫光线 */}
          {isLeaving && (
            <Box
              sx={{
                position: 'absolute',
                inset: 0,
                borderRadius: 'inherit',
                background: `linear-gradient(90deg, transparent 0%, ${alpha(theme.palette.success.main, 0.25)} 50%, transparent 100%)`,
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
    </motion.div>
  )
}

// ── 主组件 ────────────────────────────────────────────────────────────────────

interface AgentActivityCardProps {
  agentActives: Map<string, AgentActiveInfo>
}

/** 追踪卡片状态：active（显示中）| leaving（消失动画）*/
interface CardState {
  info: AgentActiveInfo
  phase: 'active' | 'leaving'
}

export default function AgentActivityCard({ agentActives }: AgentActivityCardProps) {
  const navigate = useNavigate()
  const [cards, setCards] = useState<Map<string, CardState>>(new Map())
  const lingerTimers = useRef<Map<string, ReturnType<typeof setTimeout>>>(new Map())

  // 同步 agentActives → cards 状态机
  useEffect(() => {
    setCards(prev => {
      const next = new Map(prev)

      // 新增 / 保留已有 active
      for (const [chatKey, info] of agentActives) {
        if (!next.has(chatKey)) {
          next.set(chatKey, { info, phase: 'active' })
        }
      }

      // 已从 agentActives 移除的条目 → 进入 leaving 阶段
      for (const [chatKey, card] of next) {
        if (!agentActives.has(chatKey) && card.phase === 'active') {
          next.set(chatKey, { ...card, phase: 'leaving' })

          // 消失动画播完后，从 DOM 移除
          const prev_timer = lingerTimers.current.get(chatKey)
          if (prev_timer) clearTimeout(prev_timer)
          const timer = setTimeout(() => {
            setCards(c => { const m = new Map(c); m.delete(chatKey); return m })
            lingerTimers.current.delete(chatKey)
          }, DONE_LINGER_MS)
          lingerTimers.current.set(chatKey, timer)
        }
      }

      return next
    })
  }, [agentActives])

  // 清理 linger timers
  useEffect(() => {
    const ref = lingerTimers.current
    return () => {
      for (const t of ref.values()) clearTimeout(t)
      ref.clear()
    }
  }, [])

  const handleNavigate = useCallback((chatKey: string) => {
    navigate(`/chat-channel?chat_key=${encodeURIComponent(chatKey)}`)
  }, [navigate])

  if (cards.size === 0) return null

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
        {[...cards.entries()].map(([chatKey, card]) => (
          <ActivityItem
            key={chatKey}
            info={card.info}
            isLeaving={card.phase === 'leaving'}
            onNavigate={handleNavigate}
          />
        ))}
      </AnimatePresence>
    </Box>
  )
}
