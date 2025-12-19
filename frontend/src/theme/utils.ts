/**
 * 主题工具函数
 */
import { ExecStopType } from '../services/api/sandbox'
import { getCurrentExtendedPalette } from './themeConfig'

// 获取颜色值函数
function getMetricColor(type: string): string {
  const palette = getCurrentExtendedPalette()
  switch (type) {
    case 'success_calls':
      return palette.success
    case 'failed_calls':
      return palette.error
    default:
      return '#9e9e9e'
  }
}

// 停止类型颜色映射（统一使用具体颜色值）
export const stopTypeColorValues = {
  [ExecStopType.NORMAL]: getMetricColor('success_calls'),
  [ExecStopType.ERROR]: getMetricColor('failed_calls'),
  [ExecStopType.TIMEOUT]: '#ff9800',
  [ExecStopType.AGENT]: '#2196f3',
  [ExecStopType.MANUAL]: '#9e9e9e',
  [ExecStopType.SECURITY]: '#f44336',
  [ExecStopType.MULTIMODAL_AGENT]: '#9c27b0',
} as const

// 停止类型到 i18n 键的映射
export const STOP_TYPE_I18N_KEYS: Record<ExecStopType, string> = {
  [ExecStopType.NORMAL]: 'stopType.normal',
  [ExecStopType.ERROR]: 'stopType.error',
  [ExecStopType.TIMEOUT]: 'stopType.timeout',
  [ExecStopType.AGENT]: 'stopType.agent',
  [ExecStopType.MANUAL]: 'stopType.manual',
  [ExecStopType.SECURITY]: 'stopType.security',
  [ExecStopType.MULTIMODAL_AGENT]: 'stopType.multimodal',
} as const

/**
 * 获取停止类型的 i18n 键
 */
export function getStopTypeI18nKey(stopType: number): string {
  const key = STOP_TYPE_I18N_KEYS[stopType as ExecStopType]
  if (!key) {
    console.warn(`Invalid stop type: ${stopType}, falling back to NORMAL`)
    return STOP_TYPE_I18N_KEYS[ExecStopType.NORMAL]
  }
  return key
}

/**
 * 获取停止类型的翻译文本（需要传入 t 函数）
 */
export function getStopTypeTranslatedText(
  stopType: number,
  t: (key: string, options?: { ns?: string }) => string
): string {
  const key = getStopTypeI18nKey(stopType)
  return t(key, { ns: 'common' })
}

/**
 * 获取停止类型颜色值
 */
export function getStopTypeColorValue(stopType: number): string {
  return stopTypeColorValues[stopType as ExecStopType] || '#9e9e9e'
}

/**
 * 获取消息类型颜色
 */
export function getMessageTypeColor(messageType: string): string {
  const palette = getCurrentExtendedPalette()

  switch (messageType.toLowerCase()) {
    case '群聊消息':
      return palette.primary.main
    case '私聊消息':
      return palette.secondary.main
    default:
      return '#9E9E9E'
  }
}

// 旧版兼容（已废弃）
// @deprecated 使用 getStopTypeColorValue 替代
export function getStopTypeColor(stopType: number): string {
  return getStopTypeColorValue(stopType)
}
