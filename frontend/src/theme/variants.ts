/**
 * 主题样式变体配置文件
 * 用于定义各种UI组件的通用样式变体
 */
/* cspell:ignore glassmorphism bgcolor */
import { SxProps, Theme, alpha } from '@mui/material'
import { UI_STYLES } from './themeConfig'
import { getCurrentExtendedPalette, getCurrentThemeMode } from './themeConfig'
import { getStopTypeColorValue } from './utils'
import { getShadow, getBackdropFilter, getTransition } from './themeApi'

// 圆角常量
export const BORDER_RADIUS = {
  LARGE: '12px',
  DEFAULT: '8px',
  SMALL: '4px',
  PILL: '9999px',
  MEDIUM: '10px',
}

// 布局常量
export const LAYOUT = {
  Z_INDEX: {
    BACKDROP: 10,
    DRAWER: 1200,
    MODAL: 1300,
    SNACKBAR: 1400,
    TOOLTIP: 1500,
  },
  TRANSITION: {
    DEFAULT: {
      get transition() {
        return getTransition('all 0.3s ease')
      },
    },
    SLOW: {
      get transition() {
        return getTransition('all 0.5s ease')
      },
    },
    FAST: {
      get transition() {
        return getTransition('all 0.15s ease')
      },
    },
  },
}

// 卡片组件样式变体
export const CARD_VARIANTS = {
  default: {
    get styles(): SxProps<Theme> {
      const mode = getCurrentThemeMode()

      return {
        // 半透明背景以支持毛玻璃效果
        backgroundColor:
          mode === 'dark'
            ? 'rgba(47, 47, 47, 0.75)' // 深色模式：中等透明度
            : 'rgba(255, 255, 255, 0.75)', // 浅色模式：中等透明度
        transition: LAYOUT.TRANSITION.DEFAULT.transition,
        backdropFilter: getBackdropFilter('blur(16px) saturate(1.1)'),
        WebkitBackdropFilter: getBackdropFilter('blur(16px) saturate(1.1)'),
        boxShadow: getShadow('0 4px 6px rgba(0, 0, 0, 0.05)'),
        border: '1px solid',
        borderColor: mode === 'dark' ? 'rgba(255, 255, 255, 0.12)' : 'rgba(0, 0, 0, 0.08)',
        borderRadius: BORDER_RADIUS.DEFAULT,
        // 确保内容可读性
        position: 'relative',
        overflow: 'hidden',
        '&:hover': {
          backgroundColor:
            mode === 'dark'
              ? 'rgba(47, 47, 47, 0.85)' // hover 时稍微增加不透明度
              : 'rgba(255, 255, 255, 0.85)',
          borderColor: mode === 'dark' ? 'rgba(255, 255, 255, 0.2)' : 'rgba(0, 0, 0, 0.12)',
          boxShadow: getShadow('0 8px 24px rgba(0, 0, 0, 0.12)'),
        },
      }
    },
  },
  elevated: {
    get styles(): SxProps<Theme> {
      const extendedPalette = getCurrentExtendedPalette()
      const primary = extendedPalette.primary

      return {
        backgroundColor: extendedPalette.background.paper,
        boxShadow: 'none',
        border: `1px solid ${alpha(primary.main, 0.12)}`,
        borderRadius: BORDER_RADIUS.DEFAULT,
        '&:hover': {
          boxShadow: UI_STYLES.getShadow('light'),
          borderColor: alpha(primary.main, 0.2),
        },
      }
    },
  },
  glassmorphism: {
    get styles(): SxProps<Theme> {
      const mode = getCurrentThemeMode()

      return {
        // 强透明效果用于现代毛玻璃设计
        backgroundColor:
          mode === 'dark'
            ? 'rgba(30, 30, 30, 0.4)' // 深色模式：强透明
            : 'rgba(255, 255, 255, 0.3)', // 浅色模式：强透明
        transition: LAYOUT.TRANSITION.DEFAULT.transition,
        backdropFilter: getBackdropFilter('blur(24px) saturate(1.4) brightness(1.1)'),
        WebkitBackdropFilter: getBackdropFilter('blur(24px) saturate(1.4) brightness(1.1)'),
        boxShadow: getShadow('0 8px 32px rgba(0, 0, 0, 0.06)'),
        border: '1px solid',
        borderColor: mode === 'dark' ? 'rgba(255, 255, 255, 0.15)' : 'rgba(255, 255, 255, 0.6)',
        borderRadius: BORDER_RADIUS.DEFAULT,
        position: 'relative',
        overflow: 'hidden',
        // 添加内光效果
        '&:before': {
          content: '""',
          position: 'absolute',
          top: 0,
          left: 0,
          right: 0,
          height: '1px',
          background:
            mode === 'dark'
              ? 'linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.3), transparent)'
              : 'linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.8), transparent)',
          zIndex: 1,
        },
        '&:hover': {
          backgroundColor: mode === 'dark' ? 'rgba(30, 30, 30, 0.6)' : 'rgba(255, 255, 255, 0.5)',
          borderColor: mode === 'dark' ? 'rgba(255, 255, 255, 0.25)' : 'rgba(255, 255, 255, 0.8)',
          boxShadow: getShadow('0 16px 64px rgba(0, 0, 0, 0.12)'),
          transform: 'translateY(-1px)',
        },
      }
    },
  },
  transparent: {
    get styles(): SxProps<Theme> {
      return {
        background: 'transparent',
      }
    },
  },
}

// 统一统计卡片样式（与工作区管理顶部卡片一致）
export const STAT_CARD_VARIANTS = {
  container(color: string, _active: boolean = false): SxProps<Theme> {
    return {
      ...CARD_VARIANTS.default.styles,
    }
  },
  icon(color: string): SxProps<Theme> {
    return {
      color,
      bgcolor: alpha(color, 0.1),
      borderRadius: 2,
      p: 1.1,
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      flexShrink: 0,
    }
  },
}

// 按钮组件样式变体
export const BUTTON_VARIANTS = {
  primary: {
    get styles(): SxProps<Theme> {
      const mode = getCurrentThemeMode()
      const palette = getCurrentExtendedPalette()
      return {
        backgroundColor: palette.primary.main,
        color: '#fff',
        boxShadow:
          mode === 'light'
            ? `0 4px 12px ${alpha(palette.primary.main, 0.18)}`
            : `0 6px 16px ${alpha(palette.primary.main, 0.22)}`,
        '&:hover': {
          backgroundColor: palette.primary.dark,
          boxShadow:
            mode === 'light'
              ? `0 6px 14px ${alpha(palette.primary.main, 0.22)}`
              : `0 8px 18px ${alpha(palette.primary.main, 0.28)}`,
        },
        transition: LAYOUT.TRANSITION.DEFAULT.transition,
        borderRadius: BORDER_RADIUS.DEFAULT,
        textTransform: 'none',
      }
    },
  },
  secondary: {
    get styles(): SxProps<Theme> {
      const primary = getCurrentExtendedPalette().primary
      return {
        color: primary.main,
        background: alpha(primary.main, 0.1),
        boxShadow: UI_STYLES.getShadow('light'),
        borderRadius: BORDER_RADIUS.DEFAULT,
        transition: LAYOUT.TRANSITION.DEFAULT.transition,
        textTransform: 'none',
        '&:hover': {
          background: alpha(primary.main, 0.2),
        },
      }
    },
  },
}

export const ACTION_BUTTON_VARIANTS = {
  primary: {
    get styles(): SxProps<Theme> {
      const mode = getCurrentThemeMode()
      const palette = getCurrentExtendedPalette()
      return {
        minHeight: 36,
        px: 1.5,
        borderRadius: BORDER_RADIUS.DEFAULT,
        color: '#fff',
        backgroundColor: palette.primary.main,
        boxShadow:
          mode === 'light'
            ? `0 4px 12px ${alpha(palette.primary.main, 0.18)}`
            : `0 6px 16px ${alpha(palette.primary.main, 0.24)}`,
        '&:hover': {
          backgroundColor: palette.primary.dark,
          boxShadow:
            mode === 'light'
              ? `0 6px 14px ${alpha(palette.primary.main, 0.22)}`
              : `0 8px 18px ${alpha(palette.primary.main, 0.28)}`,
        },
      }
    },
  },
  secondary: {
    get styles(): SxProps<Theme> {
      const mode = getCurrentThemeMode()
      const palette = getCurrentExtendedPalette()
      return {
        minHeight: 36,
        px: 1.5,
        borderRadius: BORDER_RADIUS.DEFAULT,
        color: palette.primary.main,
        backgroundColor:
          mode === 'light'
            ? alpha(palette.background.paper, 0.94)
            : alpha(palette.background.paper, 0.72),
        border: `1px solid ${alpha(palette.primary.main, mode === 'light' ? 0.18 : 0.24)}`,
        boxShadow:
          mode === 'light'
            ? '0 4px 12px rgba(15, 23, 42, 0.05)'
            : '0 6px 16px rgba(0, 0, 0, 0.18)',
        '&:hover': {
          backgroundColor:
            mode === 'light'
              ? alpha(palette.primary.main, 0.06)
              : alpha(palette.primary.main, 0.12),
          borderColor: alpha(palette.primary.main, mode === 'light' ? 0.26 : 0.32),
        },
      }
    },
  },
  ghost: {
    get styles(): SxProps<Theme> {
      const mode = getCurrentThemeMode()
      return {
        minHeight: 36,
        px: 1.25,
        borderRadius: BORDER_RADIUS.DEFAULT,
        color: mode === 'light' ? 'rgba(0, 0, 0, 0.72)' : 'rgba(255, 255, 255, 0.82)',
        backgroundColor: 'transparent',
        '&:hover': {
          backgroundColor:
            mode === 'light'
              ? 'rgba(0, 0, 0, 0.045)'
              : 'rgba(255, 255, 255, 0.08)',
        },
      }
    },
  },
  danger: {
    get styles(): SxProps<Theme> {
      const mode = getCurrentThemeMode()
      const palette = getCurrentExtendedPalette()
      return {
        minHeight: 36,
        px: 1.5,
        borderRadius: BORDER_RADIUS.DEFAULT,
        color: palette.error,
        backgroundColor:
          mode === 'light'
            ? alpha(palette.error, 0.08)
            : alpha(palette.error, 0.16),
        border: `1px solid ${alpha(palette.error, mode === 'light' ? 0.18 : 0.26)}`,
        '&:hover': {
          backgroundColor:
            mode === 'light'
              ? alpha(palette.error, 0.12)
              : alpha(palette.error, 0.22),
          borderColor: alpha(palette.error, mode === 'light' ? 0.26 : 0.34),
        },
      }
    },
  },
}

export const ICON_ACTION_BUTTON_VARIANTS = {
  subtle: {
    get styles(): SxProps<Theme> {
      const mode = getCurrentThemeMode()
      return {
        borderRadius: BORDER_RADIUS.DEFAULT,
        color: mode === 'light' ? 'text.secondary' : 'rgba(255, 255, 255, 0.74)',
        '&:hover': {
          backgroundColor:
            mode === 'light'
              ? 'rgba(0, 0, 0, 0.045)'
              : 'rgba(255, 255, 255, 0.08)',
        },
      }
    },
  },
  primary: {
    get styles(): SxProps<Theme> {
      const mode = getCurrentThemeMode()
      const palette = getCurrentExtendedPalette()
      return {
        borderRadius: BORDER_RADIUS.DEFAULT,
        color: palette.primary.main,
        '&:hover': {
          backgroundColor:
            mode === 'light'
              ? alpha(palette.primary.main, 0.08)
              : alpha(palette.primary.main, 0.16),
        },
      }
    },
  },
  danger: {
    get styles(): SxProps<Theme> {
      const mode = getCurrentThemeMode()
      const palette = getCurrentExtendedPalette()
      return {
        borderRadius: BORDER_RADIUS.DEFAULT,
        color: palette.error,
        '&:hover': {
          backgroundColor:
            mode === 'light'
              ? alpha(palette.error, 0.08)
              : alpha(palette.error, 0.18),
        },
      }
    },
  },
}

export type SegmentedControlDensity = 'comfortable' | 'compact' | 'tight'

const SEGMENTED_CONTROL_METRICS: Record<
  SegmentedControlDensity,
  {
    containerRadius: string
    minHeight: number
    borderRadius: string
    paddingX: number
    paddingY: number
    fontSize: string
    iconSize: number
    gap: number
  }
> = {
  comfortable: {
    containerRadius: BORDER_RADIUS.MEDIUM,
    minHeight: 36,
    borderRadius: BORDER_RADIUS.DEFAULT,
    paddingX: 1.5,
    paddingY: 0.75,
    fontSize: '0.875rem',
    iconSize: 18,
    gap: 0.75,
  },
  compact: {
    containerRadius: BORDER_RADIUS.DEFAULT,
    minHeight: 32,
    borderRadius: BORDER_RADIUS.DEFAULT,
    paddingX: 1.25,
    paddingY: 0.5,
    fontSize: '0.8125rem',
    iconSize: 16,
    gap: 0.5,
  },
  tight: {
    containerRadius: BORDER_RADIUS.DEFAULT,
    minHeight: 28,
    borderRadius: BORDER_RADIUS.SMALL,
    paddingX: 0.875,
    paddingY: 0.25,
    fontSize: '0.75rem',
    iconSize: 15,
    gap: 0.375,
  },
}

export const SEGMENTED_CONTROL_VARIANTS = {
  container: (density: SegmentedControlDensity = 'compact'): SxProps<Theme> => {
    const palette = getCurrentExtendedPalette()
    const mode = getCurrentThemeMode()
    const metrics = SEGMENTED_CONTROL_METRICS[density]

    return {
      display: 'inline-flex',
      alignItems: 'center',
      gap: 0.375,
      padding: 0.25,
      borderRadius: metrics.containerRadius,
      backgroundColor:
        mode === 'light'
          ? alpha(palette.background.paper, 0.92)
          : alpha(palette.background.paper, 0.78),
      boxShadow:
        mode === 'light'
          ? 'inset 0 1px 0 rgba(255, 255, 255, 0.95), 0 4px 12px rgba(15, 23, 42, 0.05)'
          : `inset 0 1px 0 ${alpha('#ffffff', 0.05)}, 0 6px 16px rgba(0, 0, 0, 0.2)`,
      border: `1px solid ${
        mode === 'light'
          ? alpha(palette.primary.main, 0.08)
          : alpha('#ffffff', 0.08)
      }`,
      backdropFilter: getBackdropFilter('blur(14px) saturate(1.05)'),
      WebkitBackdropFilter: getBackdropFilter('blur(14px) saturate(1.05)'),
      '& .MuiToggleButtonGroup-grouped': {
        margin: 0,
        border: 0,
        borderRadius: `${metrics.borderRadius} !important`,
      },
    }
  },
  item: (
    density: SegmentedControlDensity = 'compact',
    iconOnly: boolean = false
  ): SxProps<Theme> => {
    const palette = getCurrentExtendedPalette()
    const mode = getCurrentThemeMode()
    const metrics = SEGMENTED_CONTROL_METRICS[density]

    return {
      minHeight: metrics.minHeight,
      minWidth: iconOnly ? metrics.minHeight : 'auto',
      px: iconOnly ? 0 : metrics.paddingX,
      py: metrics.paddingY,
      border: 0,
      color:
        mode === 'light'
          ? 'rgba(0, 0, 0, 0.68)'
          : 'rgba(255, 255, 255, 0.82)',
      fontSize: metrics.fontSize,
      fontWeight: 600,
      lineHeight: 1,
      textTransform: 'none',
      transition: 'all 0.18s ease',
      '&:hover': {
        backgroundColor:
          mode === 'light'
            ? alpha(palette.primary.main, 0.07)
            : alpha(palette.primary.main, 0.14),
        color:
          mode === 'light'
            ? 'rgba(0, 0, 0, 0.87)'
            : 'rgba(255, 255, 255, 0.95)',
      },
      '&.Mui-selected': {
        color: palette.primary.main,
        backgroundColor:
          mode === 'light'
            ? alpha(palette.primary.main, 0.12)
            : alpha(palette.primary.main, 0.2),
        boxShadow:
          mode === 'light'
            ? `0 6px 14px ${alpha(palette.primary.main, 0.12)}`
            : `0 8px 18px ${alpha(palette.primary.main, 0.18)}`,
      },
      '&.Mui-selected:hover': {
        backgroundColor:
          mode === 'light'
            ? alpha(palette.primary.main, 0.16)
            : alpha(palette.primary.main, 0.24),
      },
      '&.Mui-disabled': {
        opacity: 0.45,
      },
      '& .segmented-control-content': {
        display: 'inline-flex',
        alignItems: 'center',
        justifyContent: 'center',
        gap: metrics.gap,
        minWidth: 0,
      },
      '& .segmented-control-icon': {
        display: 'inline-flex',
        alignItems: 'center',
        justifyContent: 'center',
        fontSize: metrics.iconSize,
        '& > *': {
          fontSize: metrics.iconSize,
        },
      },
    }
  },
}

export const TAB_BAR_VARIANTS = {
  get page(): SxProps<Theme> {
    const mode = getCurrentThemeMode()
    const palette = getCurrentExtendedPalette()

    return {
      minHeight: 48,
      '& .MuiTab-root': {
        minHeight: 48,
        fontSize: '0.875rem',
        fontWeight: 600,
        textTransform: 'none',
        transition: 'all 0.2s ease',
        borderRadius: BORDER_RADIUS.DEFAULT,
        mx: 0.5,
        px: 1.5,
        color:
          mode === 'light'
            ? 'rgba(0, 0, 0, 0.68)'
            : 'rgba(255, 255, 255, 0.82)',
        '&:hover': {
          backgroundColor:
            mode === 'light'
              ? 'rgba(0, 0, 0, 0.04)'
              : 'rgba(255, 255, 255, 0.08)',
        },
        '&.Mui-selected': {
          color: palette.primary.main,
          backgroundColor:
            mode === 'light'
              ? alpha(palette.primary.main, 0.1)
              : alpha(palette.primary.main, 0.18),
        },
      },
      '& .MuiTabs-indicator': {
        height: 3,
        borderRadius: '2px',
        backgroundColor: palette.primary.main,
        boxShadow: `0 0 8px ${alpha(palette.primary.main, 0.7)}`,
      },
    }
  },
  get panelContainer(): SxProps<Theme> {
    const mode = getCurrentThemeMode()
    const palette = getCurrentExtendedPalette()

    return {
      px: 1,
      py: 0.75,
      border: 1,
      borderColor:
        mode === 'light'
          ? alpha(palette.primary.main, 0.08)
          : alpha('#ffffff', 0.08),
      borderRadius: 2,
      backgroundColor:
        mode === 'light'
          ? alpha(palette.background.paper, 0.96)
          : alpha(palette.background.paper, 0.78),
      boxShadow:
        mode === 'dark'
          ? `inset 0 1px 0 ${alpha('#ffffff', 0.04)}, 0 6px 18px rgba(0, 0, 0, 0.18)`
          : 'inset 0 1px 0 rgba(255, 255, 255, 0.92), 0 8px 20px rgba(15, 23, 42, 0.06)',
    }
  },
  get panel(): SxProps<Theme> {
    const mode = getCurrentThemeMode()
    const palette = getCurrentExtendedPalette()

    return {
      minHeight: 44,
      '& .MuiTabs-flexContainer': {
        gap: 0.5,
      },
      '& .MuiTab-root': {
        minWidth: 100,
        minHeight: 36,
        fontSize: '0.9rem',
        fontWeight: 600,
        textTransform: 'none',
        borderRadius: BORDER_RADIUS.DEFAULT,
        color:
          mode === 'light'
            ? 'rgba(0, 0, 0, 0.64)'
            : 'rgba(255, 255, 255, 0.78)',
        transition: 'all 0.2s ease',
        '&:hover': {
          backgroundColor:
            mode === 'light'
              ? 'rgba(0, 0, 0, 0.035)'
              : 'rgba(255, 255, 255, 0.06)',
        },
        '&.Mui-selected': {
          color: palette.primary.main,
          bgcolor:
            mode === 'light'
              ? alpha(palette.primary.main, 0.08)
              : alpha(palette.primary.main, 0.14),
        },
      },
      '& .MuiTabs-indicator': {
        height: 3,
        borderRadius: 999,
        backgroundColor: palette.primary.main,
        boxShadow: `0 0 6px ${alpha(palette.primary.main, 0.5)}`,
      },
    }
  },
  get inline(): SxProps<Theme> {
    const mode = getCurrentThemeMode()
    const palette = getCurrentExtendedPalette()

    return {
      minHeight: 40,
      '& .MuiTab-root': {
        minHeight: 40,
        fontSize: '0.85rem',
        fontWeight: 600,
        textTransform: 'none',
        color:
          mode === 'light'
            ? 'rgba(0, 0, 0, 0.62)'
            : 'rgba(255, 255, 255, 0.76)',
      },
      '& .MuiTab-root.Mui-selected': {
        color: palette.primary.main,
      },
      '& .MuiTabs-indicator': {
        height: 2,
        borderRadius: '1px',
        backgroundColor: palette.primary.main,
      },
    }
  },
  get editor(): SxProps<Theme> {
    return {
      '& .MuiTab-root': {
        color: theme => alpha(theme.palette.common.white, 0.7),
        minHeight: '36px',
        padding: '6px 12px',
        textTransform: 'none',
        '&.Mui-selected': {
          color: 'common.white',
          fontWeight: 'bold',
          textShadow: '0 1px 2px rgba(0,0,0,0.2)',
        },
      },
      '& .MuiTabs-indicator': {
        backgroundColor: 'common.white',
        height: 3,
      },
    }
  },
}

// 输入框样式变体
export const INPUT_VARIANTS = {
  default: {
    get styles(): SxProps<Theme> {
      const extendedPalette = getCurrentExtendedPalette()
      const primary = extendedPalette.primary
      return {
        '& .MuiOutlinedInput-root': {
          transition: LAYOUT.TRANSITION.DEFAULT.transition,
          '& fieldset': {
            borderColor: `${alpha(primary.main, 0.2)}`,
          },
          '&:hover fieldset': {
            borderColor: `${alpha(primary.main, 0.3)}`,
          },
          '&.Mui-focused fieldset': {
            borderColor: primary.main,
          },
        },
      }
    },
  },
}

// 状态徽章样式变体
export const BADGE_VARIANTS = {
  // 基础徽章样式
  base: {
    display: 'inline-flex',
    alignItems: 'center',
    justifyContent: 'center',
    padding: '4px 8px',
    borderRadius: BORDER_RADIUS.PILL,
    fontSize: '0.75rem',
    fontWeight: 500,
    height: '22px',
  },

  // 状态徽章生成器
  getStatusBadge: (color: string): SxProps<Theme> => {
    return {
      ...BADGE_VARIANTS.base,
      backgroundColor: alpha(color, 0.15),
      color: color,
    }
  },
}

// 状态Chip样式变体 - 提供统一的Chip样式
export const CHIP_VARIANTS = {
  // 基础Chip样式
  base: (isSmall: boolean = false): SxProps<Theme> => ({
    height: isSmall ? 20 : 24,
    fontSize: isSmall ? '0.65rem' : '0.75rem',
    minWidth: '52px',
    '& .MuiChip-label': {
      px: isSmall ? 0.5 : 0.75,
    },
  }),

  // 基础Chip样式 - 带颜色
  baseWithColor: (isSmall: boolean = false, color: string = ''): SxProps<Theme> => ({
    ...CHIP_VARIANTS.base(isSmall),
    backgroundColor: alpha(color, 0.12),
    color: color,
    borderColor: alpha(color, 0.2),
    '& .MuiChip-icon': {
      color: color,
    },
  }),

  // 获取状态类型的Chip样式 - 使用纯函数而非Hooks
  getStatusChip: (_colorName: string, isSmall: boolean = false): SxProps<Theme> => {
    // 直接返回基础样式，颜色将由组件中的color属性决定
    return {
      ...CHIP_VARIANTS.base(isSmall),
      // 这里不设置颜色，将由MUI Chip组件的color属性设置
    }
  },

  // 自定义颜色的Chip样式 - 使用直接传入的颜色值
  getCustomColorChip: (color: string, isSmall: boolean = false): SxProps<Theme> => {
    return {
      ...CHIP_VARIANTS.base(isSmall),
      backgroundColor: alpha(color, 0.12),
      color: color,
      borderColor: alpha(color, 0.2),
      '& .MuiChip-icon': {
        color: color,
      },
    }
  },

  // 停止类型Chip样式
  getStopTypeChip: (stopType: number, isSmall: boolean = false): SxProps<Theme> => {
    const color = getStopTypeColorValue(stopType)

    return {
      ...CHIP_VARIANTS.base(isSmall),
      backgroundColor: alpha(color, 0.12),
      color: color,
      borderColor: alpha(color, 0.2),
    }
  },

  // 流式模式Chip样式
  getStreamModeChip: (isStream: boolean, isSmall: boolean = false): SxProps<Theme> => {
    const palette = getCurrentExtendedPalette()
    const color = isStream ? palette.primary.main : palette.secondary.main

    return {
      ...CHIP_VARIANTS.base(isSmall),
      backgroundColor: alpha(color, 0.12),
      color: color,
      borderColor: alpha(color, 0.2),
    }
  },

  // 日志级别Chip样式
  getLogLevelChip: (level: string, isSmall: boolean = false): SxProps<Theme> => {
    const normalizedLevel = level.toUpperCase()

    const levelStyle = (() => {
      if (Object.keys(LOG_TABLE_STYLES.SEVERITY).includes(normalizedLevel)) {
        return LOG_TABLE_STYLES.SEVERITY[normalizedLevel as keyof typeof LOG_TABLE_STYLES.SEVERITY]
      }
      return { backgroundColor: 'rgba(160, 160, 160, 0.15)', color: '#9e9e9e' }
    })()

    return {
      ...CHIP_VARIANTS.base(isSmall),
      ...levelStyle,
    }
  },

  // 用户角色Chip样式
  getRoleChip: (permLevel: number, isSmall: boolean = false): SxProps<Theme> => {
    // 角色颜色映射
    const roleColors = {
      0: '#9e9e9e', // 访客
      1: '#1976d2', // 用户
      2: '#9c27b0', // 管理员
      3: '#f44336', // 超级管理员
    }

    const color = roleColors[permLevel as keyof typeof roleColors] || '#9e9e9e'

    return {
      ...CHIP_VARIANTS.base(isSmall),
      backgroundColor: alpha(color, 0.12),
      color: color,
      borderColor: alpha(color, 0.2),
    }
  },

  // 用户状态Chip样式
  getUserStatusChip: (status: string, isSmall: boolean = false): SxProps<Theme> => {
    // 状态颜色映射
    const statusColors = {
      // 英文状态名
      normal: '#4caf50', // 正常
      passive: '#ff9800', // 未激活
      banned: '#f44336', // 封禁
      // 中文状态名
      正常: '#4caf50',
      消极: '#ff9800',
      封禁: '#f44336',
      已封禁: '#f44336',
      禁止触发: '#ff9800',
      允许触发: '#4caf50',
    }

    const color = statusColors[status as keyof typeof statusColors] || '#9e9e9e'

    return {
      ...CHIP_VARIANTS.base(isSmall),
      backgroundColor: alpha(color, 0.12),
      color: color,
      borderColor: alpha(color, 0.2),
    }
  },
}

// 插件类型相关常量
export const pluginTypeColors: Record<
  string,
  'primary' | 'secondary' | 'success' | 'error' | 'warning' | 'info'
> = {
  builtin: 'primary',
  package: 'info',
  local: 'warning',
}

export const pluginTypeTexts: Record<string, string> = {
  builtin: '内置',
  package: '云端',
  local: '本地',
}

export const configTypeColors: Record<
  string,
  'primary' | 'secondary' | 'success' | 'error' | 'warning' | 'info'
> = {
  str: 'primary',
  bool: 'success',
  int: 'warning',
  float: 'warning',
  list: 'info',
}

export const methodTypeColors: Record<
  string,
  'primary' | 'secondary' | 'success' | 'error' | 'warning' | 'info'
> = {
  tool: 'info',
  agent: 'primary',
  behavior: 'success',
  multimodal_agent: 'secondary',
}

export const methodTypeTexts: Record<string, string> = {
  tool: '工具方法',
  agent: '代理方法',
  behavior: '行为方法',
  multimodal_agent: '多模态代理',
}

// 方法类型说明文本
export const methodTypeDescriptions: Record<string, string> = {
  tool: '提供给 LLM 使用的工具，返回值可以是任意类型，LLM 可获取返回值作进一步处理',
  agent:
    '用于提供 LLM 交互反馈，其返回值必须为 str 类型，描述 LLM 行为的结果，返回后会被添加到上下文中再次调用',
  behavior:
    '用于提供 LLM 交互反馈，其返回值必须为 str 类型，描述 LLM 行为的结果，返回后会被添加到上下文中但不触发再次调用',
  multimodal_agent:
    '用于提供 LLM 交互反馈，其返回值为一段多模态 message，描述 LLM 行为的结果，返回后会被添加到上下文中再次调用',
}

// 统一表格样式变体
export const UNIFIED_TABLE_STYLES = {
  get container(): SxProps<Theme> {
    const palette = getCurrentExtendedPalette()
    const mode = getCurrentThemeMode()
    return {
      backgroundColor: mode === 'light' ? palette.background.paper : alpha(palette.background.paper, 0.75),
      borderRadius: BORDER_RADIUS.DEFAULT,
      border: `1px solid ${alpha(palette.primary.main, mode === 'light' ? 0.06 : 0.1)}`,
      boxShadow: UI_STYLES.getShadow('light'),
      overflow: 'hidden',
      transition: 'box-shadow 0.3s ease',
      position: 'relative',
      height: '100%',
      '&::before': {
        content: '""',
        position: 'absolute',
        top: 0,
        left: 0,
        width: '100%',
        height: '2px',
        backgroundColor: alpha(palette.primary.main, 0.2),
        opacity: 0.8,
      },
      '&:hover': {
        boxShadow: UI_STYLES.getShadow('medium'),
      },
    }
  },

  get header(): SxProps<Theme> {
    const mode = getCurrentThemeMode()
    const palette = getCurrentExtendedPalette()
    return {
      position: 'sticky',
      top: 0,
      zIndex: 10,
      fontWeight: 600,
      backgroundColor: mode === 'light'
        ? alpha(palette.primary.main, 0.04)
        : alpha(palette.primary.darker, 0.5),
      backdropFilter: 'blur(8px)',
      WebkitBackdropFilter: 'blur(8px)',
      boxShadow:
        mode === 'dark'
          ? '0 4px 6px -1px rgba(0, 0, 0, 0.15)'
          : '0 4px 6px -1px rgba(0, 0, 0, 0.08)',
      textTransform: 'uppercase',
      fontSize: '0.75rem',
      letterSpacing: '0.02em',
    }
  },

  get row(): SxProps<Theme> {
    const palette = getCurrentExtendedPalette()
    return {
      willChange: 'background-color',
      transition: 'background-color 0.15s ease',
      '&:nth-of-type(odd)': {
        backgroundColor:
          getCurrentThemeMode() === 'light' ? 'rgba(0, 0, 0, 0.01)' : 'rgba(255, 255, 255, 0.015)',
      },
      '&:nth-of-type(even)': {
        backgroundColor: 'transparent',
      },
      '&:hover': {
        backgroundColor: `${alpha(palette.primary.main, 0.08)} !important`,
      },
    }
  },

  get cell(): SxProps<Theme> {
    const mode = getCurrentThemeMode()
    return {
      fontSize: '0.875rem',
      borderBottom: `1px solid ${mode === 'dark' ? 'rgba(255, 255, 255, 0.07)' : 'rgba(0, 0, 0, 0.06)'}`,
    }
  },

  get paper(): SxProps<Theme> {
    const palette = getCurrentExtendedPalette()
    const mode = getCurrentThemeMode()
    return {
      backgroundColor: mode === 'light' ? palette.background.paper : alpha(palette.background.paper, 0.95),
      boxShadow: UI_STYLES.getShadow('light'),
      borderRadius: BORDER_RADIUS.DEFAULT,
      border: `1px solid ${alpha(palette.primary.main, mode === 'light' ? 0.06 : 0.1)}`,
      overflow: 'hidden',
      transition: 'box-shadow 0.3s ease',
      '&:hover': {
        boxShadow: UI_STYLES.getShadow('medium'),
      },
    }
  },

  // 表格布局容器 - 添加固定高度和滚动布局的容器样式
  get tableLayoutContainer(): SxProps<Theme> {
    return {
      height: '100%',
      display: 'flex',
      flexDirection: 'column',
      overflow: 'hidden',
      gap: '6px',
    }
  },

  // 表格内容容器 - 添加滚动的内容容器样式
  get tableContentContainer(): SxProps<Theme> {
    const mode = getCurrentThemeMode()
    const palette = getCurrentExtendedPalette()
    return {
      flex: 1,
      display: 'flex',
      flexDirection: 'column',
      overflow: 'hidden',
      backgroundColor: mode === 'light' ? palette.background.paper : alpha(palette.background.paper, 0.95),
      boxShadow: UI_STYLES.getShadow('light'),
      borderRadius: BORDER_RADIUS.DEFAULT,
      border: `1px solid ${alpha(palette.primary.main, mode === 'light' ? 0.06 : 0.1)}`,
    } as SxProps<Theme>
  },

  // 表格视口样式 - 可滚动区域
  get tableViewport(): SxProps<Theme> {
    const mode = getCurrentThemeMode()
    return {
      flex: 1,
      overflow: 'auto',
      maxHeight: '100%',
      '&::-webkit-scrollbar': {
        width: '8px',
        height: '8px',
      },
      '&::-webkit-scrollbar-thumb': {
        backgroundColor: mode === 'dark' ? 'rgba(255, 255, 255, 0.16)' : 'rgba(0, 0, 0, 0.2)',
        borderRadius: '4px',
      },
      '&::-webkit-scrollbar-track': {
        backgroundColor: mode === 'dark' ? 'rgba(255, 255, 255, 0.04)' : 'rgba(0, 0, 0, 0.04)',
        borderRadius: '4px',
      },
    }
  },

  // 表格分页器样式
  get pagination(): SxProps<Theme> {
    return {
      borderTop: '1px solid',
      borderColor: 'divider',
      flexShrink: 0,
      '.MuiTablePagination-selectLabel': {
        marginBottom: 0,
      },
      '.MuiTablePagination-displayedRows': {
        marginBottom: 0,
      },
      '.MuiTablePagination-select': {
        paddingRight: 8,
      },
      '.MuiTablePagination-select, .MuiTablePagination-selectIcon': {
        pointerEvents: 'auto',
      },
    } as SxProps<Theme>
  },

  // 移动端适配的分页器样式
  getMobilePagination: (isSmall: boolean = false): SxProps<Theme> => {
    return {
      borderTop: '1px solid',
      borderColor: 'divider',
      flexShrink: 0,
      '.MuiTablePagination-selectLabel': {
        marginBottom: 0,
        display: isSmall ? 'none' : 'block',
      },
      '.MuiTablePagination-displayedRows': {
        marginBottom: 0,
        fontSize: isSmall ? '0.75rem' : 'inherit',
      },
      '.MuiTablePagination-select': {
        paddingRight: isSmall ? 0 : 8,
      },
      '.MuiTablePagination-select, .MuiTablePagination-selectIcon': {
        pointerEvents: 'auto',
      },
    } as SxProps<Theme>
  },

  // 表格基础样式
  getTableBase: (isMobile: boolean = false, isSmall: boolean = false): SxProps<Theme> => {
    return {
      width: '100%',
      minWidth: isMobile ? '600px' : '900px',
      tableLayout: 'fixed',
      padding: isSmall ? '4px' : '8px',
    }
  },

  // 表格滚动条样式
  get scrollbar(): SxProps<Theme> {
    const mode = getCurrentThemeMode()
    return {
      '&::-webkit-scrollbar': {
        width: '8px',
        height: '8px',
      },
      '&::-webkit-scrollbar-thumb': {
        backgroundColor: mode === 'dark' ? 'rgba(255, 255, 255, 0.16)' : 'rgba(0, 0, 0, 0.2)',
        borderRadius: '4px',
      },
      '&::-webkit-scrollbar-track': {
        backgroundColor: mode === 'dark' ? 'rgba(255, 255, 255, 0.04)' : 'rgba(0, 0, 0, 0.04)',
        borderRadius: '4px',
      },
    }
  },

  // 页面顶部 Tab 栏容器样式（用于 ModelsPage / SettingsPage 等）
  get pageTabContainer(): SxProps<Theme> {
    return TAB_BAR_VARIANTS.panelContainer
  },

  // 嵌套配置行样式
  get nestedRow(): SxProps<Theme> {
    const palette = getCurrentExtendedPalette()
    const mode = getCurrentThemeMode()
    return {
      willChange: 'background-color',
      transition: 'background-color 0.15s ease',
      '&:nth-of-type(odd)': {
        backgroundColor: mode === 'light' ? 'rgba(0, 0, 0, 0.012)' : 'rgba(255, 255, 255, 0.018)',
      },
      '&:nth-of-type(even)': {
        backgroundColor: 'transparent',
      },
      '&:hover': {
        backgroundColor: `${alpha(palette.primary.main, 0.08)} !important`,
      },
    }
  },

  // 嵌套配置容器样式
  get nestedContainer(): SxProps<Theme> {
    const mode = getCurrentThemeMode()
    const palette = getCurrentExtendedPalette()
    return {
      backgroundColor: mode === 'light' ? 'rgba(0, 0, 0, 0.025)' : 'rgba(255, 255, 255, 0.025)',
      borderRadius: '0',
      border: 'none',
      borderTop: `1px solid ${mode === 'light' ? 'rgba(0, 0, 0, 0.05)' : 'rgba(255, 255, 255, 0.05)'}`,
      borderBottom: `1px solid ${mode === 'light' ? 'rgba(0, 0, 0, 0.05)' : 'rgba(255, 255, 255, 0.05)'}`,
      margin: '0',
      padding: '4px 0',
      overflow: 'hidden',
      position: 'relative',
      '&::before': {
        content: '""',
        position: 'absolute',
        left: 0,
        top: 0,
        bottom: 0,
        width: '2px',
        backgroundColor: alpha(palette.primary.main, 0.4),
      },
    }
  },
}

// 导出日志表格样式到包含新的统一样式
export const LOG_TABLE_STYLES = {
  SEVERITY: {
    INFO: {
      backgroundColor: 'rgba(41, 182, 246, 0.12)',
      color: '#03a9f4',
      backdropFilter: 'blur(4px)',
      WebkitBackdropFilter: 'blur(4px)',
      borderRadius: '4px',
      padding: '2px 8px',
      transition: 'all 0.2s ease',
    },
    DEBUG: {
      backgroundColor: 'rgba(149, 117, 205, 0.12)',
      color: '#7e57c2',
      backdropFilter: 'blur(4px)',
      WebkitBackdropFilter: 'blur(4px)',
      borderRadius: '4px',
      padding: '2px 8px',
      transition: 'all 0.2s ease',
    },
    ERROR: {
      backgroundColor: 'rgba(239, 83, 80, 0.12)',
      color: '#f44336',
      backdropFilter: 'blur(4px)',
      WebkitBackdropFilter: 'blur(4px)',
      borderRadius: '4px',
      padding: '2px 8px',
      transition: 'all 0.2s ease',
    },
    WARNING: {
      backgroundColor: 'rgba(255, 167, 38, 0.12)',
      color: '#ff9800',
      backdropFilter: 'blur(4px)',
      WebkitBackdropFilter: 'blur(4px)',
      borderRadius: '4px',
      padding: '2px 8px',
      transition: 'all 0.2s ease',
    },
    SUCCESS: {
      backgroundColor: 'rgba(102, 187, 106, 0.12)',
      color: '#4caf50',
      backdropFilter: 'blur(4px)',
      WebkitBackdropFilter: 'blur(4px)',
      borderRadius: '4px',
      padding: '2px 8px',
      transition: 'all 0.2s ease',
    },
  },
  ROW: {
    get ALTERNATE() {
      const mode = getCurrentThemeMode()
      return mode === 'light' ? 'rgba(0, 0, 0, 0.018)' : 'rgba(255, 255, 255, 0.025)'
    },
    get HOVER() {
      const palette = getCurrentExtendedPalette()
      return alpha(palette.primary.main, 0.08)
    },
  },
  TABLE: {
    get styles(): SxProps<Theme> {
      return UNIFIED_TABLE_STYLES.container
    },
  },
}

// 卡片容器样式
export const CARD_CONTAINER = {
  get styles(): SxProps<Theme> {
    const extendedPalette = getCurrentExtendedPalette()
    const primary = extendedPalette.primary

    return {
      backgroundColor: extendedPalette.background.paper,
      backgroundImage: UI_STYLES.getGradient('card'),
      boxShadow: UI_STYLES.getShadow('light'),
      border: `1px solid ${alpha(primary.main, 0.05)}`,
      borderRadius: BORDER_RADIUS.DEFAULT,
      transition: LAYOUT.TRANSITION.DEFAULT.transition,
      '&:hover': {
        boxShadow: UI_STYLES.getShadow('medium'),
        borderColor: alpha(primary.main, 0.1),
      },
    }
  },
}

// 滚动条变体
export const SCROLLBAR_VARIANTS = {
  default: {
    get styles(): SxProps<Theme> {
      const palette = getCurrentExtendedPalette()
      return {
        scrollbarWidth: 'thin',
        scrollbarColor: `${alpha(palette.primary.main, 0.3)} transparent`,
        transition: LAYOUT.TRANSITION.DEFAULT.transition,
        '&::-webkit-scrollbar': {
          width: '8px',
          height: '8px',
        },
        '&::-webkit-scrollbar-track': {
          background: 'transparent',
        },
        '&::-webkit-scrollbar-thumb': {
          background: alpha(palette.primary.main, 0.3),
          borderRadius: '4px',
          transition: LAYOUT.TRANSITION.DEFAULT.transition,
          '&:hover': {
            background: alpha(palette.primary.main, 0.5),
          },
        },
      }
    },
  },
  thin: {
    get styles(): SxProps<Theme> {
      const palette = getCurrentExtendedPalette()
      return {
        scrollbarWidth: 'thin',
        scrollbarColor: `${alpha(palette.primary.main, 0.2)} transparent`,
        '&::-webkit-scrollbar': {
          width: '4px',
          height: '4px',
        },
        '&::-webkit-scrollbar-track': {
          background: 'transparent',
        },
        '&::-webkit-scrollbar-thumb': {
          background: alpha(palette.primary.main, 0.2),
          borderRadius: '2px',
          '&:hover': {
            background: alpha(palette.primary.main, 0.4),
          },
        },
      }
    },
  },
}

// 添加缺失的CARD_STYLES常量
export const CARD_STYLES = {
  DEFAULT: {
    border: '1px solid',
    borderColor: 'divider',
    borderRadius: BORDER_RADIUS.DEFAULT,
    boxShadow: '0 4px 20px 0 rgba(0,0,0,0.05)',
    transition: 'all 0.3s ease',
  },
  ELEVATED: {
    border: '1px solid',
    borderColor: 'divider',
    borderRadius: BORDER_RADIUS.DEFAULT,
    boxShadow: '0 8px 25px 0 rgba(0,0,0,0.1)',
    transition: 'all 0.3s ease',
  },
  FLAT: {
    border: '1px solid',
    borderColor: 'divider',
    borderRadius: BORDER_RADIUS.DEFAULT,
    boxShadow: 'none',
    transition: 'all 0.3s ease',
  },
  INTERACTIVE: {
    border: '1px solid',
    borderColor: 'divider',
    borderRadius: BORDER_RADIUS.DEFAULT,
    boxShadow: '0 4px 20px 0 rgba(0,0,0,0.05)',
    transition: 'all 0.3s ease',
    cursor: 'pointer',
    '&:hover': {
      transform: 'translateY(-2px)',
      boxShadow: '0 8px 25px 0 rgba(0,0,0,0.1)',
    },
  },
}

// Alert组件样式变体
export const ALERT_VARIANTS = {
  // 默认样式 - 符合主题系统的毛玻璃质感
  default: {
    get styles(): SxProps<Theme> {
      const mode = getCurrentThemeMode()

      return {
        borderRadius: BORDER_RADIUS.DEFAULT,
        backdropFilter: getBackdropFilter('blur(12px) saturate(1.2)'),
        WebkitBackdropFilter: getBackdropFilter('blur(12px) saturate(1.2)'),
        backgroundColor: mode === 'dark' ? 'rgba(47, 47, 47, 0.8)' : 'rgba(255, 255, 255, 0.85)',
        border: '1px solid',
        borderColor: mode === 'dark' ? 'rgba(255, 255, 255, 0.12)' : 'rgba(0, 0, 0, 0.08)',
        boxShadow: getShadow('0 4px 20px rgba(0, 0, 0, 0.1), 0 1px 3px rgba(0, 0, 0, 0.05)'),
        transition: LAYOUT.TRANSITION.DEFAULT.transition,
        position: 'relative',
        overflow: 'hidden',

        // 内容文本样式
        '& .MuiAlert-message': {
          fontSize: '0.875rem',
          fontWeight: 500,
          lineHeight: 1.5,
          textShadow:
            mode === 'dark' ? '0 1px 2px rgba(0, 0, 0, 0.4)' : '0 1px 2px rgba(255, 255, 255, 0.8)',
        },

        // 图标样式
        '& .MuiAlert-icon': {
          opacity: 0.9,
          filter:
            mode === 'dark'
              ? 'drop-shadow(0 1px 2px rgba(0, 0, 0, 0.4))'
              : 'drop-shadow(0 1px 2px rgba(0, 0, 0, 0.1))',
        },

        // 操作按钮样式
        '& .MuiAlert-action': {
          '& .MuiIconButton-root': {
            backdropFilter: getBackdropFilter('blur(8px)'),
            borderRadius: BORDER_RADIUS.SMALL,
            transition: LAYOUT.TRANSITION.FAST.transition,
            '&:hover': {
              backgroundColor: mode === 'dark' ? 'rgba(255, 255, 255, 0.1)' : 'rgba(0, 0, 0, 0.08)',
            },
          },
        },

        // 顶部装饰线
        '&:before': {
          content: '""',
          position: 'absolute',
          top: 0,
          left: 0,
          right: 0,
          height: '1px',
          background:
            mode === 'dark'
              ? 'linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.3), transparent)'
              : 'linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.8), transparent)',
          zIndex: 1,
        },
      }
    },
  },

  // 严重性变体 - 基于不同的Alert类型
  severity: {
    info: {
      get styles(): SxProps<Theme> {
        const mode = getCurrentThemeMode()

        return {
          ...ALERT_VARIANTS.default.styles,
          backgroundColor:
            mode === 'dark' ? `rgba(33, 150, 243, 0.15)` : `rgba(33, 150, 243, 0.05)`,
          borderColor: `rgba(33, 150, 243, ${mode === 'dark' ? 0.3 : 0.2})`,
          boxShadow: getShadow(
            `0 4px 20px rgba(33, 150, 243, 0.15), 0 1px 3px rgba(33, 150, 243, 0.1)`
          ),

          '& .MuiAlert-icon': {
            color: '#2196F3',
          },

          '&:before': {
            background: 'linear-gradient(90deg, transparent, rgba(33, 150, 243, 0.4), transparent)',
          },
        }
      },
    },

    success: {
      get styles(): SxProps<Theme> {
        const mode = getCurrentThemeMode()

        return {
          ...ALERT_VARIANTS.default.styles,
          backgroundColor: mode === 'dark' ? `rgba(76, 175, 80, 0.15)` : `rgba(76, 175, 80, 0.05)`,
          borderColor: `rgba(76, 175, 80, ${mode === 'dark' ? 0.3 : 0.2})`,
          boxShadow: getShadow(
            `0 4px 20px rgba(76, 175, 80, 0.15), 0 1px 3px rgba(76, 175, 80, 0.1)`
          ),

          '& .MuiAlert-icon': {
            color: '#4CAF50',
          },

          '&:before': {
            background: 'linear-gradient(90deg, transparent, rgba(76, 175, 80, 0.4), transparent)',
          },
        }
      },
    },

    warning: {
      get styles(): SxProps<Theme> {
        const mode = getCurrentThemeMode()

        return {
          ...ALERT_VARIANTS.default.styles,
          backgroundColor: mode === 'dark' ? `rgba(255, 152, 0, 0.15)` : `rgba(255, 152, 0, 0.05)`,
          borderColor: `rgba(255, 152, 0, ${mode === 'dark' ? 0.3 : 0.2})`,
          boxShadow: getShadow(
            `0 4px 20px rgba(255, 152, 0, 0.15), 0 1px 3px rgba(255, 152, 0, 0.1)`
          ),

          '& .MuiAlert-icon': {
            color: '#FF9800',
          },

          '&:before': {
            background: 'linear-gradient(90deg, transparent, rgba(255, 152, 0, 0.4), transparent)',
          },
        }
      },
    },

    error: {
      get styles(): SxProps<Theme> {
        const mode = getCurrentThemeMode()

        return {
          ...ALERT_VARIANTS.default.styles,
          backgroundColor: mode === 'dark' ? `rgba(244, 67, 54, 0.15)` : `rgba(244, 67, 54, 0.05)`,
          borderColor: `rgba(244, 67, 54, ${mode === 'dark' ? 0.3 : 0.2})`,
          boxShadow: getShadow(
            `0 4px 20px rgba(244, 67, 54, 0.15), 0 1px 3px rgba(244, 67, 54, 0.1)`
          ),

          '& .MuiAlert-icon': {
            color: '#F44336',
          },

          '&:before': {
            background: 'linear-gradient(90deg, transparent, rgba(244, 67, 54, 0.4), transparent)',
          },
        }
      },
    },
  },

  // 紧凑样式 - 用于空间受限的场景
  compact: {
    get styles(): SxProps<Theme> {
      return {
        ...ALERT_VARIANTS.default.styles,
        padding: '8px 12px',
        minHeight: 'auto',

        '& .MuiAlert-message': {
          fontSize: '0.75rem',
          lineHeight: 1.4,
        },

        '& .MuiAlert-icon': {
          marginRight: '8px',
          fontSize: '1rem',
        },
      }
    },
  },

  // 突出样式 - 用于重要通知
  prominent: {
    get styles(): SxProps<Theme> {
      const mode = getCurrentThemeMode()

      return {
        ...ALERT_VARIANTS.default.styles,
        backgroundColor: mode === 'dark' ? 'rgba(47, 47, 47, 0.95)' : 'rgba(255, 255, 255, 0.95)',
        backdropFilter: getBackdropFilter('blur(20px) saturate(1.4) brightness(1.1)'),
        WebkitBackdropFilter: getBackdropFilter('blur(20px) saturate(1.4) brightness(1.1)'),
        boxShadow: getShadow('0 8px 32px rgba(0, 0, 0, 0.15), 0 2px 8px rgba(0, 0, 0, 0.08)'),
        borderWidth: '1.5px',

        '& .MuiAlert-message': {
          fontSize: '0.9rem',
          fontWeight: 600,
        },

        // 增强的装饰效果
        '&:before': {
          height: '2px',
          background:
            mode === 'dark'
              ? 'linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.5), transparent)'
              : 'linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.9), transparent)',
        },

        // 底部光影效果
        '&:after': {
          content: '""',
          position: 'absolute',
          bottom: 0,
          left: '10%',
          right: '10%',
          height: '1px',
          background: mode === 'dark' ? 'rgba(255, 255, 255, 0.1)' : 'rgba(0, 0, 0, 0.05)',
          borderRadius: '1px',
        },
      }
    },
  },
}
