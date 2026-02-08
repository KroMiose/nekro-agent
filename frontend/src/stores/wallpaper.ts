import { create } from 'zustand'
import { devtools, persist } from 'zustand/middleware'

interface WallpaperState {
  // 登录页壁纸
  loginWallpaper: string | null
  // 主布局壁纸
  mainWallpaper: string | null
  // 壁纸选择模式 ('fit' | 'cover' | 'repeat' | 'center')
  loginWallpaperMode: string
  mainWallpaperMode: string
  // 壁纸模糊程度 (0-20)
  loginWallpaperBlur: number
  mainWallpaperBlur: number
  // 壁纸暗度 (0-100)
  loginWallpaperDim: number
  mainWallpaperDim: number
  // 动作
  setLoginWallpaper: (url: string | null) => void
  setMainWallpaper: (url: string | null) => void
  setLoginWallpaperMode: (mode: string) => void
  setMainWallpaperMode: (mode: string) => void
  setLoginWallpaperBlur: (blur: number) => void
  setMainWallpaperBlur: (blur: number) => void
  setLoginWallpaperDim: (dim: number) => void
  setMainWallpaperDim: (dim: number) => void
  resetWallpapers: () => void
  // 壁纸失效回调 - 仅在删除壁纸等特殊情况使用
  handleWallpaperInvalid: (wallpaperUrl: string) => void
}

// 默认壁纸设置
const DEFAULT_WALLPAPER_MODE = 'cover'
const DEFAULT_WALLPAPER_BLUR = 0
const DEFAULT_WALLPAPER_DIM = 30

export const useWallpaperStore = create<WallpaperState>()(
  devtools(
    persist(
      (set, get) => ({
        loginWallpaper: null,
        mainWallpaper: null,
        loginWallpaperMode: DEFAULT_WALLPAPER_MODE,
        mainWallpaperMode: DEFAULT_WALLPAPER_MODE,
        loginWallpaperBlur: DEFAULT_WALLPAPER_BLUR,
        mainWallpaperBlur: DEFAULT_WALLPAPER_BLUR,
        loginWallpaperDim: DEFAULT_WALLPAPER_DIM,
        mainWallpaperDim: DEFAULT_WALLPAPER_DIM,

        setLoginWallpaper: (url: string | null) => set({ loginWallpaper: url }),
        setMainWallpaper: (url: string | null) => set({ mainWallpaper: url }),
        setLoginWallpaperMode: (mode: string) => set({ loginWallpaperMode: mode }),
        setMainWallpaperMode: (mode: string) => set({ mainWallpaperMode: mode }),
        setLoginWallpaperBlur: (blur: number) => set({ loginWallpaperBlur: blur }),
        setMainWallpaperBlur: (blur: number) => set({ mainWallpaperBlur: blur }),
        setLoginWallpaperDim: (dim: number) => set({ loginWallpaperDim: dim }),
        setMainWallpaperDim: (dim: number) => set({ mainWallpaperDim: dim }),

        resetWallpapers: () =>
          set({
            loginWallpaper: null,
            mainWallpaper: null,
            loginWallpaperMode: DEFAULT_WALLPAPER_MODE,
            mainWallpaperMode: DEFAULT_WALLPAPER_MODE,
            loginWallpaperBlur: DEFAULT_WALLPAPER_BLUR,
            mainWallpaperBlur: DEFAULT_WALLPAPER_BLUR,
            loginWallpaperDim: DEFAULT_WALLPAPER_DIM,
            mainWallpaperDim: DEFAULT_WALLPAPER_DIM,
          }),

        // 处理壁纸无效的情况 - 仅在确认壁纸已删除等特殊情况使用
        handleWallpaperInvalid: (wallpaperUrl: string) => {
          const state = get()
          
          // 检查并清除无效壁纸
          if (state.loginWallpaper === wallpaperUrl) {
            set({ loginWallpaper: null })
          }
          
          if (state.mainWallpaper === wallpaperUrl) {
            set({ mainWallpaper: null })
          }
        },
      }),
      {
        name: 'wallpaper-storage',
      }
    )
  )
)
