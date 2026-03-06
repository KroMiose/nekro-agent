import { useState, useEffect, useCallback } from 'react'
import {
  IconButton,
  Avatar,
  Tooltip,
  Box,
  Typography,
  Divider,
  Popover,
  Tabs,
  Tab,
  Badge,
  Chip,
  CircularProgress,
  Dialog,
  DialogTitle,
  DialogContent,
  alpha,
} from '@mui/material'
import {
  Person as PersonIcon,
  OpenInNew as OpenInNewIcon,
  Refresh as RefreshIcon,
  Settings as SettingsIcon,
  VpnKey as VpnKeyIcon,
  Campaign as CampaignIcon,
  Email as EmailIcon,
  PushPin as PushPinIcon,
  DoneAll as DoneAllIcon,
  Close as CloseIcon,
} from '@mui/icons-material'
import { useNavigate } from 'react-router-dom'
import { useCommunityUserStore } from '../../stores/communityUser'
import { useAnnouncementStore } from '../../stores/announcement'
import { getCurrentThemeMode, getCurrentExtendedPalette } from '../../theme/themeConfig'
import { BORDER_RADIUS } from '../../theme/variants'
import { useTranslation } from 'react-i18next'
import MarkdownRenderer from './MarkdownRenderer'
import type { AnnouncementType } from '../../services/api/cloud/announcement'

// 消息项类型（后续接入 API 时使用）
export interface MessageItem {
  id: string
  title: string
  content: string
  time: string
  read: boolean
}

// 公告类型配色
const ANNOUNCEMENT_TYPE_COLORS: Record<AnnouncementType, string> = {
  notice: '#2196f3',
  update: '#4caf50',
  maintenance: '#ff9800',
  event: '#9c27b0',
}

const ANNOUNCEMENT_TYPE_LABELS: Record<string, Record<AnnouncementType, string>> = {
  'zh-CN': { notice: '通知', update: '更新', maintenance: '维护', event: '活动' },
  'en-US': { notice: 'Notice', update: 'Update', maintenance: 'Maint', event: 'Event' },
}

function formatRelativeTime(isoString: string): string {
  const diff = Math.floor((Date.now() - new Date(isoString).getTime()) / 1000)
  if (diff < 60) return '刚刚'
  if (diff < 3600) return `${Math.floor(diff / 60)}分钟前`
  if (diff < 86400) return `${Math.floor(diff / 3600)}小时前`
  if (diff < 2592000) return `${Math.floor(diff / 86400)}天前`
  return `${Math.floor(diff / 2592000)}月前`
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
  const { t, i18n } = useTranslation('layout-MainLayout')
  const navigate = useNavigate()

  const messages: MessageItem[] = []
  const badgeCount = unreadCount()

  useEffect(() => {
    fetchUserProfile()
  }, [fetchUserProfile])

  // 组件挂载时检查公告更新，之后每 30 分钟定时检查
  useEffect(() => {
    checkForUpdates()
    const timer = setInterval(checkForUpdates, 30 * 60 * 1000)
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

  const getTypeLabel = useCallback(
    (type: AnnouncementType) => {
      const lang = i18n.language === 'en-US' ? 'en-US' : 'zh-CN'
      return ANNOUNCEMENT_TYPE_LABELS[lang]?.[type] ?? type
    },
    [i18n.language]
  )

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

  const footerBtnStyles = {
    display: 'flex',
    alignItems: 'center',
    gap: 0.75,
    px: 1.5,
    py: 0.75,
    borderRadius: BORDER_RADIUS.SMALL,
    cursor: 'pointer',
    fontSize: '0.75rem',
    color: 'text.secondary',
    transition: 'background-color 0.15s ease',
    '&:hover': {
      backgroundColor: alpha(palette.primary.main, 0.08),
      color: palette.primary.main,
    },
  }

  const renderAnnouncementList = () => {
    if (announcementLoading && announcements.length === 0) {
      return (
        <Box sx={{ display: 'flex', justifyContent: 'center', py: 5 }}>
          <CircularProgress size={24} />
        </Box>
      )
    }

    if (announcements.length === 0) {
      return (
        <EmptyState
          icon={<CampaignIcon sx={{ fontSize: 36 }} />}
          text={t('community.noNotifications')}
        />
      )
    }

    return announcements.map((item, index) => {
      const isRead = readIds.includes(item.id)
      return (
        <Box key={item.id}>
          <Box
            onClick={() => handleAnnouncementClick(item.id)}
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
            <Box sx={{ flex: 1, minWidth: 0 }}>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.75, mb: 0.25 }}>
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
                variant="body2"
                noWrap
                sx={{
                  fontWeight: item.priority >= 1 ? 600 : 400,
                  fontSize: '0.82rem',
                  lineHeight: 1.4,
                }}
              >
                {item.title}
              </Typography>
            </Box>

            {/* 时间 */}
            <Typography
              variant="caption"
              color="text.disabled"
              sx={{ flexShrink: 0, fontSize: '0.68rem', pt: 0.25 }}
            >
              {formatRelativeTime(item.createdAt)}
            </Typography>
          </Box>
          {index < announcements.length - 1 && <Divider sx={{ mx: 2 }} />}
        </Box>
      )
    })
  }

  const renderLoggedInContent = () => (
    <>
      {/* 用户信息头部 */}
      <Box sx={{ px: 2, py: 1.5, display: 'flex', alignItems: 'center', gap: 1.5 }}>
        <Avatar src={userInfo!.avatarUrl} sx={{ width: 36, height: 36 }} />
        <Box sx={{ flex: 1, minWidth: 0 }}>
          <Typography variant="subtitle2" sx={{ fontWeight: 600 }} noWrap>
            {userInfo!.username}
          </Typography>
          {userInfo!.email && (
            <Typography variant="caption" color="text.secondary" noWrap sx={{ display: 'block' }}>
              {userInfo!.email}
            </Typography>
          )}
        </Box>
        <Tooltip title={t('community.refreshProfile')} arrow>
          <IconButton size="small" onClick={handleRefresh} disabled={userLoading} sx={{ flexShrink: 0 }}>
            <RefreshIcon sx={{ fontSize: 18 }} />
          </IconButton>
        </Tooltip>
      </Box>

      <Divider />

      {/* Tab 栏 + 一键已读 */}
      <Box sx={{ display: 'flex', alignItems: 'center' }}>
        <Tabs
          value={activeTab}
          onChange={(_, v: number) => setActiveTab(v)}
          sx={{
            flex: 1,
            minHeight: 40,
            '& .MuiTab-root': {
              minHeight: 40,
              fontSize: '0.8rem',
              fontWeight: 600,
              textTransform: 'none',
              transition: 'color 0.2s ease',
            },
            '& .MuiTabs-indicator': {
              height: 2,
              borderRadius: '1px',
            },
          }}
        >
          <Tab
            icon={
              <Badge badgeContent={badgeCount || undefined} color="error" max={99}>
                <CampaignIcon sx={{ fontSize: 16 }} />
              </Badge>
            }
            iconPosition="start"
            label={t('community.tabNotifications')}
            sx={{ gap: 0.5 }}
          />
          <Tab
            icon={
              <Badge badgeContent={messages.length || undefined} color="primary" max={99}>
                <EmailIcon sx={{ fontSize: 16 }} />
              </Badge>
            }
            iconPosition="start"
            label={t('community.tabMessages')}
            sx={{ gap: 0.5 }}
          />
        </Tabs>
        {activeTab === 0 && badgeCount > 0 && (
          <Tooltip title={t('community.markAllRead')} arrow>
            <IconButton
              size="small"
              onClick={markAllAsRead}
              sx={{ mr: 1, color: 'text.secondary' }}
            >
              <DoneAllIcon sx={{ fontSize: 16 }} />
            </IconButton>
          </Tooltip>
        )}
      </Box>

      {/* 内容区 */}
      <Box sx={{ flex: 1, minHeight: 160, maxHeight: 300, overflow: 'auto' }}>
        {activeTab === 0 && renderAnnouncementList()}
        {activeTab === 1 && (
          <EmptyState
            icon={<EmailIcon sx={{ fontSize: 36 }} />}
            text={t('community.noMessages')}
          />
        )}
      </Box>

      <Divider />

      {/* 底部操作栏 */}
      <Box sx={{ display: 'flex', justifyContent: 'center', px: 1, py: 0.75, gap: 0.5 }}>
        <Box
          sx={footerBtnStyles}
          onClick={() => {
            window.open('https://community.nekro.ai', '_blank')
            handleClose()
          }}
        >
          <OpenInNewIcon sx={{ fontSize: 14 }} />
          {t('community.visitCommunity')}
        </Box>
        <Box
          sx={footerBtnStyles}
          onClick={() => {
            navigate('/settings')
            handleClose()
          }}
        >
          <SettingsIcon sx={{ fontSize: 14 }} />
          {t('community.goToSettings')}
        </Box>
      </Box>
    </>
  )

  const renderNotConfiguredContent = () => (
    <Box sx={{ p: 2.5, textAlign: 'center' }}>
      <Avatar
        sx={{
          width: 48,
          height: 48,
          mx: 'auto',
          mb: 1.5,
          bgcolor: alpha(palette.primary.main, 0.15),
          color: palette.primary.main,
        }}
      >
        <PersonIcon sx={{ fontSize: 28 }} />
      </Avatar>
      <Typography variant="subtitle2" sx={{ fontWeight: 600, mb: 0.5 }}>
        {t('community.notConfiguredTitle')}
      </Typography>
      <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mb: 2 }}>
        {t('community.notConfiguredDesc')}
      </Typography>
      <Box sx={{ display: 'flex', flexDirection: 'column', gap: 0.5 }}>
        <Box
          sx={{
            ...footerBtnStyles,
            justifyContent: 'center',
            py: 1,
            border: `1px solid ${alpha(palette.primary.main, 0.3)}`,
            color: palette.primary.main,
            fontWeight: 600,
          }}
          onClick={() => {
            window.open('https://community.nekro.ai', '_blank')
            handleClose()
          }}
        >
          <VpnKeyIcon sx={{ fontSize: 16 }} />
          {t('community.getCommunityKey')}
        </Box>
        <Box
          sx={{ ...footerBtnStyles, justifyContent: 'center', py: 1 }}
          onClick={() => {
            navigate('/settings')
            handleClose()
          }}
        >
          <SettingsIcon sx={{ fontSize: 16 }} />
          {t('community.goToSettings')}
        </Box>
      </Box>
    </Box>
  )

  const renderDetailDialog = () => (
    <Dialog
      open={detailOpen}
      onClose={handleDetailClose}
      maxWidth="sm"
      fullWidth
      PaperProps={{
        sx: {
          borderRadius: BORDER_RADIUS.LARGE,
          backgroundColor:
            themeMode === 'dark' ? 'rgba(35, 35, 40, 0.98)' : 'rgba(255, 255, 255, 0.98)',
          backdropFilter: 'blur(20px)',
          maxHeight: '70vh',
        },
      }}
    >
      {detailLoading ? (
        <Box sx={{ display: 'flex', justifyContent: 'center', py: 6 }}>
          <CircularProgress size={32} />
        </Box>
      ) : currentDetail ? (
        <>
          <DialogTitle sx={{ display: 'flex', alignItems: 'flex-start', gap: 1, pr: 6 }}>
            <Box sx={{ flex: 1 }}>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 0.75 }}>
                <Chip
                  label={getTypeLabel(currentDetail.type as AnnouncementType)}
                  size="small"
                  sx={{
                    height: 20,
                    fontSize: '0.7rem',
                    fontWeight: 600,
                    bgcolor: alpha(
                      ANNOUNCEMENT_TYPE_COLORS[currentDetail.type as AnnouncementType] ?? '#999',
                      0.15
                    ),
                    color:
                      ANNOUNCEMENT_TYPE_COLORS[currentDetail.type as AnnouncementType] ?? '#999',
                  }}
                />
                <Typography variant="caption" color="text.secondary">
                  {currentDetail.authorName} · {formatRelativeTime(currentDetail.createdAt)}
                </Typography>
              </Box>
              <Typography variant="h6" sx={{ fontWeight: 600, fontSize: '1.1rem', lineHeight: 1.4 }}>
                {currentDetail.title}
              </Typography>
            </Box>
            <IconButton
              onClick={handleDetailClose}
              size="small"
              sx={{ position: 'absolute', right: 12, top: 12 }}
            >
              <CloseIcon sx={{ fontSize: 20 }} />
            </IconButton>
          </DialogTitle>
          <DialogContent dividers sx={{ py: 2 }}>
            <MarkdownRenderer>{currentDetail.content}</MarkdownRenderer>
          </DialogContent>
        </>
      ) : null}
    </Dialog>
  )

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
        {userInfo ? renderLoggedInContent() : renderNotConfiguredContent()}
      </Popover>

      {renderDetailDialog()}
    </Box>
  )
}
