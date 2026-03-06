import {
  Avatar,
  Box,
  Typography,
  Divider,
  Tabs,
  Tab,
  Badge,
  IconButton,
  Tooltip,
  alpha,
} from '@mui/material'
import {
  Person as PersonIcon,
  Refresh as RefreshIcon,
  Settings as SettingsIcon,
  VpnKey as VpnKeyIcon,
  Campaign as CampaignIcon,
  Email as EmailIcon,
  DoneAll as DoneAllIcon,
  OpenInNew as OpenInNewIcon,
} from '@mui/icons-material'
import { useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { getCurrentExtendedPalette } from '../../theme/themeConfig'
import { BORDER_RADIUS } from '../../theme/variants'
import AnnouncementList from './AnnouncementList'
import type { AnnouncementSummary } from '../../services/api/cloud/announcement'

interface MessageItem {
  id: string
  title: string
  content: string
  time: string
  read: boolean
}

interface CommunityAvatarContentProps {
  userInfo?: { username: string; email?: string; avatarUrl?: string }
  userLoading: boolean
  announcements: AnnouncementSummary[]
  announcementLoading: boolean
  readIds: string[]
  badgeCount: number
  activeTab: number
  onTabChange: (tab: number) => void
  onRefresh: () => void
  onAnnouncementClick: (id: string) => void
  onMarkAllRead: () => void
  onClose: () => void
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

export function LoggedInContent({
  userInfo,
  userLoading,
  announcements,
  announcementLoading,
  readIds,
  badgeCount,
  activeTab,
  onTabChange,
  onRefresh,
  onAnnouncementClick,
  onMarkAllRead,
}: CommunityAvatarContentProps) {
  const { t } = useTranslation('layout-MainLayout')
  const navigate = useNavigate()
  const palette = getCurrentExtendedPalette()

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

  const messages: MessageItem[] = []

  return (
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
          <IconButton size="small" onClick={onRefresh} disabled={userLoading} sx={{ flexShrink: 0 }}>
            <RefreshIcon sx={{ fontSize: 18 }} />
          </IconButton>
        </Tooltip>
      </Box>

      <Divider />

      {/* Tab 栏 + 一键已读 */}
      <Box sx={{ display: 'flex', alignItems: 'center' }}>
        <Tabs
          value={activeTab}
          onChange={(_, v: number) => onTabChange(v)}
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
              onClick={onMarkAllRead}
              sx={{ mr: 1, color: 'text.secondary' }}
            >
              <DoneAllIcon sx={{ fontSize: 16 }} />
            </IconButton>
          </Tooltip>
        )}
      </Box>

      {/* 内容区 */}
      <Box sx={{ flex: 1, minHeight: 160, maxHeight: 300, overflow: 'auto' }}>
        {activeTab === 0 && (
          <AnnouncementList
            items={announcements}
            loading={announcementLoading}
            readIds={readIds}
            onAnnouncementClick={onAnnouncementClick}
          />
        )}
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
            window.open('https://cloud.nekro.ai', '_blank')
          }}
        >
          <OpenInNewIcon sx={{ fontSize: 14 }} />
          {t('community.visitCommunity')}
        </Box>
        <Box
          sx={footerBtnStyles}
          onClick={() => {
            navigate('/settings')
          }}
        >
          <SettingsIcon sx={{ fontSize: 14 }} />
          {t('community.goToSettings')}
        </Box>
      </Box>
    </>
  )
}

export function NotConfiguredContent({ onClose }: { onClose: () => void }) {
  const { t } = useTranslation('layout-MainLayout')
  const navigate = useNavigate()
  const palette = getCurrentExtendedPalette()

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

  return (
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
            window.open('https://cloud.nekro.ai', '_blank')
            onClose()
          }}
        >
          <VpnKeyIcon sx={{ fontSize: 16 }} />
          {t('community.getCommunityKey')}
        </Box>
        <Box
          sx={{ ...footerBtnStyles, justifyContent: 'center', py: 1 }}
          onClick={() => {
            navigate('/settings')
            onClose()
          }}
        >
          <SettingsIcon sx={{ fontSize: 16 }} />
          {t('community.goToSettings')}
        </Box>
      </Box>
    </Box>
  )
}
