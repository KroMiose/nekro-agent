import type { ChangeEvent } from 'react'

type FileImportConfig<Result> = {
  upload: (file: File) => Promise<Result>
  onSuccess: (result: Result) => void
  onError: (message: string) => void
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
      config.onError(err instanceof Error ? err.message : String(err))
    }
  }
}
