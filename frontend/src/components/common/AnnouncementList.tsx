import { useCallback } from 'react'
import {
  Box,
  Typography,
  Divider,
  CircularProgress,
  Chip,
  alpha,
} from '@mui/material'
import { PushPin as PushPinIcon, Campaign as CampaignIcon } from '@mui/icons-material'
import { useTranslation } from 'react-i18next'
import type { AnnouncementSummary, AnnouncementType } from '../../services/api/cloud/announcement'
import { ANNOUNCEMENT_TYPE_COLORS, ANNOUNCEMENT_TYPE_LABELS, formatRelativeTime } from './AnnouncementConstants'
import { BORDER_RADIUS } from '../../theme/variants'

interface AnnouncementListProps {
  items: AnnouncementSummary[]
  loading: boolean
  readIds: string[]
  onAnnouncementClick: (id: string) => void
}

function EmptyState({ icon, text }: { icon: React.ReactNode; text: string }) {
  return (
    <Box
      sx={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        py: 5,
        gap: 1.5,
        color: 'text.disabled',
      }}
    >
      {icon}
      <Typography variant="body2" color="text.disabled">
        {text}
      </Typography>
    </Box>
  )
}

export default function AnnouncementList({
  items,
  loading,
  readIds,
  onAnnouncementClick,
}: AnnouncementListProps) {
  const { t, i18n } = useTranslation('layout-MainLayout')

  const getTypeLabel = useCallback(
    (type: AnnouncementType) => {
      const lang = i18n.language === 'en-US' ? 'en-US' : 'zh-CN'
      return ANNOUNCEMENT_TYPE_LABELS[lang]?.[type] ?? type
    },
    [i18n.language]
  )

  if (loading && items.length === 0) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', py: 5 }}>
        <CircularProgress size={24} />
      </Box>
    )
  }

  if (items.length === 0) {
    return (
      <EmptyState
        icon={<CampaignIcon sx={{ fontSize: 36 }} />}
        text={t('community.noNotifications')}
      />
    )
  }

  return (
    <>
      {items.map((item, index) => {
        const isRead = readIds.includes(item.id)
        const isHighPriority = item.priority >= 2
        const isImportant = item.priority >= 1

        return (
          <Box key={item.id}>
            <Box
              onClick={() => onAnnouncementClick(item.id)}
              sx={{
                position: 'relative',
                px: 2,
                py: 1.25,
                display: 'flex',
                alignItems: 'flex-start',
                gap: 1,
                cursor: 'pointer',
                opacity: isRead ? 0.65 : 1,
                transition: 'all 0.2s ease',
                borderRadius: BORDER_RADIUS.SMALL,
                margin: '0.5px',
                backgroundColor: isHighPriority ? alpha('#f44336', 0.03) : 'transparent',
                '&:hover': {
                  backgroundColor: alpha('#1976d2', isHighPriority ? 0.12 : 0.08),
                  opacity: 1,
                  transform: 'translateX(2px)',
                },
                // 高优先级左边框
                ...(isHighPriority && {
                  borderLeft: `3px solid #f44336`,
                  paddingLeft: '1.5rem',
                }),
              }}
            >
              {/* 未读指示点 / 置顶图标 */}
              <Box
                sx={{
                  width: 16,
                  flexShrink: 0,
                  pt: 0.5,
                  display: 'flex',
                  justifyContent: 'center',
                  ...(isHighPriority && {
                    ml: -0.5,
                  }),
                }}
              >
                {!isRead ? (
                  <Box
                    sx={{
                      width: 8,
                      height: 8,
                      borderRadius: '50%',
                      bgcolor: isHighPriority ? '#f44336' : '#1976d2',
                      boxShadow: `0 0 0 2px ${alpha(isHighPriority ? '#f44336' : '#1976d2', 0.2)}`,
                      transition: 'all 0.3s ease',
                    }}
                  />
                ) : item.isPinned ? (
                  <PushPinIcon
                    sx={{
                      fontSize: 14,
                      color: '#ff9800',
                      transform: 'rotate(45deg)',
                      opacity: 0.7,
                    }}
                  />
                ) : null}
              </Box>

              {/* 内容区 */}
              <Box sx={{ flex: 1, minWidth: 0, display: 'flex', gap: 1, alignItems: 'center' }}>
                {/* 左侧：标题 */}
                <Box sx={{ flex: 1, minWidth: 0 }}>
                  <Typography
                    variant="body2"
                    sx={{
                      fontWeight: isImportant ? 800 : 600,
                      fontSize: isImportant ? '0.84rem' : '0.82rem',
                      lineHeight: 1.5,
                      color: isRead ? 'text.secondary' : 'text.primary',
                      transition: 'color 0.2s ease',
                    }}
                  >
                    {item.title}
                  </Typography>
                </Box>

                {/* 右侧：Chip（上）和时间（下） */}
                <Box
                  sx={{
                    display: 'flex',
                    flexDirection: 'column',
                    alignItems: 'flex-end',
                    gap: 0.75,
                    flexShrink: 0,
                  }}
                >
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                    <Chip
                      label={getTypeLabel(item.type)}
                      size="small"
                      sx={{
                        height: 20,
                        fontSize: '0.65rem',
                        fontWeight: 700,
                        bgcolor: alpha(ANNOUNCEMENT_TYPE_COLORS[item.type] ?? '#999', 0.25),
                        color: ANNOUNCEMENT_TYPE_COLORS[item.type] ?? '#999',
                        border: `1px solid ${alpha(ANNOUNCEMENT_TYPE_COLORS[item.type] ?? '#999', 0.4)}`,
                        '& .MuiChip-label': { px: 0.75, letterSpacing: '0.3px' },
                        transition: 'all 0.2s ease',
                        '&:hover': {
                          bgcolor: alpha(ANNOUNCEMENT_TYPE_COLORS[item.type] ?? '#999', 0.35),
                          borderColor: ANNOUNCEMENT_TYPE_COLORS[item.type] ?? '#999',
                        },
                      }}
                    />
                  </Box>
                  <Typography
                    variant="caption"
                    sx={{
                      fontSize: '0.67rem',
                      color: isRead ? 'text.disabled' : 'text.secondary',
                      transition: 'color 0.2s ease',
                      fontWeight: 500,
                    }}
                  >
                    {formatRelativeTime(item.createdAt, i18n.language)}
                  </Typography>
                </Box>
              </Box>
            </Box>
            {index < items.length - 1 && (
              <Divider
                sx={{
                  mx: 1.5,
                  my: 0,
                  opacity: 0.5,
                  transition: 'opacity 0.2s ease',
                }}
              />
            )}
          </Box>
        )
      })}
    </>
  )
}
