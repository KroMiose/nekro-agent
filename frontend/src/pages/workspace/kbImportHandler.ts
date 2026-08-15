import type { ChangeEvent } from 'react'
import type { KBZipImportError } from '../../services/api/workspace'

/** 失败通知中最多展示的错误条数，超出部分以摘要形式提示 */
export const MAX_ZIP_ERRORS_SHOWN = 10

/**
 * 格式化 zip 导入错误列表：最多展示前 MAX_ZIP_ERRORS_SHOWN 条，
 * 超出部分以 moreLabel 生成的摘要提示（如"…等 N 条未显示"）。
 */
export function formatZipImportErrors(
  errors: KBZipImportError[],
  moreLabel: (count: number) => string
): string {
  const shown = errors.slice(0, MAX_ZIP_ERRORS_SHOWN)
  const more = errors.length - shown.length
  let message = shown.map(error => `${error.source_path}: ${error.reason}`).join('\n')
  if (more > 0) {
    message += `\n${moreLabel(more)}`
  }
  return message
}

type SingleFileUploadOptions<Result> = {
  upload: (file: File) => Promise<Result>
  onResult: (result: Result) => Promise<void> | void
  onError?: (error: unknown) => void
}

/**
 * 通用"单文件上传"处理器：抽取文件、重置 input、调用 upload 并统一错误处理。
 * 成功后的通知与刷新流程由调用端在 onResult 中显式组合。
 */
export function createSingleFileUploadHandler<Result>(options: SingleFileUploadOptions<Result>) {
  return async (event: ChangeEvent<HTMLInputElement>): Promise<void> => {
    const file = event.target.files?.[0]
    event.target.value = '' // 允许再次选择同一文件
    if (!file) return

    try {
      const result = await options.upload(file)
      await options.onResult(result)
    } catch (err) {
      options.onError?.(err)
    }
  }
}
