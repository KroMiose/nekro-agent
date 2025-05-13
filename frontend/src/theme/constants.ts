import { ExecStopType } from '../services/api/sandbox'

// 颜色常量 - 根据主题规范更新
export const COLORS = {
  // 主色调
  PRIMARY: {
    LIGHT: '#EA5252', // 亮色模式主色
    DARK: '#EA5252', // 暗色模式主色
    LIGHTER: '#FF7676', // 亮色变体
    DARKER: '#C73F3F', // 暗色变体
    HIGHLIGHT: '#FF8A8A', // 高亮色
  },

  // 辅助色
  SECONDARY: {
    LIGHT: '#9C6ADE', // 亮色模式辅助色 - 淡紫色
    DARK: '#A87BEF', // 暗色模式辅助色 - 淡紫色
    LIGHTER: '#B48CF0', // 亮色变体 - 较浅的紫色
    DARKER: '#7A53AE', // 暗色变体 - 深紫色
    HIGHLIGHT: '#C3A1FF', // 高亮色 - 亮淡紫色
  },

  // 状态色
  SUCCESS: '#4caf50', // 成功 - 绿色
  ERROR: '#f44336', // 错误 - 红色
  WARNING: '#ff9800', // 警告 - 橙色
  INFO: '#2196f3', // 信息 - 蓝色
  DEFAULT: '#9e9e9e', // 默认 - 灰色
  CYAN: '#00bcd4', // 青色
} as const

// 背景渐变常量
export const GRADIENTS = {
  BACKGROUND: {
    LIGHT: {
      PRIMARY: 'linear-gradient(135deg, #f8f5f5 0%, #fff0f0 50%, #f8f5f5 100%)',
      CONTENT:
        'linear-gradient(180deg, rgba(255, 255, 255, 0.9) 0%, rgba(255, 245, 245, 0.9) 100%)',
    },
    DARK: {
      PRIMARY: 'linear-gradient(135deg, #1a1818 0%, #271e1e 50%, #1a1818 100%)',
      CONTENT: 'linear-gradient(180deg, rgba(40, 35, 35, 0.6) 0%, rgba(30, 25, 25, 0.6) 100%)',
    },
  },
  APP_BAR: {
    LIGHT: 'linear-gradient(to right, #EA5252, #FF7676, #EA5252)',
    DARK: 'linear-gradient(to right, #431c1c, #662424, #431c1c)',
  },
  DRAWER: {
    LIGHT: 'linear-gradient(to bottom, #ffffff, #fff7f7)',
    DARK: 'linear-gradient(to bottom, #211c1c, #2a2222)',
  },
  CARD: {
    LIGHT: 'linear-gradient(145deg, #ffffff, #fafafa)',
    DARK: 'linear-gradient(145deg, #232020, #1e1a1a)',
  },
} as const

// 阴影常量
export const SHADOWS = {
  CARD: {
    LIGHT: {
      DEFAULT: '0 2px 8px rgba(0, 0, 0, 0.08)',
      HOVER: '0 4px 12px rgba(0, 0, 0, 0.12)',
    },
    DARK: {
      DEFAULT: '0 4px 12px rgba(0, 0, 0, 0.3)',
      HOVER: '0 6px 16px rgba(0, 0, 0, 0.4)',
    },
  },
  APP_BAR: {
    LIGHT: '0 2px 10px rgba(234, 82, 82, 0.2)',
    DARK: '0 2px 10px rgba(67, 28, 28, 0.6)',
  },
  BUTTON: {
    LIGHT: {
      DEFAULT: '0 2px 6px rgba(0, 0, 0, 0.1)',
      HOVER: '0 4px 12px rgba(0, 0, 0, 0.15)',
    },
    DARK: {
      DEFAULT: '0 2px 6px rgba(0, 0, 0, 0.4)',
      HOVER: '0 4px 12px rgba(0, 0, 0, 0.5)',
    },
  },
  DRAWER: {
    LIGHT: '2px 0 10px rgba(0, 0, 0, 0.05)',
    DARK: '2px 0 10px rgba(0, 0, 0, 0.4)',
  },
} as const

// 边框样式常量
export const BORDERS = {
  CARD: {
    LIGHT: '1px solid rgba(234, 82, 82, 0.05)',
    DARK: '1px solid rgba(102, 36, 36, 0.08)',
  },
  DIVIDER: {
    LIGHT: '1px solid rgba(0, 0, 0, 0.08)',
    DARK: '1px solid rgba(255, 255, 255, 0.08)',
  },
} as const

// 圆角常量
export const BORDER_RADIUS = {
  SMALL: '3px',  // 小圆角 - 用于滚动条等小元素
  DEFAULT: '6px', // 默认圆角 - 用于卡片、按钮等
  MEDIUM: '8px',  // 中等圆角 - 用于对话框等
  LARGE: '12px',  // 大圆角 - 用于特殊元素
  FULL: '9999px', // 全圆 - 用于头像、徽章等
} as const

// 滚动条样式常量
export const SCROLLBARS = {
  DEFAULT: {
    LIGHT: {
      TRACK: '#f5f5f5',
      THUMB: 'rgba(0, 0, 0, 0.2)',
      THUMB_HOVER: 'rgba(0, 0, 0, 0.3)',
      WIDTH: '6px',
      HEIGHT: '6px',
    },
    DARK: {
      TRACK: 'rgba(255, 255, 255, 0.05)',
      THUMB: 'rgba(255, 255, 255, 0.15)',
      THUMB_HOVER: 'rgba(255, 255, 255, 0.25)',
      WIDTH: '6px',
      HEIGHT: '6px',
    },
  },
  THIN: {
    LIGHT: {
      TRACK: '#f5f5f5',
      THUMB: 'rgba(0, 0, 0, 0.2)',
      THUMB_HOVER: 'rgba(0, 0, 0, 0.3)',
      WIDTH: '4px',
      HEIGHT: '4px',
    },
    DARK: {
      TRACK: 'rgba(255, 255, 255, 0.05)',
      THUMB: 'rgba(255, 255, 255, 0.15)',
      THUMB_HOVER: 'rgba(255, 255, 255, 0.25)',
      WIDTH: '4px',
      HEIGHT: '4px',
    },
  },
} as const

// 卡片布局常量
export const CARD_LAYOUT = {
  CHART_HEIGHT: {
    MOBILE: 180,
    DESKTOP: 200,
  },
  LOADING_HEIGHT: '200px',
  TRANSITION: 'all 0.3s ease',
  BACKDROP_FILTER: 'blur(10px)',
} as const

// 图表默认颜色数组 - 使用主色调和辅助色调
export const CHART_COLORS = [
  COLORS.PRIMARY.LIGHT,
  COLORS.SECONDARY.LIGHT,
  COLORS.SUCCESS,
  COLORS.WARNING,
  COLORS.ERROR,
  COLORS.CYAN,
] as const

// 兼容旧版本的颜色引用
export const LEGACY_COLORS = {
  PRIMARY: COLORS.PRIMARY.LIGHT,
  SECONDARY: COLORS.SECONDARY.LIGHT,
  SUCCESS: COLORS.SUCCESS,
  ERROR: COLORS.ERROR,
  WARNING: COLORS.WARNING,
  INFO: COLORS.INFO,
  DEFAULT: COLORS.DEFAULT,
  CYAN: COLORS.CYAN,
} as const

// 沙盒停止类型颜色映射 (MUI颜色名称)
export const stopTypeColors = {
  [ExecStopType.NORMAL]: 'success',
  [ExecStopType.ERROR]: 'error',
  [ExecStopType.TIMEOUT]: 'warning',
  [ExecStopType.AGENT]: 'info',
  [ExecStopType.MANUAL]: 'default',
  [ExecStopType.MULTIMODAL_AGENT]: 'secondary',
} as const

// 沙盒停止类型颜色映射 (具体颜色值)
export const stopTypeColorValues = {
  [ExecStopType.NORMAL]: COLORS.SUCCESS,
  [ExecStopType.ERROR]: COLORS.ERROR,
  [ExecStopType.TIMEOUT]: COLORS.WARNING,
  [ExecStopType.AGENT]: COLORS.INFO,
  [ExecStopType.MANUAL]: COLORS.DEFAULT,
  [ExecStopType.MULTIMODAL_AGENT]: COLORS.SECONDARY.LIGHT,
} as const

// 沙盒停止类型文本映射
export const stopTypeTexts = {
  [ExecStopType.NORMAL]: '正常',
  [ExecStopType.ERROR]: '错误',
  [ExecStopType.TIMEOUT]: '超时',
  [ExecStopType.AGENT]: '代理',
  [ExecStopType.MANUAL]: '手动',
  [ExecStopType.MULTIMODAL_AGENT]: '多模态',
} as const

// 消息类型颜色映射
export const messageTypeColors = {
  群聊消息: COLORS.PRIMARY.LIGHT,
  私聊消息: COLORS.INFO,
} as const

// 指标颜色映射
export const metricColors = {
  messages: COLORS.SECONDARY.LIGHT,
  sandbox_calls: COLORS.WARNING,
  success_calls: COLORS.SUCCESS,
  failed_calls: COLORS.ERROR,
  success_rate: COLORS.SECONDARY.LIGHT,
} as const

// 指标名称映射
export const metricNames = {
  messages: '消息数',
  sandbox_calls: '沙盒调用',
  success_calls: '成功调用',
  failed_calls: '失败调用',
  success_rate: '成功率',
} as const

// 插件类型颜色映射 (MUI颜色名称)
export const pluginTypeColors: Record<
  string,
  'primary' | 'secondary' | 'success' | 'warning' | 'info' | 'default'
> = {
  builtin: 'primary',
  package: 'info',
  local: 'warning',
} as const

// 插件类型文本映射
export const pluginTypeTexts: Record<string, string> = {
  builtin: '内置',
  package: '云端',
  local: '本地',
} as const

// 配置类型颜色映射
export const configTypeColors: Record<
  string,
  'primary' | 'success' | 'warning' | 'info' | 'default'
> = {
  str: 'warning',
  int: 'info',
  float: 'info',
  bool: 'success',
  list: 'primary',
} as const

// 方法类型颜色映射
export const methodTypeColors: Record<string, 'primary' | 'success' | 'warning' | 'info'> = {
  tool: 'primary',
  behavior: 'success',
  agent: 'warning',
  multimodal_agent: 'info',
} as const

// 获取停止类型的颜色 (MUI颜色名称)
export const getStopTypeColor = (
  stopType: number
): 'success' | 'error' | 'warning' | 'info' | 'default' | 'secondary' => {
  return stopTypeColors[stopType as ExecStopType] || 'default'
}

// 获取停止类型的颜色值
export const getStopTypeColorValue = (stopType: number): string => {
  return stopTypeColorValues[stopType as ExecStopType] || LEGACY_COLORS.DEFAULT
}

// 获取停止类型的文本
export const getStopTypeText = (stopType: number): string => {
  return stopTypeTexts[stopType as ExecStopType] || '未知'
}

// 获取插件类型的文本
export const getPluginTypeText = (type: string): string => {
  return pluginTypeTexts[type] || '未知'
}

// 获取消息类型的颜色
export const getMessageTypeColor = (messageType: string): string => {
  return messageTypeColors[messageType as keyof typeof messageTypeColors] || LEGACY_COLORS.DEFAULT
}
