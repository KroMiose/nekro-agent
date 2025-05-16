import { create } from 'zustand'
import { persist } from 'zustand/middleware'

export type ThemeMode = 'light' | 'dark' | 'system'
// 添加性能模式类型
export type PerformanceMode = 'performance' | 'balanced' | 'quality'

// 主题颜色接口
export interface ThemeColors {
  lightBrand: string
  lightAccent: string
  darkBrand: string
  darkAccent: string
}

interface ColorModeState {
  mode: ThemeMode
  presetId: string
  lightBrand: string
  lightAccent: string
  darkBrand: string
  darkAccent: string
  // 添加性能模式
  performanceMode: PerformanceMode
  toggleColorMode: () => void
  setColorMode: (mode: ThemeMode) => void
  setThemePreset: (presetId: string) => void
  setCustomColors: (colors: ThemeColors) => void
  getEffectiveMode: () => 'light' | 'dark'
  // 添加性能模式设置方法
  setPerformanceMode: (mode: PerformanceMode) => void
}

// 获取系统主题
const getSystemTheme = (): 'light' | 'dark' => {
  if (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches) {
    return 'dark'
  }
  return 'light'
}

// 创建主题状态管理
export const useColorMode = create<ColorModeState>()(
  persist(
    (set, get) => ({
      mode: 'system' as ThemeMode,
      presetId: 'kolo',
      lightBrand: '#7E57C2',
      lightAccent: '#26A69A',
      darkBrand: '#9575CD',
      darkAccent: '#4DB6AC',
      // 默认使用质量模式
      performanceMode: 'quality' as PerformanceMode,
      toggleColorMode: () =>
        set(state => ({
          mode: state.mode === 'light' ? 'dark' : state.mode === 'dark' ? 'system' : 'light',
        })),
      setColorMode: (mode: ThemeMode) => set({ mode }),
      setThemePreset: (presetId: string) => set({ presetId }),
      setCustomColors: (colors: ThemeColors) => set({ ...colors }),
      getEffectiveMode: (): 'light' | 'dark' => {
        const currentMode = get().mode
        return currentMode === 'system' ? getSystemTheme() : currentMode as 'light' | 'dark'
      },
      // 设置性能模式
      setPerformanceMode: (performanceMode: PerformanceMode) => set({ performanceMode }),
    }),
    {
      name: 'color-mode',
      partialize: state => ({
        mode: state.mode,
        presetId: state.presetId,
        lightBrand: state.lightBrand,
        lightAccent: state.lightAccent,
        darkBrand: state.darkBrand,
        darkAccent: state.darkAccent,
        performanceMode: state.performanceMode,
      }),
    }
  )
)

// 添加系统主题变化的监听器
if (typeof window !== 'undefined') {
  const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)')
  mediaQuery.addEventListener('change', () => {
    // 仅当模式为 'system' 时，才需要触发更新
    const { mode } = useColorMode.getState()
    if (mode === 'system') {
      // 强制更新状态，触发依赖于主题的组件重新渲染
      useColorMode.setState({})
    }
  })
}
