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
 * 创建对话框背景覆盖层
 */
function createOverlay(onClose: () => void): HTMLDivElement {
  const overlay = document.createElement('div')
  overlay.style.cssText = `
    position: fixed;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background: rgba(0,0,0,0.5);
    z-index: 9999;
  `
  overlay.onclick = onClose
  return overlay
}

/**
 * 创建对话框标题元素
 */
function createTitle(text: string): HTMLDivElement {
  const title = document.createElement('div')
  title.style.cssText = 'font-weight: bold; margin-bottom: 10px; font-family: sans-serif;'
  title.textContent = text
  return title
}

/**
 * 创建文本内容输入框
 */
function createContentTextarea(text: string): HTMLTextAreaElement {
  const content = document.createElement('textarea')
  content.value = text
  content.style.cssText = `
    width: 100%;
    height: 200px;
    padding: 10px;
    border: 1px solid #ddd;
    border-radius: 4px;
    font-family: monospace;
    font-size: 12px;
    resize: vertical;
  `
  content.readOnly = false
  return content
}

/**
 * 创建关闭按钮
 */
function createCloseButton(label: string, onClose: () => void): HTMLButtonElement {
  const button = document.createElement('button')
  button.textContent = label
  button.style.cssText = `
    margin-top: 10px;
    padding: 8px 16px;
    background: #1976d2;
    color: white;
    border: none;
    border-radius: 4px;
    cursor: pointer;
    font-family: sans-serif;
  `
  button.onclick = onClose
  return button
}

/**
 * 创建对话框容器
 */
function createDialogContainer(
  title: string,
  text: string,
  closeLabel: string,
  onClose: () => void,
): HTMLDivElement {
  const dialog = document.createElement('div')
  dialog.style.cssText = `
    position: fixed;
    top: 50%;
    left: 50%;
    transform: translate(-50%, -50%);
    background: white;
    border: 1px solid #ccc;
    border-radius: 8px;
    padding: 20px;
    z-index: 10000;
    max-width: 80%;
    max-height: 80%;
    overflow: auto;
    box-shadow: 0 4px 12px rgba(0,0,0,0.15);
    font-family: monospace;
    font-size: 12px;
    white-space: pre-wrap;
    word-break: break-all;
  `

  const titleEl = createTitle(title)
  const content = createContentTextarea(text)
  const button = createCloseButton(closeLabel, onClose)

  dialog.appendChild(titleEl)
  dialog.appendChild(content)
  dialog.appendChild(button)

  return dialog
}

/**
 * 显示包含可复制文本的对话框（最后的回退方案）
 * 这个函数应该在 copyText 失败时由调用者使用
 *
 * @param text 要显示的文本
 * @param title 对话框标题
 * @param closeLabel 关闭按钮标签（可选，用于本地化）
 */
export function showCopyableTextDialog(text: string, title: string = 'Copy Text', closeLabel?: string): void {
  const finalCloseLabel = closeLabel ?? 'Close'

  const onClose = () => {
    dialog.remove()
    overlay.remove()
  }

  const overlay = createOverlay(onClose)
  const dialog = createDialogContainer(title, text, finalCloseLabel, onClose)

  document.body.appendChild(overlay)
  document.body.appendChild(dialog)

  // 自动选中文本
  setTimeout(() => {
    const textarea = dialog.querySelector('textarea') as HTMLTextAreaElement | null
    if (textarea) {
      textarea.focus()
      textarea.select()
    }
  }, 100)
}
