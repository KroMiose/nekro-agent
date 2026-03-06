import { useState, useEffect } from 'react'
import {
  IconButton,
  Menu,
  MenuItem,
  Avatar,
  Tooltip,
  Box,
  Typography,
  Divider,
  alpha,
} from '@mui/material'
import {
  Person as PersonIcon,
  OpenInNew as OpenInNewIcon,
  Refresh as RefreshIcon,
  Settings as SettingsIcon,
  VpnKey as VpnKeyIcon,
} from '@mui/icons-material'
import { useNavigate } from 'react-router-dom'
import { useCommunityUserStore } from '../../stores/communityUser'
import { getCurrentThemeMode, getCurrentExtendedPalette } from '../../theme/themeConfig'
import { BORDER_RADIUS } from '../../theme/variants'
import { useTranslation } from 'react-i18next'

export default function CommunityAvatar() {
  const { userInfo, loading, fetchUserProfile } = useCommunityUserStore()
  const [anchorEl, setAnchorEl] = useState<null | HTMLElement>(null)
  const open = Boolean(anchorEl)
  const themeMode = getCurrentThemeMode()
  const palette = getCurrentExtendedPalette()
  const { t } = useTranslation('layout-MainLayout')
  const navigate = useNavigate()

  useEffect(() => {
    fetchUserProfile()
  }, [fetchUserProfile])

  const handleClick = (event: React.MouseEvent<HTMLElement>) => {
    setAnchorEl(event.currentTarget)
  }

  const handleClose = () => {
    setAnchorEl(null)
  }

  const handleRefresh = () => {
    fetchUserProfile(true)
    handleClose()
  }

  const menuStyles = {
    '& .MuiPaper-root': {
      mt: 1,
      minWidth: 220,
      backgroundColor:
        themeMode === 'dark' ? 'rgba(35, 35, 40, 0.95)' : 'rgba(255, 255, 255, 0.95)',
      backdropFilter: 'blur(20px)',
      WebkitBackdropFilter: 'blur(20px)',
      borderRadius: BORDER_RADIUS.DEFAULT,
      border: `1px solid ${themeMode === 'dark' ? 'rgba(255, 255, 255, 0.1)' : 'rgba(0, 0, 0, 0.08)'}`,
      boxShadow:
        themeMode === 'dark' ? '0 8px 32px rgba(0, 0, 0, 0.4)' : '0 8px 32px rgba(0, 0, 0, 0.12)',
    },
  }

  const menuItemStyles = {
    py: 1,
    px: 1.5,
    transition: 'background-color 0.15s ease',
    '&:hover': {
      backgroundColor: alpha(palette.primary.main, 0.08),
    },
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
        </IconButton>
      </Tooltip>

      <Menu
        anchorEl={anchorEl}
        open={open}
        onClose={handleClose}
        transformOrigin={{ horizontal: 'right', vertical: 'top' }}
        anchorOrigin={{ horizontal: 'right', vertical: 'bottom' }}
        sx={menuStyles}
      >
        {userInfo ? (
          [
            <Box key="user-info" sx={{ px: 2, py: 1.5 }}>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5 }}>
                <Avatar src={userInfo.avatarUrl} sx={{ width: 40, height: 40 }} />
                <Box>
                  <Typography variant="subtitle2" sx={{ fontWeight: 600 }}>
                    {userInfo.username}
                  </Typography>
                  {userInfo.email && (
                    <Typography variant="caption" color="text.secondary">
                      {userInfo.email}
                    </Typography>
                  )}
                </Box>
              </Box>
            </Box>,
            <Divider key="divider" />,
            <MenuItem
              key="visit"
              onClick={() => {
                window.open('https://community.nekro.ai', '_blank')
                handleClose()
              }}
              sx={menuItemStyles}
            >
              <OpenInNewIcon sx={{ fontSize: 18, mr: 1.5, color: 'text.secondary' }} />
              <Typography variant="body2">{t('community.visitCommunity')}</Typography>
            </MenuItem>,
            <MenuItem key="refresh" onClick={handleRefresh} disabled={loading} sx={menuItemStyles}>
              <RefreshIcon sx={{ fontSize: 18, mr: 1.5, color: 'text.secondary' }} />
              <Typography variant="body2">{t('community.refreshProfile')}</Typography>
            </MenuItem>,
          ]
        ) : (
          <Box>
            <Box sx={{ px: 2, py: 1.5 }}>
              <Typography variant="subtitle2" sx={{ fontWeight: 600 }}>
                {t('community.notConfiguredTitle')}
              </Typography>
              <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mt: 0.5 }}>
                {t('community.notConfiguredDesc')}
              </Typography>
            </Box>
            <Divider />
            <MenuItem
              onClick={() => {
                window.open('https://community.nekro.ai', '_blank')
                handleClose()
              }}
              sx={menuItemStyles}
            >
              <VpnKeyIcon sx={{ fontSize: 18, mr: 1.5, color: 'text.secondary' }} />
              <Typography variant="body2">{t('community.getCommunityKey')}</Typography>
            </MenuItem>
            <MenuItem
              onClick={() => {
                navigate('/settings')
                handleClose()
              }}
              sx={menuItemStyles}
            >
              <SettingsIcon sx={{ fontSize: 18, mr: 1.5, color: 'text.secondary' }} />
              <Typography variant="body2">{t('community.goToSettings')}</Typography>
            </MenuItem>
          </Box>
        )}
      </Menu>
    </Box>
  )
}
