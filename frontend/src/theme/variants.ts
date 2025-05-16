/**
 * 主题样式变体配置文件
 * 用于定义各种UI组件的通用样式变体
 */
import { SxProps, Theme, alpha } from '@mui/material'
import { UI_STYLES } from './themeConfig'
import { getCurrentExtendedPalette, getCurrentThemeMode } from './themeConfig'
import { stopTypeColorValues } from './utils'
import { getShadow, getBackdropFilter, getBackground, getTransition } from './themeApi'

// 圆角常量
export const BORDER_RADIUS = {
  LARGE: '12px',
  DEFAULT: '8px',
  SMALL: '4px',
  PILL: '9999px',
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
      }
    },
    SLOW: {
      get transition() {
        return getTransition('all 0.5s ease')
      }
    },
    FAST: {
      get transition() {
        return getTransition('all 0.15s ease')
      }
    }
  },
}

// 卡片组件样式变体
export const CARD_VARIANTS = {
  default: {
    get styles(): SxProps<Theme> {
      const mode = getCurrentThemeMode()
      return {
        transition: LAYOUT.TRANSITION.DEFAULT.transition,
        background: getBackground(
          mode === 'dark'
            ? 'rgba(25, 25, 30, 0.85)'
            : 'rgba(255, 255, 255, 0.9)'
        ),
        backdropFilter: getBackdropFilter('blur(12px)'),
        WebkitBackdropFilter: getBackdropFilter('blur(12px)'),
        boxShadow: getShadow('0 4px 6px rgba(0, 0, 0, 0.1)'),
        border: '1px solid',
        borderColor: mode === 'dark' 
          ? 'rgba(255, 255, 255, 0.1)' 
          : 'rgba(0, 0, 0, 0.06)',
        borderRadius: BORDER_RADIUS.DEFAULT,
        '&:hover': {
          boxShadow: getShadow('0 6px 12px rgba(0, 0, 0, 0.15)'),
        }
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

// 按钮组件样式变体
export const BUTTON_VARIANTS = {
  primary: {
    get styles(): SxProps<Theme> {
      const palette = getCurrentExtendedPalette()
      return {
        background: getBackground(`linear-gradient(45deg, ${palette.primary.main} 0%, ${palette.primary.dark} 100%)`),
        color: '#fff',
        '&:hover': {
          background: getBackground(`linear-gradient(45deg, ${palette.primary.dark} 0%, ${palette.primary.main} 100%)`),
          boxShadow: getShadow('0 4px 8px rgba(0, 0, 0, 0.15)'),
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
      backgroundColor:
        mode === 'light' ? 'rgba(255, 255, 255, 0.78)' : alpha(palette.background.paper, 0.75),
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
      backgroundColor:
        mode === 'light' ? 'rgba(245, 245, 245, 0.85)' : alpha(palette.primary.darker, 0.5),
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
      '&:hover': {
        backgroundColor: alpha(palette.primary.main, 0.08),
      },
      '&:nth-of-type(odd)': {
        backgroundColor:
          getCurrentThemeMode() === 'light' ? 'rgba(0, 0, 0, 0.02)' : 'rgba(255, 255, 255, 0.03)',
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
      backgroundColor:
        mode === 'light' ? 'rgba(255, 255, 255, 0.95)' : alpha(palette.background.paper, 0.95),
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
      backgroundColor:
        mode === 'light' ? 'rgba(255, 255, 255, 0.95)' : alpha(palette.background.paper, 0.95),
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
    }
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
    }
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
  }
}
