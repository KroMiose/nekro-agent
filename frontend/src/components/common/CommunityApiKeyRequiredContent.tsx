import { Avatar, Box, Typography, alpha } from '@mui/material'
import { Person as PersonIcon, Settings as SettingsIcon, VpnKey as VpnKeyIcon } from '@mui/icons-material'
import { useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { getCurrentExtendedPalette } from '../../theme/themeConfig'
import { BORDER_RADIUS } from '../../theme/variants'

interface CommunityApiKeyRequiredContentProps {
  onClose?: () => void
}

export default function CommunityApiKeyRequiredContent({
  onClose,
}: CommunityApiKeyRequiredContentProps) {
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

  const handleOpenCommunity = () => {
    window.open('https://cloud.nekro.ai', '_blank')
    onClose?.()
  }

  const handleGoToSettings = () => {
    navigate('/settings')
    onClose?.()
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
          onClick={handleOpenCommunity}
        >
          <VpnKeyIcon sx={{ fontSize: 16 }} />
          {t('community.getCommunityKey')}
        </Box>
        <Box
          sx={{ ...footerBtnStyles, justifyContent: 'center', py: 1 }}
          onClick={handleGoToSettings}
        >
          <SettingsIcon sx={{ fontSize: 16 }} />
          {t('community.goToSettings')}
        </Box>
      </Box>
    </Box>
  )
}
