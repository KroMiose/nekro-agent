import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import i18next from '../config/i18n'
import type { SupportedLocale } from '../config/i18n'
import { unifiedConfigApi } from '../services/api/unified-config'

interface LocaleState {
  currentLocale: SupportedLocale
  /** 切换语言（同时同步到后端） */
  setLocale: (locale: SupportedLocale) => void
  /** 仅更新前端语言（不写后端，用于从后端同步到前端） */
  setLocaleLocal: (locale: SupportedLocale) => void
  /** 从后端 SYSTEM_LANG 同步到前端 */
  syncFromBackend: () => Promise<void>
}

export const useLocaleStore = create<LocaleState>()(
  persist(
    (set, get) => ({
      currentLocale: 'zh-CN',
      setLocale: (locale: SupportedLocale) => {
        i18next.changeLanguage(locale)
        set({ currentLocale: locale })
        // 同步到后端 SYSTEM_LANG（batchUpdateConfig 内部同时更新+保存到文件）
        unifiedConfigApi
          .batchUpdateConfig('system', { SYSTEM_LANG: locale })
          .catch((err) => {
            console.error('[locale] Failed to sync SYSTEM_LANG to backend:', err)
          })
      },
      setLocaleLocal: (locale: SupportedLocale) => {
        i18next.changeLanguage(locale)
        set({ currentLocale: locale })
      },
      syncFromBackend: async () => {
        try {
          const item = await unifiedConfigApi.getConfigItem('system', 'SYSTEM_LANG')
          const backendLang = item.value as string
          if (backendLang && (backendLang === 'zh-CN' || backendLang === 'en-US')) {
            const current = get().currentLocale
            if (current !== backendLang) {
              i18next.changeLanguage(backendLang)
              set({ currentLocale: backendLang as SupportedLocale })
            }
          }
        } catch {
          // 获取失败使用本地存储的值
        }
      },
    }),
    {
      name: 'nekro-locale',
      partialize: state => ({
        currentLocale: state.currentLocale,
      }),
    }
  )
)
