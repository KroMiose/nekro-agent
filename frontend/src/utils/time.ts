export function formatTimeDiff(timestamp: number): string {
  const timeDiff = Math.floor((Date.now() - timestamp * 1000) / 1000)
  const hours = Math.floor(timeDiff / 3600)
  const minutes = Math.floor((timeDiff % 3600) / 60)
  const seconds = timeDiff % 60

  if (hours > 0) {
    return `${hours}小时${minutes}分钟前`
  }
  if (minutes > 0) {
    return `${minutes}分钟${seconds}秒前`
  }
  return `${seconds}秒前`
}

export function formatLastActiveTime(timestamp: number): string {
  const now = Math.floor(Date.now() / 1000)
  const diff = now - timestamp

  if (diff < 60) {
    return '最近'
  }

  if (diff < 3600) {
    const minutes = Math.floor(diff / 60)
    return `${minutes}分钟前`
  }

  if (diff < 86400) {
    const hours = Math.floor(diff / 3600)
    return `${hours}小时前`
  }

  if (diff < 2592000) {
    const days = Math.floor(diff / 86400)
    return `${days}天前`
  }

  const months = Math.floor(diff / 2592000)
  return `${months}月前`
}

export function formatTimestampToTime(timestamp: string | number): string {
  // 检查参数类型并转换为数字
  const numTimestamp = typeof timestamp === 'string' ? parseInt(timestamp, 10) : timestamp

  // 创建日期对象
  const date = new Date(numTimestamp)

  // 格式化时间 HH:MM:SS
  const hours = date.getHours().toString().padStart(2, '0')
  const minutes = date.getMinutes().toString().padStart(2, '0')
  const seconds = date.getSeconds().toString().padStart(2, '0')

  return `${hours}:${minutes}:${seconds}`
}
