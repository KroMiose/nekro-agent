import { useState } from 'react'
import {
  IconButton,
  Menu,
  MenuItem,
  ListItemIcon,
  ListItemText,
  Tooltip,
  Box,
  Typography,
  alpha,
  SxProps,
  Theme,
} from '@mui/material'
import { Language as LanguageIcon, Check as CheckIcon } from '@mui/icons-material'
import { useLocaleStore } from '../../stores/locale'
import type { SupportedLocale } from '../../config/i18n'
import { supportedLanguages } from '../../config/i18n'
import { getCurrentThemeMode, getCurrentExtendedPalette } from '../../theme/themeConfig'
import { BORDER_RADIUS } from '../../theme/variants'
import { useTranslation } from 'react-i18next'

interface LocaleToggleButtonProps {
  /**
   * 显示模式
   * - icon: 紧凑图标模式（地球+语言代码），适合登录框
   * - compact: 简洁模式（仅地球图标），适合顶栏，与主题切换按钮样式一致
   * - full: 完整模式（国旗+语言全称），适合设置页
   */
  mode?: 'icon' | 'compact' | 'full'
  /**
   * 自定义样式
   */
  sx?: SxProps<Theme>
}

// 语言图标映射
const LOCALE_FLAGS: Record<SupportedLocale, string> = {
  'zh-CN': '🇨🇳',
  'en-US': '🇺🇸',
}

// 语言简称
const LOCALE_SHORT_NAMES: Record<SupportedLocale, string> = {
  'zh-CN': 'ZH',
  'en-US': 'EN',
}

export default function LocaleToggleButton({ mode = 'compact', sx }: LocaleToggleButtonProps) {
  const { currentLocale, setLocale } = useLocaleStore()
  const { t } = useTranslation('common')
  const [anchorEl, setAnchorEl] = useState<null | HTMLElement>(null)
  const open = Boolean(anchorEl)

  // 使用主题系统获取正确的颜色
  const themeMode = getCurrentThemeMode()
  const palette = getCurrentExtendedPalette()

  const handleClick = (event: React.MouseEvent<HTMLElement>) => {
    setAnchorEl(event.currentTarget)
  }

  const handleClose = () => {
    setAnchorEl(null)
  }

  const handleLocaleChange = (locale: SupportedLocale) => {
    setLocale(locale)
    handleClose()
  }

  // 通用菜单样式
  const menuStyles = {
    '& .MuiPaper-root': {
      mt: 1,
      minWidth: 160,
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

  // 通用菜单项样式
  const menuItemStyles = {
    py: 1,
    px: 1.5,
    transition: 'background-color 0.15s ease',
    '&.Mui-selected': {
      backgroundColor: alpha(palette.primary.main, 0.12),
    },
    '&:hover': {
      backgroundColor: alpha(palette.primary.main, 0.08),
    },
  }

  // icon 模式：地球+语言代码，适合登录框
  if (mode === 'icon') {
    return (
      <Box>
        <Tooltip title={t('locale.toggleTooltip')} arrow>
          <IconButton
            onClick={handleClick}
            size="small"
            sx={{
              color: themeMode === 'dark' ? 'rgba(255, 255, 255, 0.7)' : 'rgba(0, 0, 0, 0.6)',
              transition: 'transform 0.3s ease, opacity 0.2s ease',
              '&:hover': {
                transform: 'rotate(12deg) scale(1.05)',
                color: palette.primary.main,
              },
              '&:active': {
                transform: 'scale(0.95)',
              },
              ...sx,
            }}
            aria-label={t('locale.selectLanguage')}
            aria-controls={open ? 'locale-menu' : undefined}
            aria-haspopup="true"
            aria-expanded={open ? 'true' : undefined}
          >
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.3 }}>
              <LanguageIcon sx={{ fontSize: 18, transition: 'all 0.3s ease' }} />
              <Typography
                sx={{
                  fontSize: '0.65rem',
                  fontWeight: 700,
                  letterSpacing: '0.3px',
                }}
              >
                {LOCALE_SHORT_NAMES[currentLocale]}
              </Typography>
            </Box>
          </IconButton>
        </Tooltip>

        <Menu
          id="locale-menu"
          anchorEl={anchorEl}
          open={open}
          onClose={handleClose}
          MenuListProps={{ 'aria-labelledby': 'locale-button' }}
          transformOrigin={{ horizontal: 'right', vertical: 'top' }}
          anchorOrigin={{ horizontal: 'right', vertical: 'bottom' }}
          sx={menuStyles}
        >
          {(Object.keys(supportedLanguages) as SupportedLocale[]).map(locale => (
            <MenuItem
              key={locale}
              onClick={() => handleLocaleChange(locale)}
              selected={currentLocale === locale}
              sx={menuItemStyles}
            >
              <ListItemIcon sx={{ minWidth: 28 }}>
                <Typography sx={{ fontSize: '1rem' }}>{LOCALE_FLAGS[locale]}</Typography>
              </ListItemIcon>
              <ListItemText
                primary={supportedLanguages[locale]}
                primaryTypographyProps={{ fontSize: '0.875rem' }}
              />
              {currentLocale === locale && (
                <CheckIcon sx={{ fontSize: 16, color: palette.primary.main, ml: 1 }} />
              )}
            </MenuItem>
          ))}
        </Menu>
      </Box>
    )
  }

  // compact 模式：与 ThemeToggleButton 完全一致的样式
  if (mode === 'compact') {
    return (
      <Box>
        <Tooltip title={t('locale.toggleTooltip')} arrow>
          <IconButton
            onClick={handleClick}
            color="inherit"
            size="medium"
            sx={{
              transition: 'transform 0.3s ease, opacity 0.2s ease',
              '&:hover': {
                transform: 'rotate(12deg) scale(1.05)',
              },
              '&:active': {
                transform: 'scale(0.95)',
              },
              ...sx,
            }}
            aria-label={t('locale.selectLanguage')}
            aria-controls={open ? 'locale-menu' : undefined}
            aria-haspopup="true"
            aria-expanded={open ? 'true' : undefined}
          >
            <LanguageIcon sx={{ transition: 'all 0.3s ease' }} />
          </IconButton>
        </Tooltip>

        <Menu
          id="locale-menu"
          anchorEl={anchorEl}
          open={open}
          onClose={handleClose}
          MenuListProps={{ 'aria-labelledby': 'locale-button' }}
          transformOrigin={{ horizontal: 'right', vertical: 'top' }}
          anchorOrigin={{ horizontal: 'right', vertical: 'bottom' }}
          sx={menuStyles}
        >
          {(Object.keys(supportedLanguages) as SupportedLocale[]).map(locale => (
            <MenuItem
              key={locale}
              onClick={() => handleLocaleChange(locale)}
              selected={currentLocale === locale}
              sx={menuItemStyles}
            >
              <ListItemIcon sx={{ minWidth: 32 }}>
                <Typography sx={{ fontSize: '1.1rem' }}>{LOCALE_FLAGS[locale]}</Typography>
              </ListItemIcon>
              <ListItemText primary={supportedLanguages[locale]} />
              {currentLocale === locale && (
                <CheckIcon sx={{ fontSize: 18, color: palette.primary.main, ml: 1 }} />
              )}
            </MenuItem>
          ))}
        </Menu>
      </Box>
    )
  }

  // full 模式：国旗+语言全称，适合设置页等
  return (
    <Box>
      <Tooltip title="切换语言 / Switch Language">
        <IconButton
          onClick={handleClick}
          sx={{
            color: 'inherit',
            borderRadius: BORDER_RADIUS.DEFAULT,
            px: 2,
            py: 1,
            transition: 'transform 0.3s ease, background-color 0.2s ease',
            backgroundColor:
              themeMode === 'dark' ? 'rgba(255, 255, 255, 0.08)' : 'rgba(0, 0, 0, 0.04)',
            border: `1px solid ${themeMode === 'dark' ? 'rgba(255, 255, 255, 0.1)' : 'rgba(0, 0, 0, 0.08)'}`,
            '&:hover': {
              backgroundColor:
                themeMode === 'dark' ? 'rgba(255, 255, 255, 0.12)' : 'rgba(0, 0, 0, 0.06)',
              transform: 'translateY(-1px)',
            },
            ...sx,
          }}
          aria-label="选择语言"
          aria-controls={open ? 'locale-menu' : undefined}
          aria-haspopup="true"
          aria-expanded={open ? 'true' : undefined}
        >
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <Typography sx={{ fontSize: '1.1rem' }}>{LOCALE_FLAGS[currentLocale]}</Typography>
            <Typography sx={{ fontWeight: 500, fontSize: '0.875rem' }}>
              {supportedLanguages[currentLocale]}
            </Typography>
          </Box>
        </IconButton>
      </Tooltip>

      <Menu
        id="locale-menu"
        anchorEl={anchorEl}
        open={open}
        onClose={handleClose}
        MenuListProps={{ 'aria-labelledby': 'locale-button' }}
        transformOrigin={{ horizontal: 'right', vertical: 'top' }}
        anchorOrigin={{ horizontal: 'right', vertical: 'bottom' }}
        sx={menuStyles}
      >
        {(Object.keys(supportedLanguages) as SupportedLocale[]).map(locale => (
          <MenuItem
            key={locale}
            onClick={() => handleLocaleChange(locale)}
            selected={currentLocale === locale}
            sx={{ ...menuItemStyles, py: 1.5 }}
          >
            <ListItemIcon sx={{ minWidth: 36 }}>
              <Typography sx={{ fontSize: '1.2rem' }}>{LOCALE_FLAGS[locale]}</Typography>
            </ListItemIcon>
            <ListItemText primary={supportedLanguages[locale]} />
            {currentLocale === locale && <CheckIcon sx={{ color: palette.primary.main, ml: 1 }} />}
          </MenuItem>
        ))}
      </Menu>
    </Box>
  )
}
