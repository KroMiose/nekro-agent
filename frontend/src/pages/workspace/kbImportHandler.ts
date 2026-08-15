import type { ChangeEvent } from 'react'

type FileImportConfig<Result> = {
  upload: (file: File) => Promise<Result>
  onSuccess: (result: Result) => void
  onError: (message: string) => void
  refresh?: () => Promise<void> | void
}

/** 提取用户可读的错误信息：优先后端响应消息，其次 Error.message */
function extractErrorMessage(err: unknown): string {
  if (err instanceof Error) {
    const maybeAxios = err as Error & { response?: { data?: { message?: unknown } } }
    const serverMessage = maybeAxios.response?.data?.message
    if (typeof serverMessage === 'string' && serverMessage.trim()) {
      return serverMessage
    }
    return err.message
  }
  return String(err)
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
      config.onError(extractErrorMessage(err))
    }
  }
}
