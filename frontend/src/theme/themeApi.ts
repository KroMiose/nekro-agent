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
  methodTypeColors,
  methodTypeTexts,
  methodTypeDescriptions,
} from './variants'

// 从 utils.ts
import {
  getStopTypeText,
  getStopTypeColor,
  getStopTypeColorValue,
  getMessageTypeColor,
  LEGACY_COLORS,
  stopTypeColors,
  stopTypeColorValues,
  stopTypeTexts
} from './utils'

// 导出类型
export type {
  ThemeMode,
  BaseThemeMode,
  ThemeKeys,
  MinimalPaletteConfig,
  ThemeConfig,
  ThemePreset,
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
  methodTypeColors,
  methodTypeTexts,
  methodTypeDescriptions,

  // 从 utils.ts
  getStopTypeText,
  getStopTypeColor,
  getStopTypeColorValue,
  getMessageTypeColor,
  LEGACY_COLORS,
  stopTypeColors,
  stopTypeColorValues,
  stopTypeTexts,
} 