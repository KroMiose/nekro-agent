/**
 * 统一 API 类型定义
 *
 * 本模块提供与后端 API 响应格式对应的类型定义和工具函数
 */

// i18n 字典类型，与后端 SupportedLang 对应
export type I18nDict = {
  'zh-CN'?: string
  'en-US'?: string
}

/**
 * 后端错误响应格式
 *
 * 与后端 AppError.to_response() 输出格式对应
 */
export interface ApiErrorResponse {
  /** 错误类名，如 "ConfigNotFoundError" */
  error: string
  /** 本地化错误消息 */
  message: string
  /** 技术细节（可选，仅开发环境） */
  detail?: string | null
  /** 附加数据（可选） */
  data?: unknown
}

/**
 * 获取本地化文本
 *
 * @param i18nDict - 国际化字典
 * @param defaultText - 默认文本
 * @param lang - 目标语言，默认 zh-CN
 * @returns 本地化文本
 *
 * @example
 * ```ts
 * // i18n 字段以 i18n_ 前缀命名，便于字母排序聚合
 * const name = getLocalizedText(item.i18n_display_name, item.display_name, i18n.language)
 * const desc = getLocalizedText(item.i18n_description, item.description, i18n.language)
 * ```
 */
export function getLocalizedText(
  i18nDict: I18nDict | undefined | null,
  defaultText: string,
  lang: string = 'zh-CN'
): string {
  if (!i18nDict) return defaultText
  return i18nDict[lang as keyof I18nDict] || defaultText
}

/**
 * 检查响应是否为错误响应格式
 */
export function isApiErrorResponse(data: unknown): data is ApiErrorResponse {
  return (
    typeof data === 'object' &&
    data !== null &&
    'error' in data &&
    'message' in data &&
    typeof (data as ApiErrorResponse).error === 'string' &&
    typeof (data as ApiErrorResponse).message === 'string'
  )
}

