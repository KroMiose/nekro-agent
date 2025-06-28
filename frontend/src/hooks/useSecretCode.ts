import { useState, useEffect, useCallback } from 'react'

/**
 * 一个用于检测用户输入秘密按键序列的 React Hook。
 * @param targetSequence - 目标按键序列，例如 ['a', 'b', 'c']。
 * @param onUnlock - 当序列匹配成功时要执行的回调函数。
 * @param timeout - 输入序列中两次按键之间的最大允许超时时间（毫秒）。默认为 3000ms。
 */
export const useSecretCode = (
  targetSequence: string[],
  onUnlock: () => void,
  timeout: number = 3000
) => {
  const [inputSequence, setInputSequence] = useState<string[]>([])

  // 如果用户在指定时间内没有继续输入，则重置序列
  useEffect(() => {
    if (inputSequence.length > 0) {
      const handler = setTimeout(() => setInputSequence([]), timeout)
      return () => clearTimeout(handler)
    }
  }, [inputSequence, timeout])

  /**
   * 注册一次按键。
   * @param key - 被按下的键的标识符。
   */
  const register = useCallback(
    (key: string) => {
      const newSequence = [...inputSequence, key]

      // 检查新的序列是否是目标序列的有效前缀
      if (targetSequence.slice(0, newSequence.length).join('') !== newSequence.join('')) {
        // 如果输入错误，则重置序列。
        // 但如果当前按键是目标序列的第一个键，则开始一个新的序列。
        if (targetSequence[0] === key) {
          setInputSequence([key])
        } else {
          setInputSequence([])
        }
        return
      }

      setInputSequence(newSequence)

      // 如果序列完全匹配，则执行回调并重置
      if (newSequence.length === targetSequence.length) {
        onUnlock()
        setInputSequence([])
      }
    },
    [inputSequence, targetSequence, onUnlock]
  )

  return register
}
