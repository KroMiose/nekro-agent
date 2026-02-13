import { create } from 'zustand'
import { cloudApi } from '../services/api/cloud'
import { useWallpaperStore } from './wallpaper'
import { useColorMode } from './theme'
import { updateTheme } from '../theme/themeApi'

// 通知类型
export interface NotifyOptions {
  showSuccess?: (message: string) => void // 显示成功通知
  showWarning?: (message: string) => void // 显示警告通知
  showError?: (message: string) => void // 显示错误通知
}

// 检查回调类型定义
export interface StarCheckCallbacks {
  onStarred?: () => void // 当用户已Star时的回调
  onNotStarred?: () => void // 当用户未Star时的回调
  onError?: (error: unknown) => void // 检查出错时的回调
  resetDefaults?: boolean // 是否在未Star时重置默认设置（如主题、壁纸等）
  notify?: NotifyOptions // 通知回调函数
}

interface GitHubStarState {
  // 是否所有官方仓库都被star了
  allStarred: boolean
  // 已star的仓库列表
  starredRepositories: string[]
  // 未star的仓库列表
  unstarredRepositories: string[]
  // 是否正在检查
  checking: boolean
  // 上次检查时间
  lastCheckTime: number | null
  // 检查是否已star
  checkStarStatus: (
    options?: {
      force?: boolean // 是否强制检查（忽略缓存）
      clearCache?: boolean // 是否清除缓存
      showNotification?: boolean // 是否显示通知
    },
    callbacks?: StarCheckCallbacks // 回调函数
  ) => Promise<boolean>
  // 重置状态
  resetState: () => void
}

export const useGitHubStarStore = create<GitHubStarState>()((set, get) => ({
  allStarred: false,
  starredRepositories: [],
  unstarredRepositories: [],
  checking: false,
  lastCheckTime: null,

  checkStarStatus: async (options = {}, callbacks?: StarCheckCallbacks) => {
    const { force = false, clearCache = false, showNotification = false } = options
    const { resetDefaults = true, notify } = callbacks || {}

    try {
      const state = get()

      // 避免重复检查
      if (state.checking) return state.allStarred

      set({ checking: true })

      // 调用API检查star状态
      const response = await cloudApi.auth.checkGitHubStars(force, clearCache)
      const { allStarred, starredRepositories, unstarredRepositories } = response
      const isStarred = Boolean(allStarred)

      set({
        allStarred: isStarred,
        starredRepositories: starredRepositories || [],
        unstarredRepositories: unstarredRepositories || [],
        lastCheckTime: Date.now(),
        checking: false,
      })

      if (!isStarred && resetDefaults) {
        useWallpaperStore.getState().resetWallpapers()

        const { setThemePreset } = useColorMode.getState()
        setThemePreset('kolo')
        updateTheme('kolo')
      }

      if (isStarred) {
        callbacks?.onStarred?.()
      } else {
        callbacks?.onNotStarred?.()
      }

      return isStarred
    } catch (error) {
      set({ checking: false })

      // 显示错误通知
      if (showNotification && notify) {
        notify.showError?.('检查GitHub Star状态失败，请重试')
      }

      // 执行错误回调
      callbacks?.onError?.(error)

      return false
    }
  },

  resetState: () => {
    set({
      allStarred: false,
      starredRepositories: [],
      unstarredRepositories: [],
      lastCheckTime: null,
    })
  },
}))
