import axios from '../axios'

export type AnnouncementType = 'notice' | 'update' | 'maintenance' | 'event'

export interface AnnouncementSummary {
  id: string
  title: string
  type: AnnouncementType
  priority: number
  isPinned: boolean
  createdAt: string
}

export interface AnnouncementDetail {
  id: string
  title: string
  content: string
  type: AnnouncementType
  priority: number
  isPinned: boolean
  authorName: string
  expiresAt: string | null
  createdAt: string
  updatedAt: string
}

/**
 * 获取最新公告摘要
 */
export const getLatestAnnouncements = async (
  limit: number = 5,
  force: boolean = false
): Promise<AnnouncementSummary[]> => {
  const response = await axios.get<AnnouncementSummary[]>('/cloud/announcement/latest', {
    params: { limit, force },
  })
  return response.data
}

/**
 * 获取公告详情
 */
export const getAnnouncementDetail = async (id: string): Promise<AnnouncementDetail> => {
  const response = await axios.get<AnnouncementDetail>(`/cloud/announcement/${id}`)
  return response.data
}

/**
 * 获取公告最后更新时间（由遥测接口缓存）
 */
export const getAnnouncementUpdatedAt = async (): Promise<string | null> => {
  const response = await axios.get<{ announcementUpdatedAt: string | null }>(
    '/cloud/announcement/updated-at'
  )
  return response.data.announcementUpdatedAt
}

export default {
  getLatestAnnouncements,
  getAnnouncementDetail,
  getAnnouncementUpdatedAt,
}
