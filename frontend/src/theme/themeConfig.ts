/**
 * 主题配置管理
 * 提供主题获取和切换的核心功能
 */
import { useColorMode } from '../stores/theme'
import { themes, ThemeConfig, ThemeKeys, getAlphaColor, getExtendedPalette, getLighterColor, getDarkerColor } from './palette'
import { BORDER_RADIUS } from './variants'

// 获取当前主题模式
export function getCurrentThemeMode(): 'light' | 'dark' {
  return useColorMode.getState().getEffectiveMode()
}

// 获取当前生效的主题配置
export function getCurrentTheme(): ThemeConfig {
  const mode = getCurrentThemeMode()
  return themes[mode]
}

// 获取当前的扩展调色板 - 包含派生颜色
export function getCurrentExtendedPalette() {
  return getExtendedPalette(getCurrentTheme())
}

// 获取当前主题的背景色
export function getCurrentBackground() {
  return getCurrentExtendedPalette().background
}

// 获取指定主题的配置
export function getTheme(themeName: ThemeKeys): ThemeConfig {
  return themes[themeName] || themes['light'] // 默认返回浅色主题
}

// 兼容旧的条形图颜色映射
export const metricColors: Record<string, string> = {
  get messages() { 
    return getCurrentExtendedPalette().secondary.main
  },
  get sandbox_calls() { 
    return getCurrentExtendedPalette().warning 
  },
  get success_calls() { 
    return getCurrentExtendedPalette().success 
  },
  get failed_calls() { 
    return getCurrentExtendedPalette().error 
  },
  get success_rate() { 
    return getCurrentExtendedPalette().secondary.main 
  },
}

// UI元素样式生成器对象
export const UI_STYLES = {
  // 获取边框样式
  getBorder: (opacity: number = 0.1): string => {
    const palette = getCurrentExtendedPalette()
    return `1px solid ${getAlphaColor(palette.primary.main, opacity)}`
  },
  
  // 获取阴影样式
  getShadow: (depth: 'light' | 'medium' | 'deep'): string => {
    const mode = getCurrentThemeMode()
    const palette = getCurrentExtendedPalette()
    
    switch (depth) {
      case 'light':
        return mode === 'light' 
          ? `0 2px 8px rgba(0, 0, 0, 0.08), 0 0 1px rgba(0, 0, 0, 0.03), 0 1px 3px ${getAlphaColor(palette.primary.main, 0.05)}`
          : `0 2px 8px rgba(0, 0, 0, 0.25), 0 0 2px rgba(0, 0, 0, 0.1), 0 1px 3px ${getAlphaColor(palette.primary.main, 0.1)}`
      case 'medium':
        return mode === 'light'
          ? `0 4px 12px rgba(0, 0, 0, 0.12), 0 1px 4px rgba(0, 0, 0, 0.05), 0 2px 6px ${getAlphaColor(palette.primary.main, 0.08)}`
          : `0 4px 12px rgba(0, 0, 0, 0.35), 0 1px 4px rgba(0, 0, 0, 0.15), 0 2px 6px ${getAlphaColor(palette.primary.main, 0.12)}`
      case 'deep':
        return mode === 'light'
          ? `0 8px 20px rgba(0, 0, 0, 0.15), 0 2px 8px rgba(0, 0, 0, 0.06), 0 3px 12px ${getAlphaColor(palette.primary.main, 0.1)}`
          : `0 8px 20px rgba(0, 0, 0, 0.4), 0 2px 8px rgba(0, 0, 0, 0.2), 0 3px 12px ${getAlphaColor(palette.primary.main, 0.15)}`
      default:
        return mode === 'light'
          ? `0 2px 8px rgba(0, 0, 0, 0.08), 0 0 1px rgba(0, 0, 0, 0.03)`
          : `0 2px 8px rgba(0, 0, 0, 0.25), 0 0 2px rgba(0, 0, 0, 0.1)`
    }
  },
  
  // 获取渐变背景
  getGradient: (type: 'primary' | 'secondary' | 'background' | 'card'): string => {
    const palette = getCurrentExtendedPalette()
    const background = palette.background
    const mode = getCurrentThemeMode()
    
    switch (type) {
      case 'primary':
        return `linear-gradient(90deg, ${getAlphaColor(palette.primary.main, 0.95)}, ${getAlphaColor(palette.primary.light, 0.95)})`
      case 'secondary':
        return `linear-gradient(90deg, ${getAlphaColor(palette.secondary.main, 0.95)}, ${getAlphaColor(palette.secondary.light, 0.95)})`
      case 'background':
        return mode === 'light'
          ? `linear-gradient(135deg, ${getAlphaColor(background.main, 0.85)} 0%, ${getLighterColor(getAlphaColor(background.main, 0.8), 0.05)} 50%, ${getAlphaColor(background.main, 0.85)} 100%)`
          : `linear-gradient(135deg, ${getAlphaColor(getDarkerColor(background.main, 0.08), 0.9)} 0%, ${getAlphaColor(background.main, 0.85)} 50%, ${getAlphaColor(getDarkerColor(background.main, 0.08), 0.9)} 100%)`
      case 'card':
        return mode === 'light'
          ? `linear-gradient(145deg, rgba(255, 255, 255, 0.92), ${getAlphaColor(background.card, 0.85)})`
          : `linear-gradient(145deg, ${getAlphaColor(getLighterColor(background.paper, 0.05), 0.85)}, ${getAlphaColor(background.paper, 0.75)})`
      default:
        return 'none'
    }
  },
  
  // 获取透明度颜色
  getAlphaColor: (color: string, opacity: number): string => {
    return getAlphaColor(color, opacity)
  },

  // 兼容旧版constants.ts中的MENU_STYLES
  get HOVER() {
    const palette = getCurrentExtendedPalette()
    return getAlphaColor(palette.primary.main, 0.1)
  },

  get SELECTED() {
    const palette = getCurrentExtendedPalette()
    return getAlphaColor(palette.primary.main, 0.18)
  },

  get SELECTED_HOVER() {
    const palette = getCurrentExtendedPalette()
    return getAlphaColor(palette.primary.main, 0.25)
  },

  // 兼容旧版constants.ts中的BORDERS
  BORDERS: {
    MENU: {
      get ACTIVE() {
        const palette = getCurrentExtendedPalette()
        return `3px solid ${palette.primary.main}`
      }
    },
    CARD: {
      get DEFAULT() {
        return UI_STYLES.getBorder()
      }
    },
    DIVIDER: {
      get DEFAULT() {
        const mode = getCurrentThemeMode()
        return `1px solid ${mode === 'light' ? 'rgba(0, 0, 0, 0.12)' : 'rgba(255, 255, 255, 0.07)'}`
      }
    }
  },

  // 兼容旧版constants.ts中的GRADIENTS
  BACKGROUND: {
    get PRIMARY() {
      return UI_STYLES.getGradient('background')
    },
    get CONTENT() {
      const mode = getCurrentThemeMode()
      const palette = getCurrentExtendedPalette()
      const background = palette.background
      
      return mode === 'light'
        ? `linear-gradient(180deg, rgba(255, 255, 255, 0.95) 0%, ${getAlphaColor(background.main, 0.95)} 100%)`
        : `linear-gradient(180deg, ${getLighterColor(background.paper, 0.05)} 0%, ${background.paper} 100%)`
    }
  },

  // 兼容旧版APP_BAR
  APP_BAR: {
    get DEFAULT() {
      const palette = getCurrentExtendedPalette()
      const mode = getCurrentThemeMode()
      const primary = palette.primary
      
      // 创建一个更优雅的渐变效果
      return mode === 'light'
        ? `linear-gradient(90deg, ${primary.main} 0%, ${primary.light} 100%)`
        : `linear-gradient(90deg, ${primary.dark} 0%, ${primary.main} 100%)`
    }
  },

  // 兼容旧版SHADOWS
  SHADOWS: {
    APP_BAR: {
      get DEFAULT() {
        return UI_STYLES.getShadow('medium')
      }
    },
    CARD: {
      get DEFAULT() {
        return UI_STYLES.getShadow('light')
      },
      get HOVER() {
        return UI_STYLES.getShadow('medium')
      }
    },
    BUTTON: {
      get DEFAULT() {
        return UI_STYLES.getShadow('light')
      },
      get HOVER() {
        return UI_STYLES.getShadow('medium')
      }
    }
  },

  // 兼容旧版CARD
  CARD: {
    get DEFAULT() {
      return UI_STYLES.getBorder()
    }
  },

  // 兼容旧版GRADIENTS.CARD
  GRADIENTS: {
    CARD: {
      get DEFAULT() {
        const mode = getCurrentThemeMode()
        const palette = getCurrentExtendedPalette()
        return mode === 'light'
          ? `linear-gradient(135deg, rgba(255, 255, 255, 0.95), ${getAlphaColor(palette.primary.lighter, 0.08)})`
          : `linear-gradient(135deg, ${getAlphaColor(palette.primary.darker, 0.15)}, ${getAlphaColor(palette.background.paper, 0.95)})`
      },
      get STATISTIC() {
        const mode = getCurrentThemeMode()
        const palette = getCurrentExtendedPalette()
        return mode === 'light'
          ? `linear-gradient(135deg, rgba(255, 255, 255, 0.97), ${getAlphaColor(palette.primary.lighter, 0.06)})`
          : `linear-gradient(135deg, ${getAlphaColor(palette.background.paper, 0.92)}, ${getAlphaColor(palette.primary.darker, 0.12)})`
      },
      get SUCCESS() {
        const palette = getCurrentExtendedPalette()
        return `linear-gradient(135deg, ${getAlphaColor(palette.success, 0.08)}, ${getAlphaColor(palette.success, 0.02)})`
      },
      get ERROR() {
        const palette = getCurrentExtendedPalette()
        return `linear-gradient(135deg, ${getAlphaColor(palette.error, 0.08)}, ${getAlphaColor(palette.error, 0.02)})`
      },
      get WARNING() {
        const palette = getCurrentExtendedPalette()
        return `linear-gradient(135deg, ${getAlphaColor(palette.warning, 0.08)}, ${getAlphaColor(palette.warning, 0.02)})`
      },
      get INFO() {
        const palette = getCurrentExtendedPalette()
        return `linear-gradient(135deg, ${getAlphaColor(palette.info, 0.08)}, ${getAlphaColor(palette.info, 0.02)})`
      },
    },
    BUTTON: {
      get PRIMARY() {
        return UI_STYLES.getGradient('primary')
      },
      get SECONDARY() {
        return UI_STYLES.getGradient('secondary')
      }
    }
  },

  // 兼容旧版CARD_LAYOUT
  CARD_LAYOUT: {
    CHART_HEIGHT: {
      MOBILE: 180,
      DESKTOP: 200,
    },
    LOADING_HEIGHT: '200px',
    TRANSITION: 'all 0.3s ease',
    BACKDROP_FILTER: 'blur(10px)',
  }
}

// 【日志表格】样式
export const LOG_TABLE_STYLES = {
  SEVERITY: {
    // 信息日志
    get INFO() {
      const palette = getCurrentExtendedPalette()
      return {
        backgroundColor: getAlphaColor(palette.info, 0.15),
        color: palette.info,
        backdropFilter: 'blur(4px)',
        WebkitBackdropFilter: 'blur(4px)',
        borderRadius: '4px',
        padding: '2px 8px',
        transition: 'all 0.2s ease',
      }
    },
    // 调试日志
    get DEBUG() {
      const palette = getCurrentExtendedPalette()
      return {
        backgroundColor: getAlphaColor(palette.secondary.main, 0.15),
        color: palette.secondary.main,
        backdropFilter: 'blur(4px)',
        WebkitBackdropFilter: 'blur(4px)',
        borderRadius: '4px',
        padding: '2px 8px',
        transition: 'all 0.2s ease',
      }
    },
    // 错误日志
    get ERROR() {
      const palette = getCurrentExtendedPalette()
      return {
        backgroundColor: getAlphaColor(palette.error, 0.15),
        color: palette.error,
        backdropFilter: 'blur(4px)',
        WebkitBackdropFilter: 'blur(4px)',
        borderRadius: '4px',
        padding: '2px 8px',
        transition: 'all 0.2s ease',
      }
    },
    // 警告日志
    get WARNING() {
      const palette = getCurrentExtendedPalette()
      return {
        backgroundColor: getAlphaColor(palette.warning, 0.15),
        color: palette.warning,
        backdropFilter: 'blur(4px)',
        WebkitBackdropFilter: 'blur(4px)',
        borderRadius: '4px',
        padding: '2px 8px',
        transition: 'all 0.2s ease',
      }
    },
    // 成功日志
    get SUCCESS() {
      const palette = getCurrentExtendedPalette()
      return {
        backgroundColor: getAlphaColor(palette.success, 0.15),
        color: palette.success,
        backdropFilter: 'blur(4px)',
        WebkitBackdropFilter: 'blur(4px)',
        borderRadius: '4px',
        padding: '2px 8px',
        transition: 'all 0.2s ease',
      }
    },
  },
  ROW: {
    // 交替行样式
    get ALTERNATE() {
      const mode = getCurrentThemeMode()
      return mode === 'light' ? 'rgba(250, 245, 245, 0.5)' : 'rgba(39, 35, 36, 0.3)'
    },
    // 悬停样式
    get HOVER() {
      const mode = getCurrentThemeMode()
      const palette = getCurrentExtendedPalette()
      return getAlphaColor(palette.primary.main, mode === 'light' ? 0.1 : 0.15)
    }
  },
  // 表格容器样式
  CONTAINER: {
    get styles() {
      const mode = getCurrentThemeMode()
      const palette = getCurrentExtendedPalette()
      return {
        backdropFilter: 'blur(12px)',
        WebkitBackdropFilter: 'blur(12px)',
        backgroundColor: mode === 'light' 
          ? 'rgba(255, 255, 255, 0.85)' 
          : getAlphaColor(palette.background.paper, 0.85),
        borderRadius: '6px',
        border: `1px solid ${getAlphaColor(palette.primary.main, mode === 'light' ? 0.06 : 0.1)}`,
        boxShadow: mode === 'light'
          ? '0 2px 8px rgba(0, 0, 0, 0.08), 0 0 1px rgba(0, 0, 0, 0.03)'
          : `0 2px 8px rgba(0, 0, 0, 0.25), 0 0 2px rgba(0, 0, 0, 0.1)`,
        overflow: 'hidden',
        transition: 'all 0.3s ease',
        position: 'relative',
        '&::before': {
          content: '""',
          position: 'absolute',
          top: 0,
          left: 0,
          width: '100%',
          height: '2px',
          background: `linear-gradient(90deg, ${getAlphaColor(palette.primary.main, 0.2)}, ${getAlphaColor(palette.secondary.main, 0.2)})`,
          opacity: 0.7,
        },
        '&:hover': {
          boxShadow: mode === 'light'
            ? '0 4px 12px rgba(0, 0, 0, 0.12), 0 1px 4px rgba(0, 0, 0, 0.05)'
            : '0 4px 12px rgba(0, 0, 0, 0.35), 0 1px 4px rgba(0, 0, 0, 0.15)',
        }
      }
    }
  },
  // 表头样式
  HEADER: {
    get styles() {
      const mode = getCurrentThemeMode()
      const palette = getCurrentExtendedPalette()
      return {
        fontWeight: 600,
        backgroundColor: mode === 'light' 
          ? 'rgba(245, 245, 245, 0.8)' 
          : getAlphaColor(palette.primary.darker, 0.4),
        backdropFilter: 'blur(10px)',
        WebkitBackdropFilter: 'blur(10px)',
        boxShadow: mode === 'dark' 
          ? '0 4px 6px -1px rgba(0, 0, 0, 0.15)'
          : '0 4px 6px -1px rgba(0, 0, 0, 0.08)',
        textTransform: 'uppercase',
        fontSize: '0.75rem',
        letterSpacing: '0.02em',
        backgroundImage: mode === 'light'
          ? `linear-gradient(180deg, rgba(255, 255, 255, 0.95), rgba(245, 245, 245, 0.85))`
          : `linear-gradient(180deg, ${getAlphaColor(palette.primary.darker, 0.5)}, ${getAlphaColor(palette.primary.darker, 0.4)})`,
      }
    }
  }
}

// 【登录页面】样式
export const LOGIN_PAGE_STYLES = {
  // 背景渐变
  get BACKGROUND() {
    return UI_STYLES.getGradient('background')
  },
  // 卡片样式
  get CARD() {
    return UI_STYLES.getGradient('card')
  },
  // 阴影样式
  get SHADOW() {
    const mode = getCurrentThemeMode()
    const palette = getCurrentExtendedPalette()
    return {
      CARD: UI_STYLES.getShadow('medium'),
      CARD_HOVER: UI_STYLES.getShadow('deep'),
      BUTTON: mode === 'light' 
        ? `0 2px 10px ${getAlphaColor(palette.primary.main, 0.25)}`
        : `0 2px 10px ${getAlphaColor(palette.primary.main, 0.35)}`,
      BUTTON_HOVER: mode === 'light'
        ? `0 6px 15px ${getAlphaColor(palette.primary.main, 0.35)}`
        : `0 6px 15px ${getAlphaColor(palette.primary.main, 0.45)}`
    }
  },
  // 边框样式
  get BORDER() {
    return UI_STYLES.getBorder()
  }
}

// 指标名称映射
export const metricNames = {
  messages: '消息数',
  sandbox_calls: '沙盒调用',
  success_calls: '成功调用',
  failed_calls: '失败调用',
  success_rate: '成功率',
}

// 导出兼容旧常量
export const GRADIENTS = UI_STYLES.GRADIENTS
export const SHADOWS = UI_STYLES.SHADOWS
export const BORDERS = UI_STYLES.BORDERS
export const MENU_STYLES = {
  SELECTED: UI_STYLES.SELECTED,
  SELECTED_HOVER: UI_STYLES.SELECTED_HOVER,
  HOVER: UI_STYLES.HOVER
}
export const CARD_LAYOUT = UI_STYLES.CARD_LAYOUT
export { BORDER_RADIUS } 