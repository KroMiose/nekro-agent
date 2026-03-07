import { useState, useEffect, useCallback } from 'react'
import { Box, IconButton, Avatar, Tooltip, Badge, Popover, alpha } from '@mui/material'
import { Person as PersonIcon } from '@mui/icons-material'
import { useCommunityUserStore } from '../../stores/communityUser'
import { useAnnouncementStore } from '../../stores/announcement'
import { getCurrentThemeMode, getCurrentExtendedPalette } from '../../theme/themeConfig'
import { BORDER_RADIUS } from '../../theme/variants'
import { useTranslation } from 'react-i18next'
import AnnouncementDetailDialog from './AnnouncementDetailDialog'
import { LoggedInContent, NotConfiguredContent } from './CommunityAvatarContent'

export default function CommunityAvatar() {
  const { userInfo, loading: userLoading, fetchUserProfile } = useCommunityUserStore()
  const {
    items: announcements,
    loading: announcementLoading,
    readIds,
    currentDetail,
    detailLoading,
    fetchLatest,
    fetchDetail,
    markAllAsRead,
    clearDetail,
    unreadCount,
    checkForUpdates,
  } = useAnnouncementStore()
  const [anchorEl, setAnchorEl] = useState<null | HTMLElement>(null)
  const [activeTab, setActiveTab] = useState(0)
  const [detailOpen, setDetailOpen] = useState(false)
  const open = Boolean(anchorEl)
  const themeMode = getCurrentThemeMode()
  const palette = getCurrentExtendedPalette()
  const { t } = useTranslation('layout-MainLayout')

  const badgeCount = unreadCount()

  useEffect(() => {
    fetchUserProfile()
  }, [fetchUserProfile])

  // 组件挂载时检查公告更新，之后每 5 分钟定时检查
  useEffect(() => {
    checkForUpdates()
    const timer = setInterval(checkForUpdates, 5 * 60 * 1000)
    return () => clearInterval(timer)
  }, [checkForUpdates])

  useEffect(() => {
    if (userInfo && open) {
      fetchLatest(true)
    }
  }, [userInfo, open, fetchLatest])

  const handleClick = (event: React.MouseEvent<HTMLElement>) => {
    setAnchorEl(event.currentTarget)
  }

  const handleClose = () => {
    setAnchorEl(null)
  }

  const handleRefresh = useCallback(() => {
    fetchUserProfile(true)
    fetchLatest(true)
  }, [fetchUserProfile, fetchLatest])

  const handleAnnouncementClick = useCallback(
    (id: string) => {
      fetchDetail(id)
      setDetailOpen(true)
    },
    [fetchDetail]
  )

  const handleDetailClose = useCallback(() => {
    setDetailOpen(false)
    clearDetail()
  }, [clearDetail])

  const popoverPaperStyles = {
    mt: 1,
    width: 340,
    maxHeight: 480,
    backgroundColor:
      themeMode === 'dark' ? 'rgba(35, 35, 40, 0.95)' : 'rgba(255, 255, 255, 0.95)',
    backdropFilter: 'blur(20px)',
    WebkitBackdropFilter: 'blur(20px)',
    borderRadius: BORDER_RADIUS.LARGE,
    border: `1px solid ${themeMode === 'dark' ? 'rgba(255, 255, 255, 0.1)' : 'rgba(0, 0, 0, 0.08)'}`,
    boxShadow:
      themeMode === 'dark' ? '0 8px 32px rgba(0, 0, 0, 0.4)' : '0 8px 32px rgba(0, 0, 0, 0.12)',
    display: 'flex',
    flexDirection: 'column',
  }

  return (
    <Box>
      <Tooltip title={t('community.avatarTooltip')} arrow>
        <IconButton
          onClick={handleClick}
          size="small"
          sx={{
            ml: 1,
            p: 0.3,
            transition: 'transform 0.2s ease',
            '&:hover': {
              transform: 'scale(1.08)',
            },
          }}
        >
          <Badge
            badgeContent={badgeCount || undefined}
            color="error"
            max={9}
            sx={{
              '& .MuiBadge-badge': {
                fontSize: '0.6rem',
                height: 16,
                minWidth: 16,
                right: 2,
                top: 2,
              },
            }}
          >
            <Avatar
              src={userInfo?.avatarUrl}
              sx={{
                width: 28,
                height: 28,
                border: '2px solid rgba(255, 255, 255, 0.7)',
                bgcolor: userInfo ? 'transparent' : alpha(palette.primary.main, 0.3),
                fontSize: 16,
              }}
            >
              {!userInfo && <PersonIcon sx={{ fontSize: 18 }} />}
            </Avatar>
          </Badge>
        </IconButton>
      </Tooltip>

      <Popover
        open={open}
        anchorEl={anchorEl}
        onClose={handleClose}
        transformOrigin={{ horizontal: 'right', vertical: 'top' }}
        anchorOrigin={{ horizontal: 'right', vertical: 'bottom' }}
        slotProps={{ paper: { sx: popoverPaperStyles } }}
      >
        {userInfo ? (
          <LoggedInContent
            userInfo={userInfo}
            userLoading={userLoading}
            announcements={announcements}
            announcementLoading={announcementLoading}
            readIds={readIds}
            badgeCount={badgeCount}
            activeTab={activeTab}
            onTabChange={setActiveTab}
            onRefresh={handleRefresh}
            onAnnouncementClick={handleAnnouncementClick}
            onMarkAllRead={markAllAsRead}
            onClose={() => {
              handleClose()
            }}
          />
        ) : (
          <NotConfiguredContent onClose={handleClose} />
        )}
      </Popover>

      <AnnouncementDetailDialog
        open={detailOpen}
        detail={currentDetail}
        loading={detailLoading}
        onClose={handleDetailClose}
      />
    </Box>
  )
}
