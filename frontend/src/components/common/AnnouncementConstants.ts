import type { AnnouncementType } from '../../services/api/cloud/announcement'

// 公告类型配色
export const ANNOUNCEMENT_TYPE_COLORS: Record<AnnouncementType, string> = {
  notice: '#2196f3',
  update: '#4caf50',
  maintenance: '#ff9800',
  event: '#9c27b0',
}

// 公告类型标签（多语言）
export const ANNOUNCEMENT_TYPE_LABELS: Record<string, Record<AnnouncementType, string>> = {
  'zh-CN': { notice: '通知', update: '更新', maintenance: '维护', event: '活动' },
  'en-US': { notice: 'Notice', update: 'Update', maintenance: 'Maint', event: 'Event' },
}

// 格式化相对时间（如 "5分钟前"）
export function formatRelativeTime(isoString: string, lang: string = 'zh-CN'): string {
  const diff = Math.floor((Date.now() - new Date(isoString).getTime()) / 1000)

  if (lang === 'en-US') {
    if (diff < 60) return 'just now'
    if (diff < 3600) return `${Math.floor(diff / 60)}m ago`
    if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`
    if (diff < 2592000) return `${Math.floor(diff / 86400)}d ago`
    return `${Math.floor(diff / 2592000)}mo ago`
  }

  // 默认中文
  if (diff < 60) return '刚刚'
  if (diff < 3600) return `${Math.floor(diff / 60)}分钟前`
  if (diff < 86400) return `${Math.floor(diff / 3600)}小时前`
  if (diff < 2592000) return `${Math.floor(diff / 86400)}天前`
  return `${Math.floor(diff / 2592000)}月前`
}
