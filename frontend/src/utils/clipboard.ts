/**
 * 复制文本到剪贴板
 *
 * 优先使用现代 Clipboard API (HTTPS环境)
 * 降级使用 contentEditable + execCommand (HTTP环境)
 *
 * @param text 要复制的文本内容
 * @returns Promise<boolean> 成功返回 true，失败返回 false
 */
export async function copyText(text: string): Promise<boolean> {
  // 方法1: 现代 Clipboard API (仅 HTTPS)
  if (navigator.clipboard && window.isSecureContext) {
    try {
      await navigator.clipboard.writeText(text)
      return true
    } catch {
      // 继续尝试降级方案
    }
  }

  // 方法2: contentEditable + execCommand 降级
  try {
    const div = document.createElement('div')
    div.contentEditable = 'true'

    // 隐藏样式
    div.style.position = 'fixed'
    div.style.left = '0'
    div.style.top = '0'
    div.style.opacity = '0'
    div.style.pointerEvents = 'none'
    div.style.zIndex = '-9999'

    // 添加文本节点
    const textNode = document.createTextNode(text)
    div.appendChild(textNode)

    document.body.appendChild(div)

    // 使用 Selection API 选中内容
    const range = document.createRange()
    range.selectNodeContents(div)
    const selection = window.getSelection()
    if (selection) {
      selection.removeAllRanges()
      selection.addRange(range)
    }

    // 执行复制
    const successful = document.execCommand('copy')

    // 清理选择
    if (selection) {
      selection.removeAllRanges()
    }

    // 异步删除元素，避免时序问题
    setTimeout(() => {
      try {
        document.body.removeChild(div)
      } catch (e) {
        // 忽略
      }
    }, 10)

    return successful
  } catch {
    return false
  }
}
