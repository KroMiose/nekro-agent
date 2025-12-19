/**
 * 主题系统API入口文件
 * 导出所有非组件的主题相关内容
 */

// 从各个文件导入需要的内容
import {
  themes,
  ThemeMode,
  BaseThemeMode,
  ThemeKeys,
  MinimalPaletteConfig,
  ThemeConfig,
  ThemePreset,
  getMuiPaletteOptions,
  getAlphaColor,
  getLighterColor,
  getDarkerColor,
  getHighlightColor,
  themePresets,
  updateTheme,
  customizeTheme,
  currentThemePresetId,
  getExtendedPalette,
} from './palette'

import {
  getCurrentThemeMode,
  getCurrentTheme,
  getCurrentExtendedPalette,
  getCurrentBackground,
  getTheme,
  UI_STYLES,
  LOG_TABLE_STYLES,
  LOGIN_PAGE_STYLES,
} from './themeConfig'

import {
  BORDER_RADIUS,
  LAYOUT,
  CARD_STYLES,
  BUTTON_VARIANTS,
  INPUT_VARIANTS,
  BADGE_VARIANTS,
  CHIP_VARIANTS,
  UNIFIED_TABLE_STYLES,
  ALERT_VARIANTS,
  methodTypeColors,
  methodTypeTexts,
  methodTypeDescriptions,
} from './variants'

// 从 utils.ts
import {
  getStopTypeColor,
  getStopTypeColorValue,
  getStopTypeTranslatedText,
  getStopTypeI18nKey,
  getMessageTypeColor,
  stopTypeColorValues,
  STOP_TYPE_I18N_KEYS,
} from './utils'

// 从新的高级渐变系统导入
import AdvancedGradients, { AdvancedBackgrounds, registerHoudiniPaints } from './gradients'

// 从性能模式导入
import { PerformanceMode, useColorMode } from '../stores/theme'

// 导出类型
export type {
  ThemeMode,
  BaseThemeMode,
  ThemeKeys,
  MinimalPaletteConfig,
  ThemeConfig,
  ThemePreset,
  PerformanceMode,
}

// 导出函数和常量
export {
  // 从 palette.ts
  themes,
  themePresets,
  updateTheme,
  customizeTheme,
  currentThemePresetId,
  getMuiPaletteOptions,
  getAlphaColor,
  getLighterColor,
  getDarkerColor,
  getHighlightColor,
  getExtendedPalette,

  // 从 themeConfig.ts
  getCurrentThemeMode,
  getCurrentTheme,
  getCurrentExtendedPalette,
  getCurrentBackground,
  getTheme,
  UI_STYLES,
  LOG_TABLE_STYLES,
  LOGIN_PAGE_STYLES,

  // 从 variants.ts
  BORDER_RADIUS,
  LAYOUT,
  CARD_STYLES,
  BUTTON_VARIANTS,
  INPUT_VARIANTS,
  BADGE_VARIANTS,
  CHIP_VARIANTS,
  UNIFIED_TABLE_STYLES,
  ALERT_VARIANTS,
  methodTypeColors,
  methodTypeTexts,
  methodTypeDescriptions,

  // 从 utils.ts
  getStopTypeColor,
  getStopTypeColorValue,
  getStopTypeTranslatedText,
  getStopTypeI18nKey,
  getMessageTypeColor,
  stopTypeColorValues,
  STOP_TYPE_I18N_KEYS,

  // 从 gradients.ts
  AdvancedGradients,
  AdvancedBackgrounds,
  registerHoudiniPaints,
}

// 性能模式配置类型
export interface PerformanceConfig {
  blurEffects: boolean
  gradients: boolean
  animations: boolean
  transitions: boolean
  shadows: 'minimal' | 'moderate' | 'full'
  backgroundEffects: boolean
}

// 在文件中适当位置添加性能模式配置对象
export const PERFORMANCE_CONFIGS: Record<PerformanceMode, PerformanceConfig> = {
  // 性能模式 - 最小化视觉效果
  performance: {
    blurEffects: false, // 禁用模糊效果
    gradients: false, // 禁用渐变
    animations: false, // 禁用动画
    transitions: false, // 禁用过渡效果
    shadows: 'minimal', // 最小阴影
    backgroundEffects: false, // 禁用背景特效
  },
  // 均衡模式 - 适中的视觉效果
  balanced: {
    blurEffects: true, // 有限的模糊效果
    gradients: true, // 简化的渐变
    animations: true, // 简化的动画
    transitions: true, // 简化的过渡效果
    shadows: 'moderate', // 适中阴影
    backgroundEffects: true, // 简化的背景特效
  },
  // 质量模式 - 完整视觉效果
  quality: {
    blurEffects: true, // 完整的模糊效果
    gradients: true, // 完整的渐变
    animations: true, // 完整的动画
    transitions: true, // 完整的过渡效果
    shadows: 'full', // 完整阴影
    backgroundEffects: true, // 完整的背景特效
  },
}

// 添加获取当前性能配置的辅助函数
export function getCurrentPerformanceConfig(): PerformanceConfig {
  const { performanceMode } = useColorMode.getState()
  return PERFORMANCE_CONFIGS[performanceMode]
}

// 添加用于检查特定性能特性是否启用的辅助函数
export function isFeatureEnabled(feature: keyof PerformanceConfig): boolean {
  const config = getCurrentPerformanceConfig()
  return !!config[feature]
}

// 获取阴影级别
export function getShadowLevel(): 'minimal' | 'moderate' | 'full' {
  const config = getCurrentPerformanceConfig()
  return config.shadows as 'minimal' | 'moderate' | 'full'
}

// 根据性能模式获取动画时长
export function getAnimationDuration(defaultDuration: number): number {
  const { performanceMode } = useColorMode.getState()

  switch (performanceMode) {
    case 'performance':
      return 0
    case 'balanced':
      return defaultDuration * 0.7
    case 'quality':
    default:
      return defaultDuration
  }
}

// 根据性能模式获取模糊效果数值
export function getBlurValue(defaultValue: number): number {
  const { performanceMode } = useColorMode.getState()
  const config = PERFORMANCE_CONFIGS[performanceMode]

  if (!config.blurEffects) return 0

  switch (performanceMode) {
    case 'performance':
      return 0
    case 'balanced':
      return Math.max(2, Math.floor(defaultValue * 0.5))
    case 'quality':
    default:
      return defaultValue
  }
}

// 根据性能模式获取背景过滤器
export function getBackdropFilter(defaultFilter: string): string {
  const config = getCurrentPerformanceConfig()

  if (!config.blurEffects) return 'none'

  const { performanceMode } = useColorMode.getState()

  switch (performanceMode) {
    case 'performance':
      return 'none'
    case 'balanced': {
      // 简化过滤器，只保留模糊效果，强度减半
      if (defaultFilter.includes('blur')) {
        const blurMatch = defaultFilter.match(/blur\(([0-9]+)px\)/)
        if (blurMatch && blurMatch[1]) {
          const blurValue = Math.max(2, Math.floor(parseInt(blurMatch[1]) * 0.5))
          return `blur(${blurValue}px)`
        }
      }
      return 'none'
    }
    case 'quality':
    default:
      return defaultFilter
  }
}

// 根据性能模式获取过渡效果
export function getTransition(defaultTransition: string): string {
  const config = getCurrentPerformanceConfig()

  if (!config.transitions) return 'none'

  const { performanceMode } = useColorMode.getState()

  switch (performanceMode) {
    case 'performance':
      return 'none'
    case 'balanced': {
      // 简化过渡，缩短时间
      return defaultTransition.replace(/(\d+(?:\.\d+)?)s/g, (_match, duration) => {
        return `${Math.max(0.1, parseFloat(duration) * 0.7)}s`
      })
    }
    case 'quality':
    default:
      return defaultTransition
  }
}

// 获取阴影效果
export function getShadow(defaultShadow: string): string {
  const { performanceMode } = useColorMode.getState()

  switch (performanceMode) {
    case 'performance':
      return 'none'
    case 'balanced': {
      // 简化阴影，减少模糊和大小
      return defaultShadow.replace(/(\d+)px (\d+)px (\d+)px/g, (_, blur, spread, size) => {
        const newBlur = Math.max(1, Math.floor(parseInt(blur) * 0.5))
        const newSpread = Math.max(1, Math.floor(parseInt(spread) * 0.5))
        const newSize = Math.max(1, Math.floor(parseInt(size) * 0.5))
        return `${newBlur}px ${newSpread}px ${newSize}px`
      })
    }
    case 'quality':
    default:
      return defaultShadow
  }
}

// 获取渐变背景
export function getBackground(defaultBackground: string): string {
  const config = getCurrentPerformanceConfig()

  if (!config.gradients) {
    // 如果背景包含渐变，提取主要颜色保留，否则返回原始背景
    if (defaultBackground.includes('gradient')) {
      const colorMatch = defaultBackground.match(/#[0-9a-fA-F]{3,8}|rgba?\([\d\s,.]+\)/)
      if (colorMatch) {
        return colorMatch[0] // 使用找到的第一个颜色
      }
    }
    // 不是渐变或无法提取颜色，直接返回原始背景
    return defaultBackground
  }

  // 有渐变且允许渐变，返回完整背景
  return defaultBackground
}
