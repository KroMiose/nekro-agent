/**
 * 兼容层 - 提供向后兼容的函数
 */
import { ExecStopType } from '../services/api/sandbox'
import { getCurrentExtendedPalette } from './themeConfig'

// 沙盒停止类型颜色映射 (MUI颜色名称)
export const stopTypeColors = {
  [ExecStopType.NORMAL]: 'success',
  [ExecStopType.ERROR]: 'error',
  [ExecStopType.TIMEOUT]: 'warning',
  [ExecStopType.AGENT]: 'info',
  [ExecStopType.MANUAL]: 'default',
  [ExecStopType.MULTIMODAL_AGENT]: 'secondary',
} as const

// 获取颜色值函数
function getMetricColor(type: string): string {
  const palette = getCurrentExtendedPalette()
  switch(type) {
    case 'success_calls':
      return palette.success
    case 'failed_calls':
      return palette.error
    default:
      return '#9e9e9e'
  }
}

// 沙盒停止类型颜色映射 (具体颜色值)
export const stopTypeColorValues = {
  [ExecStopType.NORMAL]: getMetricColor('success_calls'),
  [ExecStopType.ERROR]: getMetricColor('failed_calls'),
  [ExecStopType.TIMEOUT]: '#ff9800',
  [ExecStopType.AGENT]: '#2196f3',
  [ExecStopType.MANUAL]: '#9e9e9e',
  [ExecStopType.MULTIMODAL_AGENT]: '#9c27b0',
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

// 获取停止类型文本
export function getStopTypeText(stopType: number): string {
  return stopTypeTexts[stopType as ExecStopType] || '未知'
}

// 获取停止类型颜色
export function getStopTypeColor(stopType: number): 'success' | 'error' | 'warning' | 'info' | 'default' | 'primary' | 'secondary' {
  return (stopTypeColors[stopType as ExecStopType] || 'default') as 'success' | 'error' | 'warning' | 'info' | 'default' | 'primary' | 'secondary'
}

// 获取停止类型颜色值
export function getStopTypeColorValue(stopType: number): string {
  return stopTypeColorValues[stopType as ExecStopType] || '#9e9e9e'
}

// 获取消息类型颜色
export function getMessageTypeColor(messageType: string): string {
  switch (messageType.toLowerCase()) {
    case 'user':
      return '#4CAF50'
    case 'assistant':
      return '#2196F3'
    case 'system':
      return '#FFC107'
    case 'function':
      return '#9C27B0'
    case 'tool':
      return '#FF5722'
    default:
      return '#9E9E9E'
  }
}

// 旧版 LEGACY_COLORS 兼容
export const LEGACY_COLORS = {
  PRIMARY: '#1976d2',
  SECONDARY: '#9c27b0',
  SUCCESS: '#4caf50',
  ERROR: '#f44336',
  WARNING: '#ff9800',
  INFO: '#2196f3',
  DEFAULT: '#9e9e9e',
} 