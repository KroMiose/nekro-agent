import { ExecStopType } from '../services/api/sandbox'

// 颜色常量
export const COLORS = {
  PRIMARY: '#2196f3', // 主色调 - 蓝色
  SECONDARY: '#9c27b0', // 次要色调 - 紫色
  SUCCESS: '#4caf50', // 成功 - 绿色
  ERROR: '#f44336', // 错误 - 红色
  WARNING: '#ff9800', // 警告 - 橙色
  INFO: '#2196f3', // 信息 - 蓝色
  DEFAULT: '#9e9e9e', // 默认 - 灰色
  CYAN: '#00bcd4', // 青色
} as const

// 图表默认颜色数组
export const CHART_COLORS = [
  COLORS.PRIMARY,
  COLORS.WARNING,
  COLORS.SUCCESS,
  COLORS.ERROR,
  COLORS.SECONDARY,
  COLORS.CYAN,
] as const

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
  [ExecStopType.MULTIMODAL_AGENT]: COLORS.SECONDARY,
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

// 指标颜色映射
export const metricColors = {
  messages: COLORS.PRIMARY,
  sandbox_calls: COLORS.WARNING,
  success_calls: COLORS.SUCCESS,
  failed_calls: COLORS.ERROR,
  success_rate: COLORS.SECONDARY,
} as const

// 指标名称映射
export const metricNames = {
  messages: '消息数',
  sandbox_calls: '沙盒调用',
  success_calls: '成功调用',
  failed_calls: '失败调用',
  success_rate: '成功率',
} as const

// 获取停止类型的颜色 (MUI颜色名称)
export const getStopTypeColor = (
  stopType: number
): 'success' | 'error' | 'warning' | 'info' | 'default' | 'secondary' => {
  return stopTypeColors[stopType as ExecStopType] || 'default'
}

// 获取停止类型的颜色值
export const getStopTypeColorValue = (stopType: number): string => {
  return stopTypeColorValues[stopType as ExecStopType] || COLORS.DEFAULT
}

// 获取停止类型的文本
export const getStopTypeText = (stopType: number): string => {
  return stopTypeTexts[stopType as ExecStopType] || '未知'
}
