/**
 * 主题样式变体配置文件
 * 用于定义各种UI组件的通用样式变体
 */
import { SxProps, Theme } from '@mui/material/styles'
import { alpha } from '@mui/material'
import { UI_STYLES } from './themeConfig'
import { getCurrentExtendedPalette, getCurrentThemeMode } from './themeConfig'
import { stopTypeColorValues } from './utils'

// 圆角常量
export const BORDER_RADIUS = {
  SMALL: '3px', // 小圆角 - 用于滚动条等小元素
  DEFAULT: '6px', // 默认圆角 - 用于卡片、按钮等
  MEDIUM: '8px', // 中等圆角 - 用于对话框等
  LARGE: '12px', // 大圆角 - 用于特殊元素
  FULL: '9999px', // 全圆 - 用于头像、徽章等
}

// 通用布局常量
export const LAYOUT = {
  SPACING: {
    XS: '4px',
    SM: '8px',
    MD: '16px',
    LG: '24px',
    XL: '32px',
  },
  TRANSITION: {
    FAST: 'all 0.2s ease',
    DEFAULT: 'all 0.3s ease',
    SLOW: 'all 0.5s ease',
  },
}

// 卡片样式变体
export const CARD_STYLES = {
  default: {
    get styles(): SxProps<Theme> {
      const extendedPalette = getCurrentExtendedPalette()
      const primary = extendedPalette.primary

      return {
        backgroundColor: extendedPalette.background.paper,
        backgroundImage: UI_STYLES.getGradient('card'),
        boxShadow: UI_STYLES.getShadow('light'),
        border: `1px solid ${alpha(primary.main, 0.12)}`,
        borderRadius: BORDER_RADIUS.DEFAULT,
        '&:hover': {
          boxShadow: UI_STYLES.getShadow('medium'),
          borderColor: alpha(primary.main, 0.2),
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
}

// 按钮样式变体
export const BUTTON_VARIANTS = {
  // 主按钮
  primary: {
    get styles(): SxProps<Theme> {
      return {
        background: UI_STYLES.getGradient('primary'),
        color: '#fff',
        boxShadow: UI_STYLES.getShadow('light'),
        borderRadius: BORDER_RADIUS.DEFAULT,
        transition: LAYOUT.TRANSITION.FAST,
        textTransform: 'none',
        '&:hover': {
          boxShadow: UI_STYLES.getShadow('medium'),
          transform: 'translateY(-1px)',
        },
      }
    },
  },
  // 次级按钮
  secondary: {
    get styles(): SxProps<Theme> {
      return {
        background: UI_STYLES.getGradient('secondary'),
        color: '#fff',
        boxShadow: UI_STYLES.getShadow('light'),
        borderRadius: BORDER_RADIUS.DEFAULT,
        transition: LAYOUT.TRANSITION.FAST,
        textTransform: 'none',
        '&:hover': {
          boxShadow: UI_STYLES.getShadow('medium'),
          transform: 'translateY(-1px)',
        },
      }
    },
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
          transition: LAYOUT.TRANSITION.FAST,
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
    borderRadius: BORDER_RADIUS.FULL,
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
    }
  },

  // 停止类型Chip样式
  getStopTypeChip: (stopType: number, isSmall: boolean = false): SxProps<Theme> => {
    const color = stopTypeColorValues[stopType as keyof typeof stopTypeColorValues] || '#9e9e9e'

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
    };
    
    const color = roleColors[permLevel as keyof typeof roleColors] || '#9e9e9e';
    
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
      'normal': '#4caf50', // 正常
      'passive': '#ff9800', // 未激活
      'banned': '#f44336', // 封禁
    };
    
    const color = statusColors[status.toLowerCase() as keyof typeof statusColors] || '#9e9e9e';
    
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
  package: '插件包',
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
  agent: '用于提供 LLM 交互反馈，其返回值必须为 str 类型，描述 LLM 行为的结果，返回后会被添加到上下文中再次调用',
  behavior: '用于提供 LLM 交互反馈，其返回值必须为 str 类型，描述 LLM 行为的结果，返回后会被添加到上下文中但不触发再次调用',
  multimodal_agent: '用于提供 LLM 交互反馈，其返回值为一段多模态 message，描述 LLM 行为的结果，返回后会被添加到上下文中再次调用',
}

// 统一表格样式变体
export const UNIFIED_TABLE_STYLES = {
  get container(): SxProps<Theme> {
    const palette = getCurrentExtendedPalette()
    const mode = getCurrentThemeMode()
    return {
      backdropFilter: 'blur(8px)',
      WebkitBackdropFilter: 'blur(8px)',
      backgroundColor: mode === 'light' 
        ? 'rgba(255, 255, 255, 0.78)' 
        : alpha(palette.background.paper, 0.75),
      borderRadius: BORDER_RADIUS.DEFAULT,
      border: `1px solid ${alpha(palette.primary.main, mode === 'light' ? 0.06 : 0.1)}`,
      boxShadow: UI_STYLES.getShadow('light'),
      overflow: 'hidden',
      transition: 'all 0.3s ease',
      position: 'relative',
      height: '100%',
      '&::before': {
        content: '""',
        position: 'absolute',
        top: 0,
        left: 0,
        width: '100%',
        height: '2px',
        background: `linear-gradient(90deg, ${alpha(palette.primary.main, 0.18)}, ${alpha(palette.secondary.main, 0.18)})`,
        opacity: 0.8,
      },
      '&:hover': {
        boxShadow: UI_STYLES.getShadow('medium'),
      }
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
        ? 'rgba(245, 245, 245, 0.85)' 
        : alpha(palette.primary.darker, 0.5),
      backdropFilter: 'blur(8px)',
      WebkitBackdropFilter: 'blur(8px)',
      boxShadow: mode === 'dark' 
        ? '0 4px 6px -1px rgba(0, 0, 0, 0.15)' 
        : '0 4px 6px -1px rgba(0, 0, 0, 0.08)',
      textTransform: 'uppercase',
      fontSize: '0.75rem',
      letterSpacing: '0.02em',
      backgroundImage: mode === 'light'
        ? `linear-gradient(180deg, rgba(255, 255, 255, 0.92), rgba(245, 245, 245, 0.85))`
        : `linear-gradient(180deg, ${alpha(palette.primary.darker, 0.55)}, ${alpha(palette.primary.darker, 0.45)})`,
    }
  },
  
  get row(): SxProps<Theme> {
    const palette = getCurrentExtendedPalette()
    return {
      transition: 'background-color 0.2s ease',
      '&:hover': {
        backgroundColor: alpha(palette.primary.main, 0.08),
      },
      '&:nth-of-type(odd)': {
        backgroundColor: getCurrentThemeMode() === 'light' 
          ? 'rgba(0, 0, 0, 0.02)' 
          : 'rgba(255, 255, 255, 0.03)',
      },
    }
  },
  
  get cell(): SxProps<Theme> {
    const mode = getCurrentThemeMode()
    return {
      fontSize: '0.875rem',
      backdropFilter: 'blur(4px)',
      WebkitBackdropFilter: 'blur(4px)',
      borderBottom: `1px solid ${mode === 'dark' ? 'rgba(255, 255, 255, 0.07)' : 'rgba(0, 0, 0, 0.06)'}`,
    }
  },
  
  get scrollbar(): SxProps<Theme> {
    const mode = getCurrentThemeMode()
    return {
      '&::-webkit-scrollbar': {
        width: '8px',
        height: '8px',
      },
      '&::-webkit-scrollbar-thumb': {
        backgroundColor: mode === 'dark' 
          ? 'rgba(255, 255, 255, 0.16)' 
          : 'rgba(0, 0, 0, 0.2)',
        borderRadius: '4px',
      },
      '&::-webkit-scrollbar-track': {
        backgroundColor: mode === 'dark' 
          ? 'rgba(255, 255, 255, 0.04)' 
          : 'rgba(0, 0, 0, 0.04)',
        borderRadius: '4px',
      },
    }
  },
  
  get paper(): SxProps<Theme> {
    const palette = getCurrentExtendedPalette()
    const mode = getCurrentThemeMode()
    return {
      backgroundColor: mode === 'light' 
        ? 'rgba(255, 255, 255, 0.85)' 
        : alpha(palette.background.paper, 0.8),
      backgroundImage: mode === 'light'
        ? 'linear-gradient(135deg, rgba(255, 255, 255, 0.9), rgba(255, 255, 255, 0.8))'
        : `linear-gradient(135deg, ${alpha(palette.background.paper, 0.85)}, ${alpha(palette.background.paper, 0.75)})`,
      backdropFilter: 'blur(10px)',
      WebkitBackdropFilter: 'blur(10px)',
      boxShadow: UI_STYLES.getShadow('light'),
      borderRadius: BORDER_RADIUS.DEFAULT,
      border: `1px solid ${alpha(palette.primary.main, mode === 'light' ? 0.06 : 0.1)}`,
      overflow: 'hidden',
      transition: 'all 0.3s ease',
      '&:hover': {
        boxShadow: UI_STYLES.getShadow('medium'),
      }
    }
  }
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
    }
  },
  TABLE: {
    get styles(): SxProps<Theme> {
      return UNIFIED_TABLE_STYLES.container;
    }
  }
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
      transition: LAYOUT.TRANSITION.DEFAULT,
      '&:hover': {
        boxShadow: UI_STYLES.getShadow('medium'),
        borderColor: alpha(primary.main, 0.1),
      },
    }
  },
}
