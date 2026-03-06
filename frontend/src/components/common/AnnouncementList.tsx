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
import { getCurrentExtendedPalette } from '../../theme/themeConfig'

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
  const palette = getCurrentExtendedPalette()

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
        return (
          <Box key={item.id}>
            <Box
              onClick={() => onAnnouncementClick(item.id)}
              sx={{
                px: 2,
                py: 1.25,
                display: 'flex',
                alignItems: 'flex-start',
                gap: 1,
                cursor: 'pointer',
                opacity: isRead ? 0.6 : 1,
                transition: 'background-color 0.15s ease, opacity 0.2s ease',
                '&:hover': {
                  backgroundColor: alpha(palette.primary.main, 0.06),
                  opacity: 1,
                },
              }}
            >
              {/* 未读指示点 / 置顶图标 */}
              <Box sx={{ width: 16, flexShrink: 0, pt: 0.5, display: 'flex', justifyContent: 'center' }}>
                {!isRead ? (
                  <Box
                    sx={{
                      width: 7,
                      height: 7,
                      borderRadius: '50%',
                      bgcolor: 'primary.main',
                    }}
                  />
                ) : item.isPinned ? (
                  <PushPinIcon
                    sx={{ fontSize: 13, color: 'warning.main', transform: 'rotate(45deg)' }}
                  />
                ) : null}
              </Box>

              {/* 内容区 */}
              <Box sx={{ flex: 1, minWidth: 0, display: 'flex', gap: 1 }}>
                {/* 左侧：标题 */}
                <Box sx={{ flex: 1, minWidth: 0 }}>
                  <Typography
                    variant="body2"
                    sx={{
                      fontWeight: item.priority >= 1 ? 600 : 400,
                      fontSize: '0.82rem',
                      lineHeight: 1.4,
                    }}
                  >
                    {item.title}
                  </Typography>
                </Box>

                {/* 右侧：Chip（上）和时间（下） */}
                <Box sx={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: 0.5, flexShrink: 0 }}>
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                    <Chip
                      label={getTypeLabel(item.type)}
                      size="small"
                      sx={{
                        height: 18,
                        fontSize: '0.65rem',
                        fontWeight: 600,
                        bgcolor: alpha(ANNOUNCEMENT_TYPE_COLORS[item.type] ?? '#999', 0.15),
                        color: ANNOUNCEMENT_TYPE_COLORS[item.type] ?? '#999',
                        '& .MuiChip-label': { px: 0.75 },
                      }}
                    />
                    {item.priority >= 2 && (
                      <Box
                        sx={{
                          width: 6,
                          height: 6,
                          borderRadius: '50%',
                          bgcolor: 'error.main',
                          flexShrink: 0,
                        }}
                      />
                    )}
                  </Box>
                  <Typography
                    variant="caption"
                    color="text.disabled"
                    sx={{ fontSize: '0.68rem' }}
                  >
                    {formatRelativeTime(item.createdAt)}
                  </Typography>
                </Box>
              </Box>
            </Box>
            {index < items.length - 1 && <Divider sx={{ mx: 2 }} />}
          </Box>
        )
      })}
    </>
  )
}
