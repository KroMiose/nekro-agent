import i18next, { Resource } from 'i18next'
import { initReactI18next } from 'react-i18next'
import LanguageDetector from 'i18next-browser-languagedetector'

// 支持的语言列表
export const supportedLanguages = {
  'zh-CN': '简体中文',
  'en-US': 'English',
} as const

export type SupportedLocale = keyof typeof supportedLanguages

// 使用 Vite 的 import.meta.glob 动态导入集中管理的翻译文件
const localeModules = import.meta.glob<{ default: Record<string, unknown> }>(
  ['../locales/*/*.json'],
  { eager: true }
)

// 解析翻译资源
const resources: Resource = {}

Object.entries(localeModules).forEach(([path, module]) => {
  // 解析路径以确定语言和命名空间
  // 示例路径: ../locales/zh-CN/common.json
  //正则匹配: ../locales/(?<locale>[\w-]+)/(?<namespace>[\w-]+).json
  const match = path.match(/\/([\w-]+)\/([\w-]+)\.json$/)
  if (!match) return

  const [, locale, namespace] = match

  // 初始化语言资源对象
  if (!resources[locale]) {
    resources[locale] = {}
  }

  // 添加到资源中
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  resources[locale][namespace] = module.default as any
})

// 初始化 i18next
i18next
  .use(LanguageDetector)
  .use(initReactI18next)
  .init({
    resources,
    fallbackLng: 'zh-CN',
    defaultNS: 'common',

    // 语言检测配置
    detection: {
      order: ['localStorage', 'navigator'],
      caches: ['localStorage'],
      lookupLocalStorage: 'i18nextLng',
    },

    // 插值配置
    interpolation: {
      escapeValue: false, // React 已经安全处理
    },

    // 调试模式（开发环境）
    debug: import.meta.env.DEV,

    // 命名空间配置 (可选，i18next 会自动推断)
    ns: Object.keys(resources['zh-CN'] || {}),

    // React 特定配置
    react: {
      useSuspense: false, // 我们使用 lazy loading，不需要 Suspense
    },
  })

export default i18next
