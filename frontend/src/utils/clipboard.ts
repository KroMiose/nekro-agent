/**
 * 复制文本到剪贴板（兼容 HTTP 环境）
 *
 * 策略：
 * 1. 优先使用现代 Clipboard API (HTTPS 环境)
 * 2. 回退到多种 execCommand 方法 (HTTP 环境)
 *
 * @param text 要复制的文本内容
 * @returns Promise<boolean> 成功返回 true，失败返回 false
 */
export async function copyText(text: string): Promise<boolean> {
  // 方法 1: 尝试现代 Clipboard API
  if (navigator.clipboard && window.isSecureContext) {
    try {
      await navigator.clipboard.writeText(text)
      console.log('Copied using Clipboard API')
      return true
    } catch (err) {
      console.warn('Clipboard API failed, trying fallback:', err)
    }
  }

  // 方法 2: 使用 contentEditable div + execCommand + Selection Range
  try {
    const div = document.createElement('div')
    div.contentEditable = 'true'
    div.style.position = 'fixed'
    div.style.left = '0'
    div.style.top = '0'
    div.style.opacity = '0'
    div.style.pointerEvents = 'none'
    div.style.zIndex = '-9999'

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
      console.log('Copied using contentEditable + execCommand')
      return true
    }
  } catch (err) {
    console.error('contentEditable method failed:', err)
  }

  // 方法 3: 回退到 textarea + execCommand
  try {
    const textarea = document.createElement('textarea')
    textarea.value = text
    textarea.style.position = 'fixed'
    textarea.style.left = '0'
    textarea.style.top = '0'
    textarea.style.opacity = '0'
    textarea.style.pointerEvents = 'none'
    textarea.style.zIndex = '-9999'

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
      console.log('Copied using textarea + execCommand')
      return true
    }
  } catch (err) {
    console.error('textarea method failed:', err)
  }

  // 所有方法都失败
  console.error('All clipboard methods failed - execCommand may be blocked by browser security policy')
  return false
}

/**
 * 显示包含可复制文本的对话框（最后的回退方案）
 * 这个函数应该在 copyText 失败时由调用者使用
 *
 * @param text 要显示的文本
 * @param title 对话框标题
 */
export function showCopyableTextDialog(text: string, title: string = 'Copy Text'): void {
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

  const title_el = document.createElement('div')
  title_el.style.cssText = 'font-weight: bold; margin-bottom: 10px; font-family: sans-serif;'
  title_el.textContent = title

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

  const button = document.createElement('button')
  button.textContent = 'Close'
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
  button.onclick = () => {
    dialog.remove()
    overlay.remove()
  }

  dialog.appendChild(title_el)
  dialog.appendChild(content)
  dialog.appendChild(button)

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
  overlay.onclick = () => {
    dialog.remove()
    overlay.remove()
  }

  document.body.appendChild(overlay)
  document.body.appendChild(dialog)

  // 自动选中文本
  setTimeout(() => {
    content.focus()
    content.select()
  }, 100)
}




