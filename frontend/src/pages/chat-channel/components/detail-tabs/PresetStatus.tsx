import { useEffect, useRef, useState } from 'react'
import { Box, Typography, Stack, Paper, useTheme, Tooltip } from '@mui/material'
import {
  Timeline,
  TimelineItem,
  TimelineSeparator,
  TimelineConnector,
  TimelineContent,
  TimelineDot,
} from '@mui/lab'
import {
  LocalOffer as TagIcon,
  AccessTime as TimeIcon,
  Timer as DurationIcon,
} from '@mui/icons-material'
import { ChatChannelDetail } from '../../../../services/api/chat-channel'
import { formatLastActiveTime } from '../../../../utils/time'
import { alpha } from '@mui/material/styles'
import { PresetNote } from '../../../../types/chat'

interface PresetStatusProps {
  channel: ChatChannelDetail
}

// 自定义 hook 用于处理效果的剩余时间
function useEffectRemainingTime(expireTime: number) {
  const [remainingTime, setRemainingTime] = useState<number>(0)
  const [isExpired, setIsExpired] = useState<boolean>(false)

  useEffect(() => {
    if (expireTime === 0) return

    const calculateRemainingTime = () => {
      const now = Math.floor(Date.now() / 1000)
      const remaining = expireTime - now

      setRemainingTime(Math.max(0, remaining))
      setIsExpired(remaining <= 0)
    }

    calculateRemainingTime()
    const timer = setInterval(calculateRemainingTime, 1000)

    return () => clearInterval(timer)
  }, [expireTime])

  const formatRemainingTime = (seconds: number): string => {
    if (seconds === 0) return '已过期'

    const days = Math.floor(seconds / 86400)
    const hours = Math.floor((seconds % 86400) / 3600)
    const minutes = Math.floor((seconds % 3600) / 60)
    const remainingSeconds = seconds % 60

    const parts: string[] = []
    if (days > 0) parts.push(`${days}天`)
    if (hours > 0) parts.push(`${hours}小时`)
    if (minutes > 0) parts.push(`${minutes}分钟`)
    if (remainingSeconds > 0 && days === 0 && hours === 0) parts.push(`${remainingSeconds}秒`)

    return parts.join('')
  }

  return {
    remainingTime,
    isExpired,
    formattedTime: formatRemainingTime(remainingTime),
  }
}

// 状态笔记卡片组件
function NoteCard({ note: note }: { note: PresetNote }) {
  const { isExpired, formattedTime } = useEffectRemainingTime(note.expire_time)

  return (
    <Paper
      variant="outlined"
      sx={{
        height: 140,
        p: 2.5,
        pb: 1.5,
        position: 'relative',
        display: 'flex',
        flexDirection: 'column',
        bgcolor: theme =>
          theme.palette.mode === 'dark'
            ? alpha(theme.palette.background.paper, 0.1)
            : alpha(theme.palette.background.paper, 0.7),
        borderColor: theme => {
          return theme.palette.mode === 'dark'
            ? alpha(theme.palette.divider, 0.3)
            : alpha(theme.palette.divider, 0.1)
        },
        opacity: note.expire_time > 0 && isExpired ? 0.6 : 1,
      }}
    >
      <Tooltip title={note.title} placement="top">
        <div className="flex items-center gap-2 mb-2">
          <TagIcon sx={{ fontSize: '1.25rem', color: 'primary.main' }} />
          <Typography
            variant="subtitle2"
            sx={{
              fontWeight: 500,
              flex: 1,
              overflow: 'hidden',
              textOverflow: 'ellipsis',
              whiteSpace: 'nowrap',
            }}
          >
            {note.title}
          </Typography>
          {note.expire_time === 0 ? (
            <Typography variant="caption" sx={{ color: 'success.main' }}>
              永久
            </Typography>
          ) : isExpired ? (
            <Typography variant="caption" sx={{ color: 'text.disabled' }}>
              已过期
            </Typography>
          ) : null}
        </div>
      </Tooltip>
      <Tooltip title={note.description} placement="top">
        <Typography
          variant="body2"
          sx={{
            color: 'text.secondary',
            display: '-webkit-box',
            WebkitLineClamp: 3,
            WebkitBoxOrient: 'vertical',
            overflow: 'hidden',
            flex: '1 1 auto',
            mb: 2,
            lineHeight: 1.6,
            cursor: 'pointer',
          }}
        >
          {note.description}
        </Typography>
      </Tooltip>
      <div className="flex items-center justify-between mt-auto">
        <div className="flex items-center gap-1">
          <TimeIcon sx={{ fontSize: '0.875rem', color: 'primary.main' }} />
          <Typography variant="caption" sx={{ color: 'text.disabled' }}>
            {formatLastActiveTime(note.start_time)}
          </Typography>
        </div>
        {note.expire_time > 0 && !isExpired && (
          <div className="flex items-center gap-1">
            <DurationIcon sx={{ fontSize: '0.875rem', color: 'primary.main' }} />
            <Typography variant="caption" sx={{ color: 'text.disabled' }}>
              {formattedTime}
            </Typography>
          </div>
        )}
      </div>
    </Paper>
  )
}

export default function PresetStatus({ channel }: PresetStatusProps) {
  const theme = useTheme()
  const containerRef = useRef<HTMLDivElement>(null)
  const bottomRef = useRef<HTMLDivElement>(null)

  // 自动滚动到底部
  useEffect(() => {
    if (bottomRef.current) {
      bottomRef.current.scrollIntoView({ behavior: 'auto' })
    }
  }, [])

  // 如果 channel 是 undefined，显示加载状态
  if (!channel) {
    return (
      <Box className="h-full flex items-center justify-center">
        <Typography color="textSecondary">加载中...</Typography>
      </Box>
    )
  }

  return (
    <Box className="h-full flex flex-col overflow-hidden">
      <Box ref={containerRef} className="flex-1 overflow-auto">
        {/* 状态时间线 */}
        <Box className="p-4 pb-0">
          <Typography variant="subtitle1" className="mb-4 font-medium text-black dark:text-gray-50">
            状态时间线
          </Typography>
          <Timeline
            sx={{
              p: 0,
              m: 0,
              [`& .MuiTimelineItem-root`]: {
                minHeight: 0,
                '&:before': {
                  display: 'none',
                },
              },
              [`& .MuiTimelineContent-root`]: {
                p: 0,
                pl: 2,
                m: 0,
              },
              [`& .MuiTimelineSeparator-root`]: {
                py: 0.5,
              },
            }}
          >
            {(channel.preset_status_list || []).map((status, index, array) => {
              const isCurrentStatus = index === array.length - 1
              const isExpired = index < array.length - channel.max_preset_status_refer_size
              return (
                <TimelineItem key={index}>
                  <TimelineSeparator>
                    <TimelineDot
                      className={`${isExpired ? 'opacity-50' : ''} shadow-sm`}
                      sx={{
                        backgroundColor: isCurrentStatus
                          ? theme.palette.success.main
                          : theme.palette.primary.main,
                        p: 0.5,
                      }}
                    />
                    {index < array.length - 1 && (
                      <TimelineConnector
                        className={isExpired ? 'opacity-50' : ''}
                        sx={{
                          backgroundColor: theme.palette.primary.main,
                          opacity: 0.3,
                        }}
                      />
                    )}
                  </TimelineSeparator>
                  <TimelineContent>
                    <Paper
                      variant="outlined"
                      className={`
                        w-full p-3 mb-4 transition-all duration-200 shadow-sm
                        ${isExpired ? 'opacity-50' : ''}
                        ${
                          isCurrentStatus
                            ? 'border-success-300 dark:border-success-700 bg-success-50/50 dark:bg-success-900/10'
                            : 'border-primary-200 dark:border-primary-700 hover:bg-primary-50/50 dark:hover:bg-primary-900/10'
                        }
                      `}
                      sx={{
                        backgroundColor:
                          theme.palette.mode === 'dark'
                            ? 'rgba(255, 255, 255, 0.03)'
                            : 'rgba(0, 0, 0, 0.01)',
                      }}
                    >
                      <Stack spacing={1}>
                        <div className="flex items-center gap-2">
                          <Typography variant="body1" className="font-medium">
                            {status.setting_name}
                          </Typography>
                          {isCurrentStatus && (
                            <Typography
                              component="span"
                              variant="caption"
                              className="text-success-600 dark:text-success-400"
                            >
                              (当前)
                            </Typography>
                          )}
                        </div>
                        <Typography variant="body2" className="text-gray-600 dark:text-gray-400">
                          {status.description}
                        </Typography>
                        <Typography variant="caption" className="text-gray-500 dark:text-gray-500">
                          更新于 {formatLastActiveTime(status.translated_timestamp)}
                        </Typography>
                      </Stack>
                    </Paper>
                  </TimelineContent>
                </TimelineItem>
              )
            })}
          </Timeline>
        </Box>

        <Box className="mb-6" />

        {/* 状态笔记列表 */}
        <Box className="px-4 pb-4">
          <Typography
            variant="subtitle1"
            className="mb-4 font-medium"
            sx={{
              color: theme => (theme.palette.mode === 'dark' ? 'text.primary' : 'text.primary'),
            }}
          >
            状态笔记列表
          </Typography>
          {(channel.preset_notes || []).length > 0 ? (
            <div className="grid grid-cols-2 gap-4">
              {(channel.preset_notes || []).map((note, index) => (
                <NoteCard key={index} note={note} />
              ))}
            </div>
          ) : (
            <Typography sx={{ color: 'text.disabled' }}>暂无状态笔记</Typography>
          )}
        </Box>
        <div ref={bottomRef} />
      </Box>
    </Box>
  )
}
