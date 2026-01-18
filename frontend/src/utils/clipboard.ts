/**
 * 调试标志：设置为 true 以启用详细的复制操作日志
 * 默认关闭以避免噪音和潜在的 PII 暴露
 */
const COPY_DEBUG = false

/**
 * 调试日志函数
 */
function debugLog(...args: unknown[]): void {
  if (COPY_DEBUG) {
    console.log('[copyText]', ...args)
  }
}

/**
 * 调试警告函数
 */
function debugWarn(...args: unknown[]): void {
  if (COPY_DEBUG) {
    console.warn('[copyText]', ...args)
  }
}

/**
 * 调试错误函数
 */
function debugError(...args: unknown[]): void {
  if (COPY_DEBUG) {
    console.error('[copyText]', ...args)
  }
}

/**
 * 应用隐藏元素的样式
 * 创建不可见的临时元素用于复制操作
 */
function applyHiddenStyles(el: HTMLElement): void {
  Object.assign(el.style, {
    position: 'fixed',
    left: '0',
    top: '0',
    opacity: '0',
    pointerEvents: 'none',
    zIndex: '-9999',
  } satisfies Partial<CSSStyleDeclaration>)
}

/**
 * 使用现代 Clipboard API 复制文本
 * 仅在 HTTPS 环境下可用
 */
async function copyWithClipboardAPI(text: string): Promise<boolean> {
  if (!navigator.clipboard || !window.isSecureContext) {
    return false
  }

  try {
    await navigator.clipboard.writeText(text)
    debugLog('Copied using Clipboard API')
    return true
  } catch (err) {
    debugWarn('Clipboard API failed, trying fallback:', err)
    return false
  }
}

/**
 * 使用 contentEditable div + execCommand 复制文本
 * 兼容更多浏览器和环境
 */
function copyWithContentEditable(text: string): boolean {
  try {
    const div = document.createElement('div')
    div.contentEditable = 'true'
    applyHiddenStyles(div)

    // 添加文本节点而不是 textContent，某些浏览器对此反应更好
    const textNode = document.createTextNode(text)
    div.appendChild(textNode)

    document.body.appendChild(div)

    // 选中内容
    const range = document.createRange()
    range.selectNodeContents(div)
    const selection = window.getSelection()
    if (selection) {
      selection.removeAllRanges()
      selection.addRange(range)
    }

    // 执行复制
    const successful = document.execCommand('copy')

    // 清理
    if (selection) {
      selection.removeAllRanges()
    }

    // 异步删除以避免时序问题
    setTimeout(() => {
      try {
        document.body.removeChild(div)
      } catch (e) {
        // 忽略
      }
    }, 10)

    if (successful) {
      debugLog('Copied using contentEditable + execCommand')
    }
    return successful
  } catch (err) {
    debugError('contentEditable method failed:', err)
    return false
  }
}

/**
 * 使用 textarea + execCommand 复制文本
 * 最后的降级方案，兼容最旧的浏览器
 */
function copyWithTextarea(text: string): boolean {
  try {
    const textarea = document.createElement('textarea')
    textarea.value = text
    applyHiddenStyles(textarea)

    document.body.appendChild(textarea)
    textarea.focus()
    textarea.select()

    try {
      textarea.setSelectionRange(0, text.length)
    } catch (e) {
      // 忽略
    }

    const successful = document.execCommand('copy')

    // 异步删除以避免时序问题
    setTimeout(() => {
      try {
        document.body.removeChild(textarea)
      } catch (e) {
        // 忽略
      }
    }, 10)

    if (successful) {
      debugLog('Copied using textarea + execCommand')
    }
    return successful
  } catch (err) {
    debugError('textarea method failed:', err)
    return false
  }
}

/**
 * 复制文本到剪贴板（兼容 HTTP 环境）
 *
 * 策略顺序：
 * 1. 现代 Clipboard API (HTTPS 环境)
 * 2. ContentEditable + execCommand (多数浏览器)
 * 3. Textarea + execCommand (降级方案)
 *
 * @param text 要复制的文本内容
 * @returns Promise<boolean> 成功返回 true，失败返回 false
 */
export async function copyText(text: string): Promise<boolean> {
  // 策略 1: 尝试现代 Clipboard API
  if (await copyWithClipboardAPI(text)) {
    return true
  }

  // 策略 2: 尝试 contentEditable + execCommand
  if (copyWithContentEditable(text)) {
    return true
  }

  // 策略 3: 尝试 textarea + execCommand
  if (copyWithTextarea(text)) {
    return true
  }

  // 所有方法都失败
  debugError('All clipboard methods failed - execCommand may be blocked by browser security policy')
  return false
}

/**
 * 全局事件：显示可复制文本对话框
 * 由 CopyableTextDialogProvider 监听和处理
 */
export const COPYABLE_TEXT_DIALOG_EVENT = 'nekro:showCopyableTextDialog'

export interface CopyableTextDialogEventDetail {
  text: string
  title?: string
  description?: string
}

/**
 * 显示包含可复制文本的对话框
 * 通过全局事件触发，由 CopyableTextDialogProvider 管理 UI
 *
 * @param text 要显示的文本
 * @param title 对话框标题（可选，使用翻译默认值）
 *
 * @example
 * ```typescript
 * // 从工具函数调用
 * showCopyableTextDialog('some text', 'My Dialog Title')
 *
 * // 使用翻译后的标题
 * showCopyableTextDialog(logText, t('dialog.copyLog'))
 * ```
 */
export function showCopyableTextDialog(
  text: string,
  title?: string,
): void {
  // 触发全局事件，由 CopyableTextDialogProvider 处理
  const event = new CustomEvent<CopyableTextDialogEventDetail>(
    COPYABLE_TEXT_DIALOG_EVENT,
    {
      detail: {
        text,
        title,
        // closeLabel 已不再需要，Dialog UI 中直接使用 i18n 翻译
      },
    },
  )
  window.dispatchEvent(event)
}
