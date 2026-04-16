import {
  Avatar,
  Box,
  Typography,
  Divider,
  Tab,
  Badge,
  Tooltip,
  alpha,
} from '@mui/material'
import {
  Refresh as RefreshIcon,
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
import { InlineTabs } from './NekroTabs'
import CommunityApiKeyRequiredContent from './CommunityApiKeyRequiredContent'
import type { AnnouncementSummary } from '../../services/api/cloud/announcement'
import IconActionButton from './IconActionButton'

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
          <IconActionButton size="small" onClick={onRefresh} disabled={userLoading} sx={{ flexShrink: 0 }}>
            <RefreshIcon sx={{ fontSize: 18 }} />
          </IconActionButton>
        </Tooltip>
      </Box>

      <Divider />

      {/* Tab 栏 + 一键已读 */}
      <Box sx={{ display: 'flex', alignItems: 'center' }}>
        <InlineTabs
          value={activeTab}
          onChange={(_, v: number) => onTabChange(v)}
          variant="fullWidth"
          sx={{
            flex: 1,
            '& .MuiTab-root': {
              minHeight: 40,
              minWidth: 0,
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
        </InlineTabs>
        {activeTab === 0 && badgeCount > 0 && (
          <Tooltip title={t('community.markAllRead')} arrow>
            <IconActionButton
              size="small"
              onClick={onMarkAllRead}
              sx={{ mr: 1, color: 'text.secondary' }}
            >
              <DoneAllIcon sx={{ fontSize: 16 }} />
            </IconActionButton>
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
  return <CommunityApiKeyRequiredContent onClose={onClose} />
}
