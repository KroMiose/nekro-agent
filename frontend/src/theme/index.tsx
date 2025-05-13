import { createTheme, ThemeProvider } from '@mui/material/styles'
import { CssBaseline } from '@mui/material'
import { ReactNode } from 'react'
import { useColorMode } from '../stores/theme'
import { GRADIENTS, COLORS, SHADOWS } from './constants'

// 圆角尺寸常量
const BORDER_RADIUS = {
  SMALL: '6px',   // 默认，用于按钮、卡片等
  MEDIUM: '8px',  // 用于对话框、大型容器
  LARGE: '12px',  // 用于特殊组件
}

// 定义全局字体
const globalFonts = {
  sans: [
    '"Microsoft YaHei"',
    '-apple-system',
    'BlinkMacSystemFont',
    '"Segoe UI"',
    'Roboto',
    '"Helvetica Neue"',
    'Arial',
    'sans-serif',
  ].join(','),
}

export default function ThemeConfig({ children }: { children: ReactNode }) {
  const { mode } = useColorMode()
  const isDark = mode === 'dark'

  const theme = createTheme({
    palette: {
      mode,
      primary: {
        main: isDark ? COLORS.PRIMARY.DARK : COLORS.PRIMARY.LIGHT,
        contrastText: '#fff',
        light: isDark ? COLORS.PRIMARY.HIGHLIGHT : COLORS.PRIMARY.LIGHTER, 
        dark: isDark ? COLORS.PRIMARY.DARKER : COLORS.PRIMARY.DARKER,
      },
      secondary: {
        main: isDark ? COLORS.SECONDARY.DARK : COLORS.SECONDARY.LIGHT,
        light: isDark ? COLORS.SECONDARY.HIGHLIGHT : COLORS.SECONDARY.LIGHTER,
        dark: isDark ? COLORS.SECONDARY.DARKER : COLORS.SECONDARY.DARKER,
      },
      background: {
        default: isDark ? '#1a1818' : '#f8f5f5',
        paper: isDark ? '#211c1c' : '#fff',
      },
      text: {
        primary: isDark ? 'rgba(255, 255, 255, 0.95)' : 'rgba(0, 0, 0, 0.87)',
        secondary: isDark ? 'rgba(255, 255, 255, 0.7)' : 'rgba(0, 0, 0, 0.6)',
        disabled: isDark ? 'rgba(255, 255, 255, 0.5)' : 'rgba(0, 0, 0, 0.38)',
      },
      divider: isDark ? 'rgba(255, 255, 255, 0.12)' : 'rgba(0, 0, 0, 0.12)',
      action: {
        active: isDark ? 'rgba(255, 255, 255, 0.8)' : 'rgba(0, 0, 0, 0.6)',
        hover: isDark ? 'rgba(255, 255, 255, 0.12)' : 'rgba(0, 0, 0, 0.04)',
        selected: isDark ? 'rgba(255, 255, 255, 0.16)' : 'rgba(0, 0, 0, 0.08)',
        disabled: isDark ? 'rgba(255, 255, 255, 0.3)' : 'rgba(0, 0, 0, 0.26)',
        disabledBackground: isDark ? 'rgba(255, 255, 255, 0.12)' : 'rgba(0, 0, 0, 0.12)',
      },
    },
    typography: {
      fontFamily: globalFonts.sans,
      h1: { fontFamily: globalFonts.sans },
      h2: { fontFamily: globalFonts.sans },
      h3: { fontFamily: globalFonts.sans },
      h4: { fontFamily: globalFonts.sans },
      h5: { fontFamily: globalFonts.sans },
      h6: { fontFamily: globalFonts.sans },
      subtitle1: { fontFamily: globalFonts.sans },
      subtitle2: { fontFamily: globalFonts.sans },
      body1: { fontFamily: globalFonts.sans },
      body2: { fontFamily: globalFonts.sans },
      button: { fontFamily: globalFonts.sans },
      caption: { fontFamily: globalFonts.sans },
      overline: { fontFamily: globalFonts.sans },
    },
    shape: {
      borderRadius: parseInt(BORDER_RADIUS.SMALL),
    },
    components: {
      MuiAppBar: {
        styleOverrides: {
          root: {
            backgroundColor: 'transparent',
            backgroundImage: isDark 
              ? GRADIENTS.APP_BAR.DARK
              : GRADIENTS.APP_BAR.LIGHT,
            boxShadow: isDark 
              ? SHADOWS.APP_BAR.DARK
              : SHADOWS.APP_BAR.LIGHT,
            borderBottom: isDark ? `1px solid rgba(234, 82, 82, 0.15)` : 'none',
          },
        },
      },
      MuiDrawer: {
        styleOverrides: {
          paper: {
            backgroundColor: isDark ? '#1a1818' : '#fff',
            backgroundImage: isDark 
              ? GRADIENTS.DRAWER.DARK
              : GRADIENTS.DRAWER.LIGHT,
            boxShadow: isDark 
              ? SHADOWS.DRAWER.DARK
              : SHADOWS.DRAWER.LIGHT,
            borderRight: isDark 
              ? '1px solid rgba(102, 36, 36, 0.08)'
              : '1px solid rgba(0, 0, 0, 0.05)',
          },
        },
      },
      MuiButton: {
        styleOverrides: {
          root: {
            textTransform: 'none',
            borderRadius: BORDER_RADIUS.SMALL,
            transition: 'all 0.2s ease-in-out',
          },
          contained: {
            boxShadow: isDark 
              ? SHADOWS.BUTTON.DARK.DEFAULT
              : SHADOWS.BUTTON.LIGHT.DEFAULT,
            '&:hover': {
              boxShadow: isDark 
                ? SHADOWS.BUTTON.DARK.HOVER
                : SHADOWS.BUTTON.LIGHT.HOVER,
            },
          },
        },
      },
      MuiCard: {
        styleOverrides: {
          root: {
            boxShadow: isDark 
              ? SHADOWS.CARD.DARK.DEFAULT
              : SHADOWS.CARD.LIGHT.DEFAULT,
            transition: 'all 0.3s ease',
            borderRadius: BORDER_RADIUS.SMALL,
            '&:hover': {
              boxShadow: isDark 
                ? SHADOWS.CARD.DARK.HOVER
                : SHADOWS.CARD.LIGHT.HOVER,
            },
          },
        },
      },
      MuiPaper: {
        styleOverrides: {
          root: {
            backgroundImage: 'none',
            backgroundColor: isDark 
              ? '#211c1c'
              : '#fff',
            borderRadius: BORDER_RADIUS.SMALL,
          },
        },
      },
      MuiDialog: {
        styleOverrides: {
          paper: {
            borderRadius: BORDER_RADIUS.MEDIUM,
          },
        },
      },
      MuiCssBaseline: {
        styleOverrides: {
          'html, body': {
            margin: 0,
            padding: 0,
            minHeight: '100vh',
          },
          body: {
            fontFamily: globalFonts.sans,
            transition: 'background-color 0.3s ease',
            background: isDark 
              ? GRADIENTS.BACKGROUND.DARK.PRIMARY
              : GRADIENTS.BACKGROUND.LIGHT.PRIMARY,
          },
          '*::-webkit-scrollbar': {
            width: '8px',
            height: '8px',
          },
          '*::-webkit-scrollbar-track': {
            background: isDark ? 'rgba(255, 255, 255, 0.05)' : '#f5f5f5',
            borderRadius: '4px',
          },
          '*::-webkit-scrollbar-thumb': {
            background: isDark ? 'rgba(255, 255, 255, 0.15)' : 'rgba(0, 0, 0, 0.2)',
            borderRadius: '4px',
            '&:hover': {
              background: isDark ? 'rgba(255, 255, 255, 0.25)' : 'rgba(0, 0, 0, 0.3)',
            },
          },
          '*': {
            scrollbarWidth: 'thin',
            scrollbarColor:
              isDark
                ? `rgba(255, 255, 255, 0.15) rgba(255, 255, 255, 0.05)`
                : `rgba(0, 0, 0, 0.2) #f5f5f5`,
          },
        },
      },
      MuiListItemButton: {
        styleOverrides: {
          root: {
            '&.Mui-selected': {
              backgroundColor: isDark 
                ? 'rgba(240, 84, 84, 0.15)'
                : 'rgba(234, 82, 82, 0.08)',
              '&:hover': {
                backgroundColor: isDark 
                  ? 'rgba(240, 84, 84, 0.25)'
                  : 'rgba(234, 82, 82, 0.12)',
              },
            },
            '&:hover': {
              backgroundColor: isDark 
                ? 'rgba(240, 84, 84, 0.08)'
                : 'rgba(234, 82, 82, 0.05)',
            },
          },
        },
      },
      MuiListItemIcon: {
        styleOverrides: {
          root: {
            color: isDark ? 'rgba(255, 255, 255, 0.7)' : 'inherit',
            minWidth: '40px',
          }
        }
      },
    },
  })

  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      {children}
    </ThemeProvider>
  )
}
