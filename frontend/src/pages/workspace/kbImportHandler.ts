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

type FileImportConfig<Result> = {
  upload: (file: File) => Promise<Result>
  onSuccess: (result: Result) => void
  onError?: (error: unknown) => void
  refresh?: () => Promise<void> | void
}

/** 通用"单文件上传 + 回调通知 + 刷新"导入处理器，供 zip 等单文件导入场景复用 */
export function createSingleFileImportHandler<Result>(config: FileImportConfig<Result>) {
  return async (event: ChangeEvent<HTMLInputElement>): Promise<void> => {
    const file = event.target.files?.[0]
    event.target.value = '' // 允许再次选择同一文件
    if (!file) return

    try {
      const result = await config.upload(file)
      config.onSuccess(result)
      await config.refresh?.()
    } catch (err) {
      config.onError?.(err)
    }
  }
}
