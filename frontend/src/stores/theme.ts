import { create } from 'zustand'
import { persist } from 'zustand/middleware'

export type ThemeMode = 'light' | 'dark' | 'system'

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
  toggleColorMode: () => void
  setColorMode: (mode: ThemeMode) => void
  setThemePreset: (presetId: string) => void
  setCustomColors: (colors: ThemeColors) => void
  getEffectiveMode: () => 'light' | 'dark'
}

// 检测系统主题偏好
const getSystemTheme = (): 'light' | 'dark' => {
  if (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches) {
    return 'dark'
  }
  return 'light'
}

// 默认主题颜色
const DEFAULT_COLORS: ThemeColors = {
  lightBrand: '#EA5252',
  lightAccent: '#9C6ADE',
  darkBrand: '#E05252',
  darkAccent: '#A07BE0',
}

// 先创建 store，不使用内部引用
export const useColorMode = create<ColorModeState>()(
  persist(
    (set, get) => ({
      mode: 'light' as ThemeMode,
      presetId: 'red',
      ...DEFAULT_COLORS,
      toggleColorMode: () => 
        set(state => {
          // 在 light、dark 和 system 之间循环切换
          const modes: ThemeMode[] = ['light', 'dark', 'system']
          const currentIndex = modes.indexOf(state.mode)
          const nextIndex = (currentIndex + 1) % modes.length
          return { mode: modes[nextIndex] }
        }),
      setColorMode: (mode: ThemeMode) => set({ mode }),
      setThemePreset: (presetId: string) => set({ presetId }),
      setCustomColors: (colors: ThemeColors) => set({
        presetId: 'custom',
        ...colors
      }),
      getEffectiveMode: (): 'light' | 'dark' => {
        const currentMode = get().mode
        // 如果是系统模式则获取系统主题，否则返回当前模式
        // 由于 currentMode 可能是 'system'，需要处理这种情况
        return currentMode === 'system' ? getSystemTheme() : (currentMode === 'dark' ? 'dark' : 'light')
      }
    }),
    {
      name: 'color-mode',
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
