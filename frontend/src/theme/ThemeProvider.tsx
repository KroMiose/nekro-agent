/**
 * 主题提供者组件
 * 负责创建并提供MUI主题，处理主题切换逻辑
 */
import { ReactNode, useEffect, useState } from 'react'
import { createTheme, ThemeProvider as MuiThemeProvider } from '@mui/material/styles'
import { CssBaseline } from '@mui/material'
import { useColorMode } from '../stores/theme'
import { getCurrentTheme, UI_STYLES, getCurrentBackground, getCurrentExtendedPalette } from './themeConfig'
import { LAYOUT, BORDER_RADIUS } from './variants'
import { getMuiPaletteOptions, getAlphaColor } from './palette'

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

/**
 * 主题提供者组件
 * 提供整个应用的主题配置，处理主题切换逻辑
 */
export default function ThemeProvider({ children }: { children: ReactNode }) {
  const { getEffectiveMode } = useColorMode()
  const effectiveMode = getEffectiveMode()
  const currentTheme = getCurrentTheme()
  const currentBackground = getCurrentBackground()
  const extendedPalette = getCurrentExtendedPalette()
  
  // 状态跟踪，用于强制重新渲染
  const [, forceUpdate] = useState({});

  // 监听系统主题变化
  useEffect(() => {
    const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)')
    
    const handleChange = () => {
      // 触发重新渲染 (由于 useEffect 会在依赖变化时重新运行，这里不需要额外操作)
    }
    
    mediaQuery.addEventListener('change', handleChange)
    
    return () => {
      mediaQuery.removeEventListener('change', handleChange)
    }
  }, [])
  
  // 监听主题变化事件
  useEffect(() => {
    const handleThemeChange = () => {
      // 强制组件重新渲染
      forceUpdate({});
    };
    
    window.addEventListener('nekro-theme-change', handleThemeChange);
    
    return () => {
      window.removeEventListener('nekro-theme-change', handleThemeChange);
    };
  }, []);

  // 创建 MUI 主题
  const theme = createTheme({
    // 调色板配置
    palette: getMuiPaletteOptions(effectiveMode, currentTheme),
    
    // 字体设置
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
    
    // 形状设置
    shape: {
      borderRadius: parseInt(BORDER_RADIUS.DEFAULT),
    },
    
    // 组件样式覆盖
    components: {
      // 应用栏
      MuiAppBar: {
        styleOverrides: {
          root: {
            backgroundColor: 'transparent',
            backgroundImage: UI_STYLES.getGradient('primary'),
            boxShadow: UI_STYLES.getShadow('medium'),
            borderBottom: effectiveMode === 'dark' ? UI_STYLES.getBorder() : 'none',
          },
        },
      },
      
      // 抽屉
      MuiDrawer: {
        styleOverrides: {
          paper: {
            backgroundColor: getAlphaColor(currentBackground.paper, 0.85),
            backgroundImage: `linear-gradient(to bottom, ${getAlphaColor(extendedPalette.primary.darker, 0.05)}, transparent)`,
            backdropFilter: 'blur(12px)',
            WebkitBackdropFilter: 'blur(12px)',
            boxShadow: `0 0 25px rgba(0, 0, 0, ${effectiveMode === 'dark' ? 0.35 : 0.1}), 0 0 10px ${getAlphaColor(extendedPalette.primary.main, effectiveMode === 'dark' ? 0.12 : 0.05)}`,
            borderRight: '1px solid',
            borderRightColor: effectiveMode === 'dark' 
              ? getAlphaColor(extendedPalette.primary.main, 0.12)
              : getAlphaColor(extendedPalette.primary.main, 0.06),
            transition: 'all 0.3s ease-in-out',
          },
        },
      },
      
      // 按钮
      MuiButton: {
        styleOverrides: {
          root: {
            textTransform: 'none',
            borderRadius: BORDER_RADIUS.DEFAULT,
            transition: LAYOUT.TRANSITION.FAST,
            '&:hover': {
              transform: 'translateY(-1px)',
            },
          },
          contained: {
            boxShadow: UI_STYLES.getShadow('light'),
            '&:hover': {
              boxShadow: UI_STYLES.getShadow('medium'),
            },
          },
        },
      },
      
      // 卡片
      MuiCard: {
        styleOverrides: {
          root: {
            boxShadow: UI_STYLES.getShadow('light'),
            transition: LAYOUT.TRANSITION.DEFAULT,
            borderRadius: BORDER_RADIUS.DEFAULT,
            border: effectiveMode === 'light' 
              ? `1px solid rgba(0, 0, 0, 0.08)` 
              : `1px solid ${getAlphaColor(extendedPalette.primary.main, 0.12)}`,
            backgroundColor: effectiveMode === 'light'
              ? 'rgba(255, 255, 255, 0.92)'
              : getAlphaColor(currentBackground.paper, 0.92),
            backgroundImage: effectiveMode === 'light'
              ? `linear-gradient(135deg, rgba(255, 255, 255, 0.95), rgba(255, 255, 255, 0.9))`
              : `linear-gradient(135deg, ${getAlphaColor(currentBackground.paper, 0.95)}, ${getAlphaColor(currentBackground.paper, 0.85)})`,
            backdropFilter: 'blur(10px)',
            WebkitBackdropFilter: 'blur(10px)',
            position: 'relative',
            overflow: 'hidden',
            '&:before': {
              content: '""',
              position: 'absolute',
              top: 0,
              left: 0,
              right: 0,
              height: '2px',
              background: `linear-gradient(90deg, ${getAlphaColor(extendedPalette.primary.main, 0.12)}, ${getAlphaColor(extendedPalette.secondary.main, 0.12)})`,
              opacity: 0,
              transition: 'opacity 0.3s ease',
            },
            '&:hover': {
              boxShadow: UI_STYLES.getShadow('medium'),
              transform: 'translateY(-2px)',
              borderColor: getAlphaColor(extendedPalette.primary.main, effectiveMode === 'light' ? 0.1 : 0.18),
              '&:before': {
                opacity: 1,
              },
            },
          },
        },
      },
      
      // 纸张
      MuiPaper: {
        styleOverrides: {
          root: {
            backgroundImage: 'none',
            backgroundColor: getAlphaColor(currentBackground.paper, 0.85),
            backdropFilter: 'blur(8px)',
            WebkitBackdropFilter: 'blur(8px)',
            borderRadius: BORDER_RADIUS.DEFAULT,
            transition: LAYOUT.TRANSITION.DEFAULT,
            border: `1px solid ${getAlphaColor(extendedPalette.primary.main, effectiveMode === 'dark' ? 0.08 : 0.04)}`,
          },
        },
      },
      
      // 对话框
      MuiDialog: {
        styleOverrides: {
          paper: {
            borderRadius: BORDER_RADIUS.MEDIUM,
            backgroundColor: getAlphaColor(currentBackground.paper, 0.9),
            backdropFilter: 'blur(12px)',
            WebkitBackdropFilter: 'blur(12px)',
            border: `1px solid ${getAlphaColor(extendedPalette.primary.main, effectiveMode === 'dark' ? 0.15 : 0.08)}`,
            boxShadow: `0 10px 30px rgba(0, 0, 0, ${effectiveMode === 'dark' ? 0.35 : 0.15}), 0 0 10px ${getAlphaColor(extendedPalette.primary.main, effectiveMode === 'dark' ? 0.12 : 0.05)}`,
            overflow: 'hidden',
          },
        },
      },
      
      // 全局样式
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
            background: UI_STYLES.getGradient('background'),
            backgroundColor: effectiveMode === 'dark' ? '#181818' : '#f8f8f8',
          },
          '*::-webkit-scrollbar': {
            width: '7px',
            height: '7px',
          },
          '*::-webkit-scrollbar-track': {
            background: effectiveMode === 'dark' ? 'rgba(255, 255, 255, 0.05)' : 'rgba(0, 0, 0, 0.04)',
            borderRadius: '3px',
          },
          '*::-webkit-scrollbar-thumb': {
            background: effectiveMode === 'dark' ? 'rgba(255, 255, 255, 0.18)' : 'rgba(0, 0, 0, 0.18)',
            borderRadius: '3px',
            '&:hover': {
              background: effectiveMode === 'dark' ? 'rgba(255, 255, 255, 0.25)' : 'rgba(0, 0, 0, 0.25)',
            },
          },
          '*': {
            scrollbarWidth: 'thin',
            scrollbarColor: `${effectiveMode === 'dark' ? 'rgba(255, 255, 255, 0.18)' : 'rgba(0, 0, 0, 0.18)'} 
            ${effectiveMode === 'dark' ? 'rgba(255, 255, 255, 0.05)' : 'rgba(0, 0, 0, 0.04)'}`,
          },
        },
      },
      
      // 列表项按钮
      MuiListItemButton: {
        styleOverrides: {
          root: {
            borderRadius: '6px',
            margin: '3px 8px',
            '&.Mui-selected': {
              backgroundColor: getAlphaColor(extendedPalette.primary.main, 0.15),
              boxShadow: `0 2px 5px ${getAlphaColor(extendedPalette.primary.main, 0.1)}`,
              '&:hover': {
                backgroundColor: getAlphaColor(extendedPalette.primary.main, 0.25),
              },
            },
            '&:hover': {
              backgroundColor: getAlphaColor(extendedPalette.primary.main, 0.1),
              transform: 'translateY(-1px)',
            },
            transition: 'all 0.2s ease',
          },
        },
      },
      
      // 列表项图标
      MuiListItemIcon: {
        styleOverrides: {
          root: {
            color: effectiveMode === 'dark' 
              ? getAlphaColor(extendedPalette.primary.lighter, 0.85)
              : extendedPalette.primary.main,
            minWidth: '40px',
            transition: 'color 0.2s ease',
          }
        }
      },
      
      // 表格容器
      MuiTableContainer: {
        styleOverrides: {
          root: {
            backgroundColor: effectiveMode === 'light' 
              ? 'rgba(255, 255, 255, 0.85)' 
              : getAlphaColor(currentBackground.paper, 0.85),
            backdropFilter: 'blur(12px)',
            WebkitBackdropFilter: 'blur(12px)',
            borderRadius: BORDER_RADIUS.DEFAULT,
            boxShadow: UI_STYLES.getShadow('light'),
            border: effectiveMode === 'light' 
              ? `1px solid rgba(0, 0, 0, 0.06)` 
              : `1px solid ${getAlphaColor(extendedPalette.primary.main, 0.1)}`,
            overflow: 'hidden',
            transition: 'all 0.3s ease',
            position: 'relative',
            '&:hover': {
              boxShadow: UI_STYLES.getShadow('medium'),
            },
            '&::before': {
              content: '""',
              position: 'absolute',
              top: 0,
              left: 0,
              width: '100%',
              height: '2px',
              background: `linear-gradient(90deg, ${getAlphaColor(extendedPalette.primary.main, 0.2)}, ${getAlphaColor(extendedPalette.secondary.main, 0.2)})`,
              opacity: 0.7,
            },
          },
        },
      },

      // 表格
      MuiTable: {
        styleOverrides: {
          root: {
            borderCollapse: 'separate',
            borderSpacing: 0,
          },
        },
      },
      
      // 表格行
      MuiTableRow: {
        styleOverrides: {
          root: {
            '&:hover': {
              backgroundColor: getAlphaColor(extendedPalette.primary.main, 0.08),
            },
            '&:nth-of-type(odd)': {
              backgroundColor: effectiveMode === 'light'
                ? 'rgba(0, 0, 0, 0.02)'
                : 'rgba(255, 255, 255, 0.03)',
            },
            transition: 'background-color 0.2s ease',
          },
        }
      },
      
      // 表格单元格
      MuiTableCell: {
        styleOverrides: {
          root: {
            borderBottom: `1px solid ${effectiveMode === 'dark' ? 'rgba(255, 255, 255, 0.07)' : 'rgba(0, 0, 0, 0.06)'}`,
            transition: 'background-color 0.2s ease',
            padding: '12px 16px',
          },
          head: {
            fontWeight: 600,
            backgroundColor: effectiveMode === 'light'
              ? 'rgba(245, 245, 245, 0.8)'
              : getAlphaColor(extendedPalette.primary.darker, 0.4),
            color: effectiveMode === 'dark' ? 'rgba(255, 255, 255, 0.95)' : 'rgba(0, 0, 0, 0.85)',
            transition: 'background-color 0.2s ease, color 0.2s ease',
            backdropFilter: 'blur(10px)',
            WebkitBackdropFilter: 'blur(10px)',
            position: 'sticky',
            top: 0,
            zIndex: 10,
            boxShadow: effectiveMode === 'dark' 
              ? '0 4px 6px -1px rgba(0, 0, 0, 0.15)'
              : '0 4px 6px -1px rgba(0, 0, 0, 0.08)',
            backgroundImage: effectiveMode === 'light'
              ? `linear-gradient(180deg, rgba(255, 255, 255, 0.95), rgba(245, 245, 245, 0.85))`
              : `linear-gradient(180deg, ${getAlphaColor(extendedPalette.primary.darker, 0.5)}, ${getAlphaColor(extendedPalette.primary.darker, 0.4)})`,
            letterSpacing: '0.02em',
            textTransform: 'uppercase',
            fontSize: '0.75rem',
          },
          body: {
            fontSize: '0.875rem',
            backdropFilter: 'blur(4px)',
            WebkitBackdropFilter: 'blur(4px)',
          },
        }
      },
      
      // 工具栏
      MuiToolbar: {
        styleOverrides: {
          root: {
            transition: 'all 0.3s ease',
            '& .MuiTypography-root': {
              textShadow: effectiveMode === 'dark'
                ? '0 0 8px rgba(0, 0, 0, 0.3)'
                : '0 0 8px rgba(255, 255, 255, 0.3)',
            },
          },
        }
      },
      
      // 菜单
      MuiMenu: {
        styleOverrides: {
          paper: {
            backdropFilter: 'blur(10px)',
            WebkitBackdropFilter: 'blur(10px)',
            backgroundColor: getAlphaColor(currentBackground.paper, 0.85),
            boxShadow: `0 4px 20px rgba(0, 0, 0, ${effectiveMode === 'dark' ? 0.3 : 0.12}), 0 0 10px ${getAlphaColor(extendedPalette.primary.main, effectiveMode === 'dark' ? 0.1 : 0.05)}`,
            border: `1px solid ${getAlphaColor(extendedPalette.primary.main, effectiveMode === 'dark' ? 0.12 : 0.06)}`,
            '& .MuiMenuItem-root': {
              transition: 'background-color 0.2s ease',
            },
          },
        },
      },

      // 弹出框
      MuiPopover: {
        styleOverrides: {
          paper: {
            backdropFilter: 'blur(10px)',
            WebkitBackdropFilter: 'blur(10px)',
            backgroundColor: getAlphaColor(currentBackground.paper, 0.85),
            boxShadow: `0 4px 20px rgba(0, 0, 0, ${effectiveMode === 'dark' ? 0.3 : 0.12}), 0 0 10px ${getAlphaColor(extendedPalette.primary.main, effectiveMode === 'dark' ? 0.1 : 0.05)}`,
            border: `1px solid ${getAlphaColor(extendedPalette.primary.main, effectiveMode === 'dark' ? 0.12 : 0.06)}`,
          },
        },
      },
      
      // 表单控件
      MuiOutlinedInput: {
        styleOverrides: {
          root: {
            backdropFilter: 'blur(8px)',
            WebkitBackdropFilter: 'blur(8px)',
            backgroundColor: getAlphaColor(currentBackground.paper, 0.5),
            transition: 'all 0.2s ease-in-out',
            '&:hover': {
              boxShadow: `0 2px 8px ${getAlphaColor(extendedPalette.primary.main, 0.1)}`,
            },
            '&.Mui-focused': {
              boxShadow: `0 3px 10px ${getAlphaColor(extendedPalette.primary.main, 0.15)}`,
            },
          },
        },
      },
    },
  })

  return (
    <MuiThemeProvider theme={theme}>
      <CssBaseline />
      {children}
    </MuiThemeProvider>
  )
} 