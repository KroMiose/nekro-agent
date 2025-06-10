/**
 * 颜色调色板文件
 * 该文件定义所有主题的基础色彩配置，其他颜色由算法生成
 */
import { PaletteMode } from '@mui/material'
import { alpha, darken, lighten } from '@mui/material/styles'

// 主题类型扩展 - 允许未来添加更多主题
export type ThemeMode = 'light' | 'dark'
export type BaseThemeMode = 'light' | 'dark'
export type ThemeKeys = 'light' | 'dark' | string // 未来可以添加更多主题

// 【极简】调色板配置 - 只需定义两种核心颜色
export interface MinimalPaletteConfig {
  // 品牌主色 - 整个应用的主要颜色
  brand: string
  // 强调色 - 用于次要按钮、链接等
  accent: string
}

// 最简洁的主题配置
export interface ThemeConfig {
  // 基础调色板
  palette: MinimalPaletteConfig
  // 主题模式
  mode: 'light' | 'dark'
}

// 主题预设类型
export interface ThemePreset {
  id: string
  name: string
  description: string
  light: MinimalPaletteConfig
  dark: MinimalPaletteConfig
}

// 【预设主题】基础颜色配置
export const themePresets: ThemePreset[] = [
  {
    id: 'kolo',
    name: '可洛红',
    description: '热情活力的红色主题',
    light: {
      brand: '#EA5252',
      accent: '#9C6ADE',
    },
    dark: {
      brand: '#E05252',
      accent: '#A07BE0',
    },
  },
  {
    id: 'sakura',
    name: '樱花粉',
    description: '如樱花般柔和甜美的粉色系',
    light: {
      brand: '#FF9BB3',
      accent: '#7986CB',
    },
    dark: {
      brand: '#F06292',
      accent: '#5C6BC0',
    },
  },
  {
    id: 'aqua',
    name: '星空蓝',
    description: '如深邃星空般梦幻的蓝色系',
    light: {
      brand: '#5D9CEC',
      accent: '#EC87C0',
    },
    dark: {
      brand: '#4A89DC',
      accent: '#D770AD',
    },
  },
  {
    id: 'matcha',
    name: '抹茶绿',
    description: '如日式抹茶般清新的绿色系',
    light: {
      brand: '#66BB6A',
      accent: '#FFB74D',
    },
    dark: {
      brand: '#4CAF50',
      accent: '#FFA726',
    },
  },
  {
    id: 'lilac',
    name: '魔法紫',
    description: '如魔法少女般神秘的紫色系',
    light: {
      brand: '#9575CD',
      accent: '#4DB6AC',
    },
    dark: {
      brand: '#7E57C2',
      accent: '#26A69A',
    },
  },
]

// 【浅色主题】基础颜色配置
const lightPalette: MinimalPaletteConfig = {
  brand: '#EA5252', // 主色调
  accent: '#9C6ADE', // 辅助色
}

// 【暗色主题】基础颜色配置
const darkPalette: MinimalPaletteConfig = {
  brand: '#E05252', // 主色调
  accent: '#A07BE0', // 辅助色
}

// 应用当前使用的主题 ID - 在初始化时从存储读取
let _currentThemePresetId = 'kolo' // 默认值，将在初始化时更新

// 尝试从本地存储获取主题ID
if (typeof window !== 'undefined') {
  try {
    const storedData = JSON.parse(localStorage.getItem('color-mode') || '{}')
    if (storedData && storedData.state && storedData.state.presetId) {
      _currentThemePresetId = storedData.state.presetId

      // 如果是自定义主题，同时需要加载自定义颜色
      if (
        _currentThemePresetId === 'custom' &&
        storedData.state.lightBrand &&
        storedData.state.lightAccent &&
        storedData.state.darkBrand &&
        storedData.state.darkAccent
      ) {
        // 更新默认的浅色主题
        lightPalette.brand = storedData.state.lightBrand
        lightPalette.accent = storedData.state.lightAccent

        // 更新默认的深色主题
        darkPalette.brand = storedData.state.darkBrand
        darkPalette.accent = storedData.state.darkAccent
      } else {
        // 应用预设主题
        const preset = themePresets.find(p => p.id === _currentThemePresetId)
        if (preset) {
          lightPalette.brand = preset.light.brand
          lightPalette.accent = preset.light.accent
          darkPalette.brand = preset.dark.brand
          darkPalette.accent = preset.dark.accent
        }
      }
    }
  } catch (error) {
    console.error('Failed to load theme from localStorage:', error)
  }
}

// 导出当前主题ID
export const currentThemePresetId = _currentThemePresetId

// 所有主题的完整配置
export const themes: Record<ThemeKeys, ThemeConfig> = {
  light: {
    palette: lightPalette,
    mode: 'light',
  },
  dark: {
    palette: darkPalette,
    mode: 'dark',
  },
}

// 更新主题配置
export function updateTheme(themePresetId: string) {
  const preset = themePresets.find(p => p.id === themePresetId)
  if (preset) {
    // 更新当前选中的预设ID
    _currentThemePresetId = themePresetId

    // 更新主题配置
    themes.light.palette = preset.light
    themes.dark.palette = preset.dark

    // 触发重新渲染
    if (typeof window !== 'undefined') {
      // 如果是在客户端环境，派发一个自定义事件通知主题变化
      const themeChangeEvent = new CustomEvent('nekro-theme-change', {
        detail: { presetId: themePresetId },
      })
      window.dispatchEvent(themeChangeEvent)
    }
  }
}

// 自定义主题
export function customizeTheme(light: MinimalPaletteConfig, dark: MinimalPaletteConfig) {
  // 更新当前选中的预设ID为自定义
  _currentThemePresetId = 'custom'

  // 更新主题配置
  themes.light.palette = light
  themes.dark.palette = dark

  // 触发重新渲染
  if (typeof window !== 'undefined') {
    // 如果是在客户端环境，派发一个自定义事件通知主题变化
    const themeChangeEvent = new CustomEvent('nekro-theme-change', {
      detail: {
        presetId: 'custom',
        light,
        dark,
      },
    })
    window.dispatchEvent(themeChangeEvent)
  }
}

// 颜色衍生工具函数

/**
 * 获取颜色的亮色变体
 * @param color 基础颜色
 * @param factor 亮化因子
 * @returns 更亮的颜色
 */
export function getLighterColor(color: string, factor: number = 0.2): string {
  return lighten(color, factor)
}

/**
 * 获取颜色的暗色变体
 * @param color 基础颜色
 * @param factor 暗化因子
 * @returns 更暗的颜色
 */
export function getDarkerColor(color: string, factor: number = 0.2): string {
  return darken(color, factor)
}

/**
 * 获取颜色的高亮变体
 * @param color 基础颜色
 * @returns 高亮颜色
 */
export function getHighlightColor(color: string): string {
  return lighten(color, 0.15)
}

/**
 * 获取颜色的透明变体
 * @param color 基础颜色
 * @param opacity 透明度
 * @returns 带透明度的颜色
 */
export function getAlphaColor(color: string, opacity: number): string {
  return alpha(color, opacity)
}

/**
 * 从基础颜色生成功能色
 * @param brand 主色调
 * @param accent 辅助色
 * @param mode 主题模式
 * @returns 功能色对象
 */
export function generateFunctionalColors(_brand: string, _accent: string, mode: 'light' | 'dark') {
  // 生成功能色
  return {
    success: mode === 'light' ? '#4caf50' : '#5BC15F', // 成功色
    error: mode === 'light' ? '#f44336' : '#F25757', // 错误色
    warning: mode === 'light' ? '#ff9800' : '#FFA726', // 警告色
    info: mode === 'light' ? '#2196f3' : '#42A5F5', // 信息色
  }
}

/**
 * 从基础颜色生成背景色
 * @param mode 主题模式
 * @param brand 主色调
 * @returns 背景色对象
 */
export function generateBackgroundColors(mode: 'light' | 'dark', brand: string) {
  // 根据主色调生成适合的背景色，但降低饱和度
  const desaturateFactor = 0.7 // 调整饱和度的系数，增加到0.7
  const baseColor =
    mode === 'light'
      ? getAlphaColor(getLighterColor(brand, 0.7), desaturateFactor) // 浅色模式下基于主色生成非常浅的背景色
      : getAlphaColor(getDarkerColor(brand, 0.85), desaturateFactor) // 深色模式下基于主色生成更深的背景色

  // 在暗色模式下使用更暗的纸张颜色
  const paperColor =
    mode === 'light'
      ? '#fafafa' // 浅色模式下使用纯白色
      : '#2f2f2f' // 深色模式下使用深灰色

  return {
    main: baseColor, // 主背景色
    paper:
      mode === 'light'
        ? paperColor // 浅色模式下
        : paperColor, // 深色模式下卡片背景
    card:
      mode === 'light'
        ? getAlphaColor(getLighterColor(baseColor, 0.04), 0.95) // 浅色模式下卡片渐变底色比背景稍亮
        : getAlphaColor(getLighterColor(baseColor, 0.04), 0.95), // 深色模式下卡片渐变底色比背景稍亮
  }
}

/**
 * 扩展基本调色板以生成MUI使用的完整配置
 * @param config 基本主题配置
 * @returns 扩展后的调色板配置
 */
export function getExtendedPalette(config: ThemeConfig) {
  const { palette, mode } = config

  // 生成功能色和背景色
  const functionalColors = generateFunctionalColors(palette.brand, palette.accent, mode)
  const backgroundColors = generateBackgroundColors(mode, palette.brand)

  // 扩展主色调
  const primaryExtended = {
    main: palette.brand,
    light: getLighterColor(palette.brand, 0.2),
    dark: getDarkerColor(palette.brand, 0.2),
    lighter: getLighterColor(palette.brand, 0.4),
    darker: getDarkerColor(palette.brand, 0.3),
    highlight: getHighlightColor(palette.brand),
  }

  // 扩展辅助色
  const secondaryExtended = {
    main: palette.accent,
    light: getLighterColor(palette.accent, 0.2),
    dark: getDarkerColor(palette.accent, 0.2),
    lighter: getLighterColor(palette.accent, 0.4),
    darker: getDarkerColor(palette.accent, 0.3),
    highlight: getHighlightColor(palette.accent),
  }

  return {
    primary: primaryExtended,
    secondary: secondaryExtended,
    // 扩展功能色
    success: functionalColors.success,
    error: functionalColors.error,
    warning: functionalColors.warning,
    info: functionalColors.info,
    // 背景色
    background: backgroundColors,
  }
}

// MUI调色板配置转换
export function getMuiPaletteOptions(mode: PaletteMode, themeConfig: ThemeConfig) {
  const extendedPalette = getExtendedPalette(themeConfig)
  const { background } = extendedPalette

  return {
    mode,
    primary: {
      main: extendedPalette.primary.main,
      light: extendedPalette.primary.light,
      dark: extendedPalette.primary.dark,
      contrastText: '#fff',
    },
    secondary: {
      main: extendedPalette.secondary.main,
      light: extendedPalette.secondary.light,
      dark: extendedPalette.secondary.dark,
      contrastText: '#fff',
    },
    success: {
      main: extendedPalette.success,
      contrastText: '#fff',
    },
    error: {
      main: extendedPalette.error,
      contrastText: '#fff',
    },
    warning: {
      main: extendedPalette.warning,
      contrastText: mode === 'dark' ? 'rgba(0, 0, 0, 0.87)' : '#fff',
    },
    info: {
      main: extendedPalette.info,
      contrastText: '#fff',
    },
    background: {
      default: background.main,
      paper: background.paper,
    },
    text: {
      primary: mode === 'dark' ? 'rgba(255, 255, 255, 0.92)' : 'rgba(0, 0, 0, 0.87)',
      secondary: mode === 'dark' ? 'rgba(255, 255, 255, 0.68)' : 'rgba(0, 0, 0, 0.6)',
      disabled: mode === 'dark' ? 'rgba(255, 255, 255, 0.48)' : 'rgba(0, 0, 0, 0.38)',
    },
    divider: mode === 'dark' ? 'rgba(255, 255, 255, 0.07)' : 'rgba(0, 0, 0, 0.12)',
    action: {
      active: mode === 'dark' ? 'rgba(255, 255, 255, 0.75)' : 'rgba(0, 0, 0, 0.6)',
      hover: mode === 'dark' ? 'rgba(255, 255, 255, 0.1)' : 'rgba(0, 0, 0, 0.04)',
      selected:
        mode === 'dark'
          ? getAlphaColor(extendedPalette.primary.main, 0.18)
          : getAlphaColor(extendedPalette.primary.main, 0.18),
      disabled: mode === 'dark' ? 'rgba(255, 255, 255, 0.28)' : 'rgba(0, 0, 0, 0.26)',
      disabledBackground: mode === 'dark' ? 'rgba(255, 255, 255, 0.1)' : 'rgba(0, 0, 0, 0.12)',
    },
  }
}
